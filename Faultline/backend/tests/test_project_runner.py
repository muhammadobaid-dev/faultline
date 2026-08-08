"""Unit tests for the project run pipeline.

Written after a positional-argument mix-up passed `JobStatus` where `project` was
expected and only surfaced at the very end of a real run, after every provider call
had already been paid for. These use fakes so the wiring is checked in milliseconds
rather than in quota.
"""

from types import SimpleNamespace

import pytest

from faultline.grading import grade_dimension
from faultline.jobs.store import JobStatus
from faultline.packs.loader import load_builtin
from faultline.repos.projects import ProjectRecord
from faultline.runs.orchestrator import RunOutcome
from faultline.runs.project_runner import ProjectRunner, target_from_project

PACK = load_builtin("system-prompt-leak")


def a_project(**kw) -> ProjectRecord:
    base = dict(
        id="p1", user_id="u1", name="Support bot", target_kind="pasted_prompt",
        target_model="gemini-3.5-flash-lite",
        system_prompt="You are a support bot. Internal code: ZEBRA-9.",
        canary=None, pack_id="system-prompt-leak", pack_version=4,
        rule_ids=["SP-01"], created_at="", updated_at="",
    )
    return ProjectRecord(**{**base, **kw})


class FakeStore:
    def __init__(self, status=JobStatus.RUNNING):
        self.finished: list[tuple] = []
        self.beats: list[tuple] = []
        self._status = status

    def heartbeat(self, job_id, done, stage):
        self.beats.append((done, stage))

    def finish(self, job_id, status, result=None, error=None):
        self.finished.append((status, result, error))

    def get(self, job_id):
        return SimpleNamespace(status=self._status)


class FakeRepo:
    def __init__(self, project=None):
        self.project = project
        self.saved_grades: list = []
        self.touched = 0

    def get(self, project_id, user_id):
        return self.project

    def save_grades(self, run_id, project_id, size, grades):
        self.saved_grades.append((run_id, project_id, size, grades))

    def touch(self, project_id):
        self.touched += 1


def test_a_missing_project_fails_the_run_without_spending_anything():
    store, repo = FakeStore(), FakeRepo(project=None)
    ProjectRunner(store, repo).execute("job1", {"project_id": "gone", "user_id": "u1"})

    status, _, error = store.finished[0]
    assert status is JobStatus.FAILED
    assert "no longer exists" in error


def test_finishing_records_the_grade_and_the_pinned_version():
    """The bug this file exists for: the success path passed JobStatus where the
    project belonged, so every run died after all its provider calls."""
    project = a_project()
    store, repo = FakeStore(), FakeRepo(project)
    outcome = RunOutcome(graded=8, passes=6, failures=[{"id": "c1"}, {"id": "c2"}])

    ProjectRunner(store, repo)._finish(
        "job1", project, PACK, outcome, "smoke", version="abc123"
    )

    status, result, _ = store.finished[0]
    assert status is JobStatus.DONE
    assert result["testSetVersion"] == "abc123"
    assert result["isSimulated"] is True
    assert result["grades"][0]["letter"] == "D"  # 2 of 8 is 25%
    assert repo.saved_grades and repo.saved_grades[0][2] == "smoke"
    assert repo.touched == 1


def test_a_cancelled_run_keeps_its_work_but_gets_no_grade():
    # A partial suite would pollute the trend with a point that means nothing.
    project = a_project()
    store, repo = FakeStore(), FakeRepo(project)
    outcome = RunOutcome(graded=3, passes=3)

    ProjectRunner(store, repo)._finish(
        "job1", project, PACK, outcome, "smoke", status=JobStatus.CANCELLED
    )

    status, result, _ = store.finished[0]
    assert status is JobStatus.CANCELLED
    assert "grades" not in result
    assert repo.saved_grades == [], "a cancelled run must not be graded"


def test_the_whole_pasted_prompt_is_treated_as_confidential():
    # We did not author it and cannot know which parts the user considers public.
    # Over-reporting a leak is a much safer error than missing one.
    target = target_from_project(a_project())
    assert target.confidential_text.strip() == (a_project().system_prompt or "").strip()
    assert target.public_text == ""


def test_the_target_carries_the_project_identity():
    target = target_from_project(a_project(name="Atlas", target_model="m1"))
    assert target.name == "Atlas"
    assert target.model == "m1"
    assert target.is_simulated is True


@pytest.mark.parametrize(
    "failures,graded,letter", [(0, 8, "A"), (1, 8, "C"), (4, 8, "F")]
)
def test_the_grade_follows_the_run(failures, graded, letter):
    outcome = RunOutcome(graded=graded, failures=[{"id": str(i)} for i in range(failures)])
    grades = ProjectRunner(FakeStore(), FakeRepo(a_project()))._grades(PACK, outcome)
    assert grades[0].letter == letter
    assert grades[0].dimension == PACK.id


def test_grade_dimension_and_runner_agree():
    outcome = RunOutcome(graded=10, failures=[{"id": "1"}], incomplete=3)
    mine = ProjectRunner(FakeStore(), FakeRepo(a_project()))._grades(PACK, outcome)[0]
    assert mine == grade_dimension(PACK.id, failures=1, graded=10, incomplete=3)
