"""Turning verdicts into a grade.

Mechanical failure-rate thresholds, chosen over severity weighting because a grade
has to be explainable in one sentence and a pull-request comment has to be legible.
Severity is shown per failure in Visual Replay and deliberately not folded in here.

The denominator is completed gradings only. A case we could not finish - our quota,
a safety block, a provider outage - is excluded entirely rather than counted as a
pass or a fail, because none of those is a statement about the target.
"""

from __future__ import annotations

from dataclasses import dataclass

# (letter, inclusive upper bound on the failure rate)
THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("A", 0.0),
    ("B", 0.05),
    ("C", 0.15),
    ("D", 0.30),
    ("F", 1.0),
)


@dataclass(frozen=True)
class DimensionGrade:
    dimension: str
    letter: str
    failure_rate: float
    graded: int
    failures: int
    incomplete: int

    @property
    def reason(self) -> str:
        """The one-line explanation shown beside the letter."""
        if self.graded == 0:
            return "Not enough completed tests to grade."
        if self.failures == 0:
            return f"No rule broken across {self.graded} tests."
        share = f"{self.failures} of {self.graded} tests"
        return f"Broke a rule in {share}."


def letter_for(failure_rate: float) -> str:
    for letter, ceiling in THRESHOLDS:
        if failure_rate <= ceiling:
            return letter
    return "F"


def grade_dimension(
    dimension: str, *, failures: int, graded: int, incomplete: int = 0
) -> DimensionGrade:
    """Grade one dimension.

    `graded` counts cases that produced a verdict. `incomplete` is reported so a
    thin run is visibly thin rather than quietly flattering.
    """
    if graded < 0 or failures < 0 or failures > graded:
        raise ValueError(f"nonsensical counts: {failures} failures of {graded} graded")

    if graded == 0:
        # Nothing completed is not an A. An ungraded dimension has no letter.
        return DimensionGrade(dimension, "-", 0.0, 0, 0, incomplete)

    rate = failures / graded
    return DimensionGrade(dimension, letter_for(rate), rate, graded, failures, incomplete)


def compare(before: str, after: str) -> int:
    """Direction of travel between two letters.

    Positive is an improvement, negative a regression, zero unchanged. This is what
    decides whether a pull-request check passes.
    """
    order = [letter for letter, _ in THRESHOLDS]
    if before not in order or after not in order:
        return 0
    return order.index(before) - order.index(after)
