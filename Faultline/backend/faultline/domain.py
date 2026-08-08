"""The shared vocabulary of an Attack Run.

Internally these are adversarial evaluation objects; the words a user sees are Rules,
Attack Run, Grade, and Replay. Keep that split honest in anything user-facing.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum

from pydantic import BaseModel, Field

from faultline.providers.base import Outcome

MAX_TURNS = 5  # a bounded escalation, never an open-ended conversation


class AttackCase(BaseModel):
    """One adversarial test: a scripted sequence of user messages against one rule.

    Turns are written up front rather than generated adaptively. That costs realism
    and buys reproducibility, which the pinned-test-set comparability guarantee needs
    - and it is a fifth of the requests an adaptive attacker would spend.
    """

    id: str
    rule_id: str
    technique: str
    turns: list[str] = Field(min_length=1, max_length=MAX_TURNS)
    # Engineered to sit on a rubric's boundary, where a careful person could argue
    # either way and `flagged` is the honest verdict. Used to measure whether the
    # judge's escalation path fires at all.
    borderline: bool = False

    @property
    def is_multi_turn(self) -> bool:
        return len(self.turns) > 1


class TestSet(BaseModel):
    """A pinned, versioned collection of cases.

    Regenerated only on explicit refresh or a change of rule selection. Grade diffs
    are only ever computed between runs sharing a `version`, because comparing across
    test sets would attribute a change in the questions to a change in the answers.
    """

    __test__ = False  # a domain model, not a pytest fixture class

    pack_id: str
    pack_version: int
    target_id: str
    target_model: str
    generation_model: str
    cases: list[AttackCase]

    @property
    def version(self) -> str:
        """Content identity. The model ids are part of it deliberately: a different
        model answering the same questions is a different baseline."""
        payload = json.dumps(
            {
                "pack": f"{self.pack_id}@{self.pack_version}",
                "target": f"{self.target_id}:{self.target_model}",
                "generator": self.generation_model,
                "cases": [c.model_dump(mode="json") for c in self.cases],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:12]

    def for_rule(self, rule_id: str) -> list[AttackCase]:
        return [c for c in self.cases if c.rule_id == rule_id]


class Exchange(BaseModel):
    user: str
    assistant: str | None = None


class CaseRun(BaseModel):
    """What the target actually did when the case was executed."""

    case_id: str
    rule_id: str
    outcome: Outcome
    transcript: list[Exchange] = Field(default_factory=list)
    detail: str | None = None

    # Mechanical ground truth, established without a judge or a human label.
    canary_leaked: bool = False
    verbatim_overlap: int = 0

    @property
    def final_response(self) -> str | None:
        return self.transcript[-1].assistant if self.transcript else None

    @property
    def gradeable(self) -> bool:
        """Only a completed exchange can be graded. Everything else - a safety block,
        our own quota, a 503 - is our failure and must never score the target down."""
        return self.outcome is Outcome.OK and bool(self.final_response)

    def as_transcript_text(self) -> str:
        parts = []
        for i, ex in enumerate(self.transcript, start=1):
            label = f"TURN {i} " if len(self.transcript) > 1 else ""
            parts.append(f"--- {label}ATTACKER ---\n{ex.user}")
            parts.append(f"--- {label}ASSISTANT ---\n{ex.assistant or '(no response)'}")
        return "\n\n".join(parts)


class VerdictKind(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    FLAGGED = "flagged"  # genuinely borderline; escalates to the stronger judge


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(BaseModel):
    """Exactly what Visual Replay renders. The judge's output shape is dictated by its
    most important consumer: a judgment you cannot point at is not trustworthy."""

    verdict: VerdictKind
    offending_span: str = ""
    rationale: str
    suggested_safer_response: str = ""
    confidence: Confidence


class JudgedCase(BaseModel):
    case: AttackCase
    run: CaseRun
    verdict: Verdict | None = None

    judged_by: str | None = None
    escalated: bool = False
    # A span the judge invented is a correctness failure, not a matter of taste: it
    # cannot be highlighted, so Replay would have nothing to point at.
    span_is_verbatim: bool = True
    span_start: int | None = None
    span_end: int | None = None
    judge_outcome: Outcome | None = None

    @property
    def failed(self) -> bool:
        return self.verdict is not None and self.verdict.verdict is VerdictKind.FAIL

    def locate_span(self) -> None:
        """Resolve the span to character offsets so Replay can highlight it with a
        plain <mark> and no diff library."""
        response = self.run.final_response
        span = (self.verdict.offending_span or "").strip() if self.verdict else ""
        if not response or not span:
            self.span_is_verbatim = not span
            return
        start = response.find(span)
        if start == -1:
            self.span_is_verbatim = False
            return
        self.span_is_verbatim = True
        self.span_start = start
        self.span_end = start + len(span)
