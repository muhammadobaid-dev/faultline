"""The job queue, behind one narrow seam.

An Attack Run cannot happen inside a request: it takes minutes, needs its progress
tracked, and must survive the process dying - a free Render service spins down when
idle and cold-starts on the next request. FastAPI's built-in background tasks are the
wrong tool for exactly those reasons.

`JobStore` is the seam. The SQLite implementation below gives real transactional claim
semantics with no credentials and no setup. Swapping it for Postgres
`FOR UPDATE SKIP LOCKED` is one class implementing the same five methods, which is
why the seam exists.

Claiming is idempotent and lease-based rather than fire-and-forget: a worker that dies
mid-run leaves a lease that expires, and the job is reclaimed rather than stranded at
sixty percent forever.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger("faultline.jobs")

LEASE_SECONDS = 120


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    # Our own allowance ran out. Never a statement about the target.
    DEFERRED = "deferred"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in (
            JobStatus.DONE,
            JobStatus.FAILED,
            JobStatus.DEFERRED,
            JobStatus.CANCELLED,
        )


@dataclass
class Job:
    id: str
    kind: str
    status: JobStatus
    payload: dict[str, Any]
    progress_done: int
    progress_total: int
    stage: str
    result: dict[str, Any] | None
    error: str | None
    created_at: str
    updated_at: str
    project_id: str | None = None

    @property
    def percent(self) -> int:
        if self.progress_total <= 0:
            return 0
        return min(100, round(100 * self.progress_done / self.progress_total))


class JobStore(Protocol):
    def enqueue(self, kind: str, payload: dict[str, Any], total: int) -> Job: ...
    def get(self, job_id: str) -> Job | None: ...
    def claim(self) -> Job | None: ...
    def heartbeat(self, job_id: str, done: int, stage: str) -> None: ...
    def finish(self, job_id: str, status: JobStatus, **kw: Any) -> None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL,
  progress_done INTEGER NOT NULL DEFAULT 0,
  progress_total INTEGER NOT NULL DEFAULT 0,
  stage TEXT NOT NULL DEFAULT '',
  result TEXT,
  error TEXT,
  leased_until TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS rate_limit (
  bucket TEXT NOT NULL,
  day TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (bucket, day)
);
"""


class SqliteJobStore(JobStore):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            kind=row["kind"],
            status=JobStatus(row["status"]),
            payload=json.loads(row["payload"]),
            progress_done=row["progress_done"],
            progress_total=row["progress_total"],
            stage=row["stage"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def enqueue(self, kind: str, payload: dict[str, Any], total: int) -> Job:
        job_id = uuid.uuid4().hex[:16]
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO jobs (id, kind, status, payload, progress_total, stage,"
                " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (job_id, kind, JobStatus.QUEUED.value, json.dumps(payload), total,
                 "queued", now, now),
            )
        log.info("queued %s job %s (%d units)", kind, job_id, total)
        return self.get(job_id)  # type: ignore[return-value]

    def get(self, job_id: str) -> Job | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def claim(self) -> Job | None:
        """Take the oldest claimable job under an exclusive transaction.

        Also reclaims a job whose lease expired, which is how a run survives the
        worker dying rather than sitting at sixty percent forever.
        """
        now = datetime.now(timezone.utc)
        lease = (now + timedelta(seconds=LEASE_SECONDS)).isoformat()
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute(
                "SELECT * FROM jobs WHERE status = ? OR (status = ? AND leased_until < ?)"
                " ORDER BY created_at LIMIT 1",
                (JobStatus.QUEUED.value, JobStatus.RUNNING.value, now.isoformat()),
            ).fetchone()
            if row is None:
                c.execute("COMMIT")
                return None
            if row["status"] == JobStatus.RUNNING.value:
                log.warning("reclaiming job %s from an expired lease", row["id"])
            c.execute(
                "UPDATE jobs SET status = ?, leased_until = ?, updated_at = ?"
                " WHERE id = ?",
                (JobStatus.RUNNING.value, lease, now.isoformat(), row["id"]),
            )
            c.execute("COMMIT")
        return self.get(row["id"])

    def heartbeat(self, job_id: str, done: int, stage: str) -> None:
        """Extend the lease and publish progress. This is what the UI polls."""
        lease = (
            datetime.now(timezone.utc) + timedelta(seconds=LEASE_SECONDS)
        ).isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE jobs SET progress_done = ?, stage = ?, leased_until = ?,"
                " updated_at = ? WHERE id = ?",
                (done, stage, lease, _now(), job_id),
            )

    def finish(
        self,
        job_id: str,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE jobs SET status = ?, result = ?, error = ?, stage = ?,"
                " leased_until = NULL, updated_at = ? WHERE id = ?",
                (
                    status.value,
                    json.dumps(result) if result is not None else None,
                    error,
                    status.value,
                    _now(),
                    job_id,
                ),
            )
        log.info("job %s finished: %s", job_id, status.value)

    def cancel(self, job_id: str) -> bool:
        """Cooperative cancel: completed work is kept, nothing new is started."""
        with self._conn() as c:
            cur = c.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status IN (?,?)",
                (JobStatus.CANCELLED.value, _now(), job_id,
                 JobStatus.QUEUED.value, JobStatus.RUNNING.value),
            )
            return cur.rowcount > 0

    # -- anonymous rate limiting ------------------------------------------

    def bump_rate(self, bucket: str, day: str) -> int:
        with self._conn() as c:
            c.execute(
                "INSERT INTO rate_limit (bucket, day, count) VALUES (?,?,1)"
                " ON CONFLICT(bucket, day) DO UPDATE SET count = count + 1",
                (bucket, day),
            )
            row = c.execute(
                "SELECT count FROM rate_limit WHERE bucket = ? AND day = ?",
                (bucket, day),
            ).fetchone()
        return row["count"]

    def rate(self, bucket: str, day: str) -> int:
        with self._conn() as c:
            row = c.execute(
                "SELECT count FROM rate_limit WHERE bucket = ? AND day = ?",
                (bucket, day),
            ).fetchone()
        return row["count"] if row else 0
