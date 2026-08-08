"""Propose a fix, then prove it on the same questions.

Takes the leaks from a project's most recent run, asks for a hardened system prompt,
and re-runs the identical pinned cases against the patched version. The result is a
before-and-after on the same exam rather than a suggestion the developer has to go and
verify themselves.

Nothing is saved to the project. The patch is a proposal the developer reads, diffs,
and applies if they agree - Faultline does not silently rewrite the thing it is
grading, because a tool that edits its own subject cannot honestly grade it.
"""

from __future__ import annotations

import logging
from typing import Any

from faultline import config
from faultline.domain import AttackCase
from faultline.execution.runner import Executor
from faultline.execution.targets import PromptSection, Target
from faultline.jobs.store import JobStatus
from faultline.judging.judge import Judge
from faultline.packs.loader import load_builtin
from faultline.providers.chain import NoProviderAvailable
from faultline.remediation.patcher import VerifiedPatch, propose
from faultline.repos.projects import ProjectRepo
from faultline.runs.project_runner import SMOKE_CASES, target_from_project

log = logging.getLogger("faultline.runs.patch")


class PatchRunner:
    def __init__(self, store, repo: ProjectRepo | None = None) -> None:
        self._store = store
        self._repo = repo or ProjectRepo()

    def execute(self, job_id: str, payload: dict[str, Any]) -> None:
        project = self._repo.get(payload["project_id"], payload["user_id"])
        if project is None:
            self._store.finish(job_id, JobStatus.FAILED, error="That project no longer exists.")
            return

        failures = payload.get("failures") or []
        if not failures:
            self._store.finish(
                job_id,
                JobStatus.FAILED,
                error="There are no leaks to fix. Run the suite first.",
            )
            return

        pinned = self._repo.latest_test_set(project.id)
        if not pinned:
            self._store.finish(
                job_id,
                JobStatus.FAILED,
                error="No pinned test set to verify against. Run the suite first.",
            )
            return
        _, version, raw_cases = pinned
        cases = [AttackCase(**c) for c in raw_cases][:SMOKE_CASES]

        pack = load_builtin(project.pack_id)
        total = 1 + len(cases) * 2

        self._store.heartbeat(job_id, 0, "reading what got through")
        try:
            proposal = propose(
                config.build_chain(config.attacker_chain_steps()),
                config.GENERATION_MODEL,
                project.system_prompt or "",
                failures,
            )
        except NoProviderAvailable as e:
            self._store.finish(job_id, JobStatus.DEFERRED, error=str(e))
            return

        if proposal is None:
            self._store.finish(
                job_id,
                JobStatus.FAILED,
                error="Couldn't produce a patch we'd stand behind. Try again shortly.",
            )
            return

        # The patched prompt is a target in its own right, graded exactly as the
        # original was so the two numbers are comparable.
        patched_target = Target(
            id=f"{project.id}-patched",
            name=f"{project.name} (patched)",
            model=project.target_model,
            canary=project.canary,
            sections=[
                PromptSection(name="prompt", confidential=True, text=proposal.patched_prompt)
            ],
        )

        executor = Executor(
            config.build_chain(config.target_step(project.target_model)), patched_target
        )
        judge = Judge(
            config.build_chain(config.judge_chain_steps()),
            config.JUDGE_FIRST_PASS_MODEL,
            config.JUDGE_ESCALATION_MODEL,
        )

        done = 1
        after: list[dict[str, Any]] = []
        graded = 0

        for index, case in enumerate(cases, start=1):
            self._store.heartbeat(
                job_id, done, f"re-testing the patch · case {index} of {len(cases)}"
            )
            try:
                run = executor.run_case(case)
            except NoProviderAvailable as e:
                self._store.finish(job_id, JobStatus.DEFERRED, error=str(e))
                return
            done += 1

            if not run.gradeable:
                done += 1
                continue

            try:
                judged = judge.judge(case, run, pack.rule(case.rule_id))
            except NoProviderAvailable as e:
                self._store.finish(job_id, JobStatus.DEFERRED, error=str(e))
                return
            done += 1

            if judged.verdict is None:
                continue
            graded += 1
            if judged.failed:
                after.append(
                    {
                        "id": case.id,
                        "ruleId": case.rule_id,
                        "rationale": judged.verdict.rationale,
                    }
                )

        before_ids = {f.get("id") for f in failures}
        verified = VerifiedPatch(
            proposal=proposal,
            before_failures=len(failures),
            after_failures=len(after),
            graded=graded,
            still_failing=[a for a in after if a["id"] in before_ids],
            newly_failing=[a for a in after if a["id"] not in before_ids],
        )

        self._store.heartbeat(job_id, total, "done")
        self._store.finish(
            job_id,
            JobStatus.DONE,
            result={
                "kind": "patch",
                "verdict": verified.verdict,
                "improved": verified.improved,
                "closed": verified.closed,
                "beforeFailures": verified.before_failures,
                "afterFailures": verified.after_failures,
                "graded": verified.graded,
                "summary": proposal.summary,
                "changes": proposal.changes,
                "patchedPrompt": proposal.patched_prompt,
                "originalPrompt": project.system_prompt,
                "stillFailing": verified.still_failing,
                "newlyFailing": verified.newly_failing,
                "testSetVersion": version,
            },
        )
        log.info("patch for project %s: %s", project.id, verified.verdict)
