"""Persistent schema.

Identity is owned by Auth.js on the frontend, which manages its own `users`,
`accounts` and `sessions` tables in this same database. The backend therefore holds
`user_id` as a plain indexed column with no foreign key: two migration systems
pointing at one table is a worse problem than the referential integrity it would buy,
and the trusted proxy is what asserts the identity in the first place.

`Grade` is a row per dimension rather than three columns. A dimension is data, so the
deferred hallucination grade becomes an insert rather than a migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(*, index: bool = False, nullable: bool = False) -> Column:
    """A timezone-aware timestamp column.

    SQLModel maps a bare `datetime` to `TIMESTAMP WITHOUT TIME ZONE`, which would
    silently drop the offset from the aware values we write - and lease expiry is
    compared across processes, so a dropped offset is a stranded job.
    """
    return Column(DateTime(timezone=True), index=index, nullable=nullable)


# Enum-valued columns are stored as text rather than as native Postgres enums.
# A native enum turns "add a run size" or "add a dimension" into an ALTER TYPE
# migration, and leaves types behind on downgrade that collide with the next
# upgrade. The values are still validated in Python by the Enum itself.


class TargetKind(str, Enum):
    PUNCHBAG = "punchbag"
    PASTED_PROMPT = "pasted_prompt"


class RunKind(str, Enum):
    PUNCHBAG = "punchbag"  # anonymous, not attached to a project
    PROJECT = "project"


class RunSize(str, Enum):
    """Smoke runs are what CI executes on every push.

    A full audit costs 50-90 provider requests, and two free Gemini accounts supply
    roughly 10-20 of those per day across every user combined. A pull request cannot
    cost that, so CI runs a small pinned subset and the grade records which size
    produced it - a badge must never overstate the evidence behind it.
    """

    SMOKE = "smoke"
    FULL = "full"


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(index=True)
    name: str
    target_kind: TargetKind = Field(default=TargetKind.PASTED_PROMPT, sa_type=String)
    target_model: str
    # Present for a pasted-prompt target. Results from one are graded on our
    # stand-in model rather than the user's deployment, so they are barred from
    # backing a public Trust Page - see `is_simulated` on the run.
    system_prompt: str | None = None
    canary: str | None = None
    pack_id: str = "system-prompt-leak"
    pack_version: int = 4
    rule_ids: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now, sa_column=_ts())
    updated_at: datetime = Field(default_factory=_now, sa_column=_ts())


class TestSet(SQLModel, table=True):
    """A pinned collection of attack cases.

    `version` is a content hash. A grade diff is only ever computed between runs
    sharing one, because comparing across versions would attribute a change in the
    questions to a change in the answers.
    """

    __tablename__ = "test_sets"

    id: str = Field(default_factory=_uuid, primary_key=True)
    project_id: str = Field(index=True)
    version: str = Field(index=True)
    cases: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now, sa_column=_ts())


class Run(SQLModel, table=True):
    """Both the run record and the queue row.

    Keeping them as one table is the point of a database-backed queue: the row is the
    single source of truth, so a worker that dies leaves an expired lease that another
    reclaims, rather than a run stranded at sixty percent.
    """

    __tablename__ = "runs"

    id: str = Field(default_factory=_uuid, primary_key=True)
    kind: RunKind = Field(default=RunKind.PUNCHBAG, sa_type=String)
    size: RunSize = Field(default=RunSize.FULL, sa_type=String)
    project_id: str | None = Field(default=None, index=True)
    test_set_id: str | None = None
    test_set_version: str | None = Field(default=None, index=True)

    status: str = Field(default="queued", index=True)
    stage: str = ""
    progress_done: int = 0
    progress_total: int = 0

    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = None

    leased_until: datetime | None = Field(default=None, sa_column=_ts(nullable=True))
    created_at: datetime = Field(default_factory=_now, sa_column=_ts(index=True))
    updated_at: datetime = Field(default_factory=_now, sa_column=_ts())


class Grade(SQLModel, table=True):
    """One dimension's letter for one run."""

    __tablename__ = "grades"

    id: str = Field(default_factory=_uuid, primary_key=True)
    run_id: str = Field(index=True)
    project_id: str | None = Field(default=None, index=True)
    dimension: str = Field(index=True)
    letter: str
    failure_rate: float
    graded: int
    failures: int
    incomplete: int
    size: RunSize = Field(default=RunSize.FULL, sa_type=String)
    created_at: datetime = Field(default_factory=_now, sa_column=_ts(index=True))


class RateLimit(SQLModel, table=True):
    __tablename__ = "rate_limits"

    bucket: str = Field(primary_key=True)
    day: str = Field(primary_key=True)
    count: int = 0


# Claiming scans for queued work and for leases that have expired; one index serves
# both halves of that query.
Index("runs_claimable", Run.__table__.c.status, Run.__table__.c.leased_until)

CREATE_EXTENSIONS = (text("CREATE EXTENSION IF NOT EXISTS vector"),)
