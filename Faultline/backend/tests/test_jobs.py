"""The queue is what lets a run outlive its process, so its claim semantics are
tested rather than assumed."""

from datetime import datetime, timedelta, timezone

from faultline.jobs.store import JobStatus, SqliteJobStore
from faultline.runs.orchestrator import load_punchbag_cases, select_cases


def store(tmp_path) -> SqliteJobStore:
    return SqliteJobStore(tmp_path / "jobs.sqlite3")


def test_a_queued_job_can_be_claimed_once(tmp_path):
    s = store(tmp_path)
    s.enqueue("punchbag", {}, total=4)
    assert s.claim() is not None
    assert s.claim() is None, "a claimed job must not be handed out twice"


def test_progress_is_published_for_the_poller(tmp_path):
    s = store(tmp_path)
    job = s.enqueue("punchbag", {}, total=8)
    s.claim()
    s.heartbeat(job.id, 4, "grading - case 2 of 4")
    fetched = s.get(job.id)
    assert fetched.percent == 50
    assert fetched.stage == "grading - case 2 of 4"


def test_a_job_survives_a_restart(tmp_path):
    # The whole point of a DB-backed queue: Render spins down when idle.
    job = store(tmp_path).enqueue("punchbag", {"count": 3}, total=6)
    assert store(tmp_path).get(job.id).payload == {"count": 3}


def test_an_expired_lease_is_reclaimed_rather_than_stranded(tmp_path):
    s = store(tmp_path)
    job = s.enqueue("punchbag", {}, total=4)
    s.claim()
    assert s.claim() is None

    # Simulate a worker that died mid-run.
    stale = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with s._conn() as c:  # noqa: SLF001
        c.execute("UPDATE jobs SET leased_until = ? WHERE id = ?", (stale, job.id))

    reclaimed = s.claim()
    assert reclaimed is not None and reclaimed.id == job.id


def test_finishing_records_the_result(tmp_path):
    s = store(tmp_path)
    job = s.enqueue("punchbag", {}, total=2)
    s.finish(job.id, JobStatus.DONE, result={"failures": []})
    done = s.get(job.id)
    assert done.status is JobStatus.DONE
    assert done.status.terminal
    assert done.result == {"failures": []}


def test_cancelling_is_cooperative_and_only_applies_to_live_jobs(tmp_path):
    s = store(tmp_path)
    job = s.enqueue("punchbag", {}, total=2)
    assert s.cancel(job.id) is True
    assert s.get(job.id).status is JobStatus.CANCELLED
    assert s.cancel(job.id) is False, "a finished job cannot be cancelled again"


def test_deferred_is_terminal_and_distinct_from_failed(tmp_path):
    # Out of allowance is a state of ours, never a verdict on the target.
    s = store(tmp_path)
    job = s.enqueue("punchbag", {}, total=2)
    s.finish(job.id, JobStatus.DEFERRED, error="daily free allowance is spent")
    fetched = s.get(job.id)
    assert fetched.status is JobStatus.DEFERRED
    assert fetched.status.terminal


def test_rate_counters_are_per_bucket_and_per_day(tmp_path):
    s = store(tmp_path)
    assert s.bump_rate("ip:1.2.3.4", "2026-07-25") == 1
    assert s.bump_rate("ip:1.2.3.4", "2026-07-25") == 2
    assert s.rate("ip:5.6.7.8", "2026-07-25") == 0
    assert s.rate("ip:1.2.3.4", "2026-07-26") == 0


# -- case selection ---------------------------------------------------------


def test_punchbag_cases_load_and_cover_several_rules():
    cases = load_punchbag_cases()
    assert len(cases) >= 5
    assert len({c.rule_id for c in cases}) >= 3


def test_selection_is_deterministic_for_a_seed():
    cases = load_punchbag_cases()
    assert [c.id for c in select_cases(cases, None, 4, seed=7)] == [
        c.id for c in select_cases(cases, None, 4, seed=7)
    ]


def test_selection_respects_the_chosen_rules():
    cases = load_punchbag_cases()
    picked = select_cases(cases, ["SP-03"], 5, seed=1)
    assert picked and all(c.rule_id == "SP-03" for c in picked)


def test_selection_falls_back_rather_than_returning_nothing():
    # A rule with no punchbag cases must not produce an empty, instantly-green run.
    picked = select_cases(load_punchbag_cases(), ["SP-99"], 3, seed=1)
    assert len(picked) == 3
