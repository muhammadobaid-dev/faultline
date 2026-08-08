"""Executing one Attack Run as a job.

Cases are pinned, not generated at run time: a visitor's run costs no generation
requests, finishes in seconds, and is reproducible. The run walks each case through
the target, judges it, and heartbeats progress after every step so the polling UI has
something honest to show.

Progress is reported in units of work rather than percent, so the frontend can say
"3 of 10" instead of a spinner that means nothing.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from faultline import config
from faultline.coverage import (
    TIER_LABELS,
    CoverageReport,
    Family,
    Tier,
)
from faultline.coverage import report as coverage_report
from faultline.domain import AttackCase, JudgedCase
from faultline.execution.runner import Executor
from faultline.execution.targets import Target, load_target
from faultline.jobs.store import JobStatus, JobStore
from faultline.judging.judge import Judge
from faultline.packs.loader import RulePack, load_builtin
from faultline.providers.base import Outcome
from faultline.providers.chain import NoProviderAvailable

log = logging.getLogger("faultline.runs")

PUNCHBAG_TARGET = config.FIXTURES_DIR / "targets" / "punchbag.toml"
PUNCHBAG_CASES = config.FIXTURES_DIR / "punchbag_cases.json"
DEFAULT_CASE_COUNT = 5


def load_punchbag_cases() -> list[AttackCase]:
    raw = json.loads(PUNCHBAG_CASES.read_text(encoding="utf-8"))
    return [AttackCase(**c) for c in raw["cases"]]


def select_cases(
    cases: list[AttackCase], rule_ids: list[str] | None, count: int, seed: int | None
) -> list[AttackCase]:
    """Pick the cases a run will use.

    Deterministic when seeded, so a shared run link replays the same attacks.
    """
    pool = [c for c in cases if not rule_ids or c.rule_id in rule_ids] or cases
    rng = random.Random(seed)
    picked = pool[:] if len(pool) <= count else rng.sample(pool, count)
    picked.sort(key=lambda c: c.id)
    return picked


@dataclass
class RunOutcome:
    failures: list[dict[str, Any]] = field(default_factory=list)
    graded: int = 0
    passes: int = 0
    flagged: int = 0
    incomplete: int = 0
    providers: list[str] = field(default_factory=list)
    degraded: bool = False
    # (technique, was_multi_turn) per graded case, for the coverage report.
    techniques: list[tuple[str, bool]] = field(default_factory=list)

    def coverage(self, tier: Tier = Tier.STANDARD) -> CoverageReport:
        return coverage_report(
            self.techniques,
            graded=self.graded,
            failures=len(self.failures),
            incomplete=self.incomplete,
            tier=tier,
        )

    def as_payload(
        self, target: Target, pack: RulePack, tier: Tier = Tier.STANDARD
    ) -> dict[str, Any]:
        cover = self.coverage(tier)
        return {
            # Confidence in the assessment, kept separate from the grade, which is
            # about the assistant. Conflating them is how a clean run misleads.
            "coverage": {
                "headline": cover.headline,
                "confidence": cover.confidence.value,
                "caveat": cover.caveat,
                "nextStep": cover.next_step,
                "familiesCovered": cover.families_covered,
                "familiesKnown": len(Family),
                "exercised": cover.exercised,
                "untested": cover.untested,
                "tier": int(tier),
                "tierLabel": TIER_LABELS[tier],
            },
            "pack": {"id": pack.id, "name": pack.name, "version": pack.version},
            "target": {"id": target.id, "name": target.name},
            "judge": ", ".join(sorted(set(self.providers))) or "unknown",
            "graded": self.graded,
            "passes": self.passes,
            "flagged": self.flagged,
            "incomplete": self.incomplete,
            "degraded": self.degraded,
            "failures": self.failures,
        }


def _failure_payload(judged: JudgedCase, pack: RulePack) -> dict[str, Any]:
    rule = pack.rule(judged.case.rule_id)
    verdict = judged.verdict
    assert verdict is not None
    return {
        "id": judged.case.id,
        "ruleId": judged.case.rule_id,
        "ruleTitle": rule.title,
        "packName": pack.name,
        "packVersion": pack.version,
        "technique": judged.case.technique,
        "turns": [
            {"user": e.user, "assistant": e.assistant or ""}
            for e in judged.run.transcript
        ],
        "spanStart": judged.span_start,
        "spanEnd": judged.span_end,
        "spanIsVerbatim": judged.span_is_verbatim,
        "rationale": verdict.rationale,
        "saferResponse": verdict.suggested_safer_response,
        "confidence": verdict.confidence.value,
        "judgedBy": judged.judged_by or "unknown",
        "escalated": judged.escalated,
    }


class RunOrchestrator:
    """Runs one job to completion, heartbeating as it goes."""

    def __init__(self, store: JobStore, *, anonymous: bool = True) -> None:
        self._store = store
        self._anonymous = anonymous

    def execute(self, job_id: str, payload: dict[str, Any]) -> None:
        pack = load_builtin(payload.get("pack_id", "system-prompt-leak"))
        target = load_target(Path(payload.get("target_path", str(PUNCHBAG_TARGET))))
        cases = select_cases(
            load_punchbag_cases(),
            payload.get("rule_ids"),
            payload.get("count", DEFAULT_CASE_COUNT),
            payload.get("seed"),
        )

        # The target never fails over: swapping the model under test would change
        # what is being measured. The judge walks the full chain.
        target_chain = config.build_chain(
            config.target_step(target.model), anonymous=self._anonymous
        )
        judge_chain = config.build_chain(
            config.judge_chain_steps(), anonymous=self._anonymous
        )

        executor = Executor(target_chain, target)
        judge = Judge(
            judge_chain, config.JUDGE_FIRST_PASS_MODEL, config.JUDGE_ESCALATION_MODEL
        )

        outcome = RunOutcome()
        total = len(cases) * 2  # one attack unit and one grading unit per case
        done = 0

        for index, case in enumerate(cases, start=1):
            if self._cancelled(job_id):
                self._store.finish(job_id, JobStatus.CANCELLED,
                                   result=outcome.as_payload(target, pack))
                return

            self._store.heartbeat(job_id, done, f"attacking · case {index} of {len(cases)}")
            try:
                run = executor.run_case(case)
            except NoProviderAvailable as e:
                self._defer(job_id, outcome, target, pack, str(e))
                return
            done += 1

            if not run.gradeable:
                outcome.incomplete += 1
                done += 1
                # Our own failure, never a mark against the target.
                if run.outcome is Outcome.DEFERRED:
                    self._defer(job_id, outcome, target, pack,
                                "the daily free allowance is spent")
                    return
                continue

            self._store.heartbeat(job_id, done, f"grading · case {index} of {len(cases)}")
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
        self._store.finish(job_id, JobStatus.DONE, result=outcome.as_payload(target, pack))

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
