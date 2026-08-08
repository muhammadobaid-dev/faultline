"""Running a project's suite against the user's own target.

Synchronous by design: it makes blocking provider calls one after another and
runs in the worker thread, reaching the database through SyncFacade.

The difference from the punchbag is that the cases are not hand-authored: they are
generated once, pinned to the project, and reused. That pinning is what makes a trend
meaningful - a grade diff between two runs of the same test set measures the bot
changing, whereas a diff across regenerated suites measures the questions changing and
tells you nothing.

Generation happens at most once per project unless the rules change. Recon happens in
the same breath, because a target-blind attacker gets deflected at whatever gate the
bot has and reports false safety.
"""

from __future__ import annotations

import logging
from typing import Any

from faultline import config
from faultline.domain import AttackCase
from faultline.execution.runner import Executor
from faultline.execution.targets import PromptSection, Target
from faultline.generation.generator import AttackGenerator
from faultline.generation.recon import observe
from faultline.grading import DimensionGrade, grade_dimension
from faultline.jobs.store import JobStatus
from faultline.judging.judge import Judge
from faultline.packs.loader import RulePack, load_builtin
from faultline.providers.base import Outcome
from faultline.providers.chain import NoProviderAvailable
from faultline.repos.projects import ProjectRecord, ProjectRepo
from faultline.runs.orchestrator import RunOutcome, _failure_payload

log = logging.getLogger("faultline.runs.project")

# A smoke run is what CI executes on every push. Two free Gemini accounts supply
# roughly 10-20 full audits a day across every user combined, so a pull request
# cannot cost a full one.
SMOKE_CASES = 8
FULL_CASES = 24

MULTI_TURN_PER_RULE = {"SP-05": 1, "SP-02": 1}


def target_from_project(project: ProjectRecord) -> Target:
    """Build a runnable target from a stored system prompt.

    The whole prompt is treated as confidential. We did not author it and cannot
    know which parts the user considers public, and over-reporting a leak is a far
    safer error than missing one.
    """
    return Target(
        id=project.id,
        name=project.name,
        model=project.target_model,
        canary=project.canary,
        sections=[
            PromptSection(
                name="prompt", confidential=True, text=project.system_prompt or ""
            )
        ],
    )


