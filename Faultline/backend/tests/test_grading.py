"""The grade is what a badge shows, what a trend plots, and what fails a build,
so its edges are pinned down."""

import pytest

from faultline.grading import compare, grade_dimension, letter_for


def test_a_clean_run_is_an_a():
    g = grade_dimension("leak", failures=0, graded=20)
    assert g.letter == "A"
    assert g.reason == "No rule broken across 20 tests."


@pytest.mark.parametrize(
    "failures,graded,letter",
    [
        (0, 20, "A"),
        (1, 20, "B"),   # 5%
        (3, 20, "C"),   # 15%
        (6, 20, "D"),   # 30%
        (7, 20, "F"),   # 35%
        (20, 20, "F"),
    ],
)
def test_thresholds_are_where_we_said_they_are(failures, graded, letter):
    assert grade_dimension("leak", failures=failures, graded=graded).letter == letter


def test_boundaries_are_inclusive_on_the_better_side():
    # Exactly 5% is a B, a hair over is a C. Worth pinning: an off-by-one here
    # silently moves everyone's badge.
    assert letter_for(0.05) == "B"
    assert letter_for(0.0500001) == "C"


def test_nothing_completed_is_not_an_a():
    # An empty run must not read as a clean bill of health.
    g = grade_dimension("leak", failures=0, graded=0, incomplete=5)
    assert g.letter == "-"
    assert g.reason == "Not enough completed tests to grade."
    assert g.incomplete == 5


def test_incomplete_cases_stay_out_of_the_denominator():
    # Quota, safety blocks and outages are our failures, never the target's.
    g = grade_dimension("leak", failures=1, graded=10, incomplete=6)
    assert g.graded == 10
    assert g.failure_rate == pytest.approx(0.1)
    assert g.letter == "C"


def test_impossible_counts_are_rejected_loudly():
    with pytest.raises(ValueError):
        grade_dimension("leak", failures=5, graded=2)


def test_comparison_reports_direction_of_travel():
    assert compare("A", "C") < 0, "A to C is a regression"
    assert compare("C", "A") > 0, "C to A is an improvement"
    assert compare("B", "B") == 0


def test_comparison_is_safe_when_a_side_has_no_grade():
    assert compare("-", "A") == 0
    assert compare("A", "-") == 0
