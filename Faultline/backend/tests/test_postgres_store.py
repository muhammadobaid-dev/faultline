"""Integration tests for the Postgres queue.

These need a real database - the behaviour under test is FOR UPDATE SKIP LOCKED and
lease reclaim, neither of which a fake would exercise honestly. They skip when
FAULTLINE_DATABASE_URL is unset, so the unit suite still runs anywhere.
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from faultline.db.engine import session_factory
from faultline.jobs.postgres_store import PostgresJobStore
from faultline.jobs.store import JobStatus

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("FAULTLINE_DATABASE_URL"),
        reason="needs a database; set FAULTLINE_DATABASE_URL to run",
    ),
]


@pytest.fixture
def store() -> PostgresJobStore:
    return PostgresJobStore()


async def _cleanup(job_id: str) -> None:
    async with session_factory()() as s:
        await s.execute(text("DELETE FROM runs WHERE id = :id"), {"id": job_id})
        await s.commit()


async def test_a_queued_run_is_claimed_exactly_once(store):
    job = await store.enqueue("test", {"n": 1}, total=4)
    try:
        first = await store.claim()
        assert first is not None and first.id == job.id
        assert first.status is JobStatus.RUNNING
        # Another worker polling at the same moment must not get the same row.
        assert await store.claim() is None
    finally:
        await _cleanup(job.id)


async def test_progress_is_published_for_the_poller(store):
    job = await store.enqueue("test", {}, total=8)
    try:
        await store.claim()
        await store.heartbeat(job.id, 6, "grading - case 3 of 4")
        fetched = await store.get(job.id)
        assert fetched.percent == 75
        assert fetched.stage == "grading - case 3 of 4"
    finally:
        await _cleanup(job.id)


async def test_an_expired_lease_is_reclaimed(store):
    """A worker that dies leaves a lease, not a run stranded at sixty percent."""
    job = await store.enqueue("test", {}, total=4)
    try:
        await store.claim()
        assert await store.claim() is None

        stale = datetime.now(timezone.utc) - timedelta(seconds=1)
        async with session_factory()() as s:
            await s.execute(
                text("UPDATE runs SET leased_until = :t WHERE id = :id"),
                {"t": stale, "id": job.id},
            )
            await s.commit()

        reclaimed = await store.claim()
        assert reclaimed is not None and reclaimed.id == job.id
    finally:
        await _cleanup(job.id)


async def test_a_finished_run_keeps_its_result(store):
    job = await store.enqueue("test", {}, total=2)
    try:
        await store.finish(job.id, JobStatus.DONE, result={"graded": 2, "failures": []})
        done = await store.get(job.id)
        assert done.status is JobStatus.DONE
        assert done.status.terminal
        assert done.result == {"graded": 2, "failures": []}
    finally:
        await _cleanup(job.id)


async def test_deferred_is_terminal_and_carries_its_reason(store):
    # Out of allowance is a state of ours, never a verdict on the target.
    job = await store.enqueue("test", {}, total=2)
    try:
        await store.finish(job.id, JobStatus.DEFERRED, error="free allowance spent")
        fetched = await store.get(job.id)
        assert fetched.status is JobStatus.DEFERRED
        assert fetched.error == "free allowance spent"
    finally:
        await _cleanup(job.id)


async def test_cancelling_only_applies_to_live_runs(store):
    job = await store.enqueue("test", {}, total=2)
    try:
        assert await store.cancel(job.id) is True
        assert (await store.get(job.id)).status is JobStatus.CANCELLED
        assert await store.cancel(job.id) is False
    finally:
        await _cleanup(job.id)


async def test_a_cancelled_run_is_not_claimable(store):
    job = await store.enqueue("test", {}, total=2)
    try:
        await store.cancel(job.id)
        claimed = await store.claim()
        assert claimed is None or claimed.id != job.id
    finally:
        await _cleanup(job.id)


async def test_rate_counters_are_per_bucket_and_per_day(store):
    day = "1999-01-01"  # a day no real traffic will ever use
    bucket = "ip:test-suite"
    async with session_factory()() as s:
        await s.execute(text("DELETE FROM rate_limits WHERE day = :d"), {"d": day})
        await s.commit()

    assert await store.bump_rate(bucket, day) == 1
    assert await store.bump_rate(bucket, day) == 2
    assert await store.rate("ip:someone-else", day) == 0

    async with session_factory()() as s:
        await s.execute(text("DELETE FROM rate_limits WHERE day = :d"), {"d": day})
        await s.commit()