class ProjectRunner:
    def __init__(self, store, repo: ProjectRepo | None = None) -> None:
        self._store = store
        self._repo = repo or ProjectRepo()

    def execute(self, job_id: str, payload: dict[str, Any]) -> None:
        project = self._repo.get(payload["project_id"], payload["user_id"])
        if project is None:
            self._store.finish(
                job_id, JobStatus.FAILED, error="That project no longer exists."
            )
            return

        pack = load_builtin(project.pack_id)
        target = target_from_project(project)
        size = payload.get("size", "smoke")
        wanted = SMOKE_CASES if size == "smoke" else FULL_CASES

        try:
            cases, version = self._pinned_cases(job_id, project, pack, target, wanted)
        except NoProviderAvailable as e:
            self._defer(job_id, RunOutcome(), target, pack, str(e))
            return

        if not cases:
            self._store.finish(
                job_id,
                JobStatus.FAILED,
                error="No attack cases could be generated for this project.",
            )
            return

        if version:
            self._store.set_test_set(job_id, version)

        cases = cases[:wanted]
        self._run_cases(job_id, project, pack, target, cases, version, size)

    # -- pinned test set ---------------------------------------------------

    def _pinned_cases(
        self, job_id, project: ProjectRecord, pack: RulePack, target: Target, wanted: int
    ) -> tuple[list[AttackCase], str]:
        existing = self._repo.latest_test_set(project.id)
        if existing and len(existing[2]) >= wanted:
            _, version, raw = existing
            log.info("reusing pinned test set %s for project %s", version, project.id)
            return [AttackCase(**c) for c in raw], version

        self._store.heartbeat(job_id, 0, "looking at how your bot responds")
        recon_chain = config.build_chain(config.target_step(project.target_model))
        observation = observe(recon_chain, target)

        self._store.heartbeat(job_id, 0, "writing attacks for your rules")
        generator = AttackGenerator(
            config.build_chain(config.attacker_chain_steps()),
            config.GENERATION_MODEL,
            observation=observation,
        )
        selected = [r for r in pack.rules if not project.rule_ids or r.id in project.rule_ids]
        narrowed = RulePack(
            id=pack.id, name=pack.name, version=pack.version,
            summary=pack.summary, rules=selected or pack.rules,
        )
        test_set = generator.generate(
            narrowed, target,
            total_cases=max(wanted, FULL_CASES),
            multi_turn_per_rule=MULTI_TURN_PER_RULE,
        )
        if not test_set.cases:
            return [], ""

        self._repo.save_test_set(
            project.id, test_set.version,
            [c.model_dump(mode="json") for c in test_set.cases],
        )
        log.info(
            "pinned test set %s for project %s (%d cases)",
            test_set.version, project.id, len(test_set.cases),
        )
        return test_set.cases, test_set.version

    # -- execution ---------------------------------------------------------

    def _run_cases(
        self, job_id, project, pack, target, cases, version, size
    ) -> None:
        target_chain = config.build_chain(config.target_step(project.target_model))
        judge_chain = config.build_chain(config.judge_chain_steps())
        executor = Executor(target_chain, target)
        judge = Judge(
            judge_chain, config.JUDGE_FIRST_PASS_MODEL, config.JUDGE_ESCALATION_MODEL
        )

        outcome = RunOutcome()
        total = len(cases) * 2
        done = 0

        for index, case in enumerate(cases, start=1):
            if self._cancelled(job_id):
                self._finish(
                    job_id, project, pack, outcome, size,
                    version=version, status=JobStatus.CANCELLED,
                )
                return

            self._store.heartbeat(
                job_id, done, f"attacking · case {index} of {len(cases)}"
            )
            try:
                run = executor.run_case(case)
            except NoProviderAvailable as e:
                self._defer(job_id, outcome, target, pack, str(e))
                return
            done += 1

            if not run.gradeable:
                outcome.incomplete += 1
                done += 1
                if run.outcome is Outcome.DEFERRED:
                    self._defer(
                        job_id, outcome, target, pack,
                        "the daily free allowance is spent",
                    )
                    return
                continue

            self._store.heartbeat(
                job_id, done, f"grading · case {index} of {len(cases)}"
            )
            try:
                judged = judge.judge(case, run, pack.rule(case.rule_id))
            except NoProviderAvailable as e:
                self._defer(job_id, outcome, target, pack, str(e))
                return
            done += 1

            outcome.techniques.append((case.technique, case.is_multi_turn))
            if judged.judged_by:
                outcome.providers.append(judged.judged_by)
            if judged.verdict is None:
                outcome.incomplete += 1
            elif judged.failed:
                outcome.graded += 1
                outcome.failures.append(_failure_payload(judged, pack))
            else:
                outcome.graded += 1
                if judged.verdict.verdict.value == "flagged":
                    outcome.flagged += 1
                else:
                    outcome.passes += 1

        outcome.degraded = bool(judge_chain.failovers)
        self._store.heartbeat(job_id, total, "done")
        self._finish(job_id, project, pack, outcome, size, version=version)

    # -- finishing ---------------------------------------------------------

    def _grades(self, pack: RulePack, outcome: RunOutcome) -> list[DimensionGrade]:
        return [
            grade_dimension(
                pack.id,
                failures=len(outcome.failures),
                graded=outcome.graded,
                incomplete=outcome.incomplete,
            )
        ]

    def _finish(
        self,
        job_id,
        project,
        pack,
        outcome,
        size,
        version: str | None = None,
        status: JobStatus = JobStatus.DONE,
    ) -> None:
        target = target_from_project(project)
        payload = outcome.as_payload(target, pack)
        grades = self._grades(pack, outcome)
        payload["grades"] = [
            {
                "dimension": g.dimension, "letter": g.letter, "reason": g.reason,
                "failureRate": g.failure_rate, "graded": g.graded,
                "failures": g.failures, "incomplete": g.incomplete,
            }
            for g in grades
        ]
        payload["testSetVersion"] = version
        payload["isSimulated"] = project.is_simulated

        # A cancelled run keeps the work already completed, but does not get a
        # grade: a partial suite would understate or overstate the target and
        # would pollute the trend with a point that means nothing.
        if status is JobStatus.DONE:
            self._repo.save_grades(job_id, project.id, size, grades)
        else:
            payload.pop("grades", None)
        self._repo.touch(project.id)
        self._store.finish(job_id, status, result=payload)

    def _cancelled(self, job_id: str) -> bool:
        job = self._store.get(job_id)
        return job is not None and job.status is JobStatus.CANCELLED

    def _defer(self, job_id, outcome, target, pack, reason: str) -> None:
        """Out of allowance is a state of ours, not a verdict on the target."""
        log.warning("run %s deferred: %s", job_id, reason)
        self._store.finish(
            job_id, JobStatus.DEFERRED,
            result=outcome.as_payload(target, pack), error=reason,
        )
