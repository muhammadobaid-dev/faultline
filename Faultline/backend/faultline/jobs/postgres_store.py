"""The Postgres job store.

Same five methods as the SQLite store, which is the point of the seam. What changes
is how a job is claimed: `SELECT ... FOR UPDATE SKIP LOCKED` lets several workers
pull from one queue without blocking each other or handing the same job out twice,
which SQLite could only approximate with an exclusive transaction.

Claiming also picks up rows whose lease has expired. A worker that dies - or a free
Render instance that spins down mid-run - leaves a lease behind rather than a job
stranded at sixty percent, and the next claim reclaims it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from faultline.db.engine import session_factory
from faultline.jobs.store import Job, JobStatus

log = logging.getLogger("faultline.jobs.pg")

LEASE_SECONDS = 120


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_job(row: Any) -> Job:
    return Job(
        id=row.id,
        kind=row.kind,
        status=JobStatus(row.status),
        payload=row.payload or {},
        progress_done=row.progress_done,
        progress_total=row.progress_total,
        stage=row.stage or "",
        result=row.result,
        error=row.error,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
        project_id=getattr(row, "project_id", None),
    )


class PostgresJobStore:
    """Async. The API and the worker both hold one of these."""

    def __init__(self, sessions=None) -> None:
        self._session_factory = sessions

    @property
    def _sessions(self):
        """Resolved on first use, not at construction.

        Importing the app must not require a database - the test suite, the CLI and
        `--help` all import it, and only some of them have one.
        """
        if self._session_factory is None:
            self._session_factory = session_factory()
        return self._session_factory


    # Raw SQL bypasses SQLModel's Python-side defaults, so every NOT NULL column
    # is supplied explicitly here rather than relied upon.
    async def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        total: int,
        *,
        project_id: str | None = None,
        test_set_id: str | None = None,
        test_set_version: str | None = None,
        size: str = "full",
    ) -> Job:
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        """
                        INSERT INTO runs (id, kind, size, project_id, test_set_id,
                                          test_set_version, status, stage, payload,
                                          progress_done, progress_total,
                                          created_at, updated_at)
                        VALUES (replace(gen_random_uuid()::text, '-', ''),
                                :kind, :size, :project_id,
                                :test_set_id, :version, 'queued', 'queued',
                                CAST(:payload AS jsonb), 0, :total, now(), now())
                        RETURNING *
                        """
                    ),
                    {
                        "kind": kind,
                        "size": size,
                        "project_id": project_id,
                        "test_set_id": test_set_id,
                        "version": test_set_version,
                        "payload": _json(payload),
                        "total": total,
                    },
                )
            ).one()
            await s.commit()
        log.info("queued %s run %s (%d units)", kind, row.id, total)
        return _to_job(row)

    async def get(self, job_id: str) -> Job | None:
        async with self._sessions() as s:
            row = (
                await s.execute(text("SELECT * FROM runs WHERE id = :id"), {"id": job_id})
            ).first()
        return _to_job(row) if row else None

    async def claim(self) -> Job | None:
        """Take one claimable run, skipping rows another worker already holds."""
        lease = _now() + timedelta(seconds=LEASE_SECONDS)
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        """
                        WITH claimable AS (
                            SELECT id FROM runs
                            WHERE status = 'queued'
                               OR (status = 'running' AND leased_until < now())
                            ORDER BY created_at
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        UPDATE runs SET status = 'running', leased_until = :lease,
                                        updated_at = now()
                        WHERE id IN (SELECT id FROM claimable)
                        RETURNING *
                        """
                    ),
                    {"lease": lease},
                )
            ).first()
            await s.commit()
        if row is None:
            return None
        return _to_job(row)

    async def set_test_set(self, job_id: str, test_set_version: str) -> None:
        """Record which pinned test set a run actually used.

        Not known when the run is queued - the runner may have to generate and pin
        one first - but load-bearing afterwards: a grade diff is only meaningful
        between runs sharing a version, because comparing across versions measures
        the questions changing rather than the answers.
        """
        async with self._sessions() as s:
            await s.execute(
                text(
                    "UPDATE runs SET test_set_version = :v, updated_at = now()"
                    " WHERE id = :id"
                ),
                {"v": test_set_version, "id": job_id},
            )
            await s.commit()

    async def heartbeat(self, job_id: str, done: int, stage: str) -> None:
        """Publish progress and extend the lease. This is what the UI polls."""
        lease = _now() + timedelta(seconds=LEASE_SECONDS)
        async with self._sessions() as s:
            await s.execute(
                text(
                    "UPDATE runs SET progress_done = :done, stage = :stage,"
                    " leased_until = :lease, updated_at = now() WHERE id = :id"
                ),
                {"done": done, "stage": stage, "lease": lease, "id": job_id},
            )
            await s.commit()

    async def finish(
        self,
        job_id: str,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._sessions() as s:
            await s.execute(
                text(
                    "UPDATE runs SET status = :status,"
                    " result = CAST(:result AS jsonb), error = :error,"
                    " stage = :stage, leased_until = NULL, updated_at = now()"
                    " WHERE id = :id"
                ),
                {
                    "status": status.value,
                    "result": _json(result) if result is not None else None,
                    "error": error,
                    "stage": status.value,
                    "id": job_id,
                },
            )
            await s.commit()
        log.info("run %s finished: %s", job_id, status.value)

    async def cancel(self, job_id: str) -> bool:
        """Cooperative: completed work is kept, nothing new is started."""
        async with self._sessions() as s:
            result = await s.execute(
                text(
                    "UPDATE runs SET status = 'cancelled', updated_at = now()"
                    " WHERE id = :id AND status IN ('queued','running')"
                ),
                {"id": job_id},
            )
            await s.commit()
        return result.rowcount > 0

    # -- anonymous rate limiting ------------------------------------------

    async def bump_rate(self, bucket: str, day: str) -> int:
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        "INSERT INTO rate_limits (bucket, day, count) VALUES (:b,:d,1)"
                        " ON CONFLICT (bucket, day) DO UPDATE SET count ="
                        " rate_limits.count + 1 RETURNING count"
                    ),
                    {"b": bucket, "d": day},
                )
            ).one()
            await s.commit()
        return row.count

    async def rate(self, bucket: str, day: str) -> int:
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT count FROM rate_limits WHERE bucket = :b AND day = :d"
                    ),
                    {"b": bucket, "d": day},
                )
            ).first()
        return row.count if row else 0


def _json(value: Any) -> str:
    import json

    return json.dumps(value)
