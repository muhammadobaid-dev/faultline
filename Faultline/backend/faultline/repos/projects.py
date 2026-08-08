"""Data access for projects, test sets, runs and grades.

Plain SQL through the async engine rather than the ORM session-per-request pattern.
The queries here are small, explicit and read like what they do, and the alternative
buys lazy loading we would never use.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from faultline.db.engine import session_factory
from faultline.grading import DimensionGrade

log = logging.getLogger("faultline.repos")


@dataclass
class ProjectRecord:
    id: str
    user_id: str
    name: str
    target_kind: str
    target_model: str
    system_prompt: str | None
    canary: str | None
    pack_id: str
    pack_version: int
    rule_ids: list[str]
    created_at: str
    updated_at: str

    @property
    def is_simulated(self) -> bool:
        """A pasted prompt is graded on our stand-in model, not the user's own
        deployment, so its results must never back a public claim."""
        return self.target_kind == "pasted_prompt"


def _project(row: Any) -> ProjectRecord:
    return ProjectRecord(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        target_kind=row.target_kind,
        target_model=row.target_model,
        system_prompt=row.system_prompt,
        canary=row.canary,
        pack_id=row.pack_id,
        pack_version=row.pack_version,
        rule_ids=row.rule_ids or [],
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


class ProjectRepo:
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


    async def create(
        self,
        *,
        user_id: str,
        name: str,
        system_prompt: str,
        target_model: str,
        rule_ids: list[str],
        canary: str | None,
        pack_id: str,
        pack_version: int,
    ) -> ProjectRecord:
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        """
                        INSERT INTO projects
                          (id, user_id, name, target_kind, target_model,
                           system_prompt, canary, pack_id, pack_version, rule_ids,
                           created_at, updated_at)
                        VALUES
                          (replace(gen_random_uuid()::text, '-', ''), :user_id, :name,
                           'pasted_prompt', :model, :prompt, :canary, :pack,
                           :pack_version, CAST(:rules AS jsonb), now(), now())
                        RETURNING *
                        """
                    ),
                    {
                        "user_id": user_id,
                        "name": name,
                        "model": target_model,
                        "prompt": system_prompt,
                        "canary": canary,
                        "pack": pack_id,
                        "pack_version": pack_version,
                        "rules": json.dumps(rule_ids),
                    },
                )
            ).one()
            await s.commit()
        return _project(row)

    async def list_for_user(self, user_id: str) -> list[ProjectRecord]:
        async with self._sessions() as s:
            rows = (
                await s.execute(
                    text(
                        "SELECT * FROM projects WHERE user_id = :u"
                        " ORDER BY updated_at DESC"
                    ),
                    {"u": user_id},
                )
            ).all()
        return [_project(r) for r in rows]

    async def get(self, project_id: str, user_id: str) -> ProjectRecord | None:
        """Scoped by user on purpose: an id alone must never be enough to read
        someone else's project."""
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text("SELECT * FROM projects WHERE id = :i AND user_id = :u"),
                    {"i": project_id, "u": user_id},
                )
            ).first()
        return _project(row) if row else None

    async def delete(self, project_id: str, user_id: str) -> bool:
        async with self._sessions() as s:
            result = await s.execute(
                text("DELETE FROM projects WHERE id = :i AND user_id = :u"),
                {"i": project_id, "u": user_id},
            )
            await s.execute(
                text("DELETE FROM runs WHERE project_id = :i"), {"i": project_id}
            )
            await s.commit()
        return result.rowcount > 0

    async def touch(self, project_id: str) -> None:
        async with self._sessions() as s:
            await s.execute(
                text("UPDATE projects SET updated_at = now() WHERE id = :i"),
                {"i": project_id},
            )
            await s.commit()

    # -- pinned test sets --------------------------------------------------

    async def save_test_set(
        self, project_id: str, version: str, cases: list[dict[str, Any]]
    ) -> str:
        """Idempotent on (project, version): the same content is the same test set."""
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        """
                        INSERT INTO test_sets (id, project_id, version, cases, created_at)
                        VALUES (replace(gen_random_uuid()::text, '-', ''), :p, :v,
                                CAST(:cases AS jsonb), now())
                        RETURNING id
                        """
                    ),
                    {"p": project_id, "v": version, "cases": json.dumps(cases)},
                )
            ).one()
            await s.commit()
        return row.id

    async def latest_test_set(self, project_id: str) -> tuple[str, str, list] | None:
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT id, version, cases FROM test_sets WHERE project_id = :p"
                        " ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"p": project_id},
                )
            ).first()
        return (row.id, row.version, row.cases) if row else None

    # -- runs and grades ---------------------------------------------------

    async def runs_for_project(self, project_id: str, limit: int = 50) -> list[dict]:
        async with self._sessions() as s:
            rows = (
                await s.execute(
                    text(
                        """
                        SELECT r.id, r.status, r.size, r.test_set_version,
                               r.progress_done, r.progress_total, r.stage,
                               r.created_at, r.updated_at, r.error,
                               r.result -> 'failures' AS failures
                        FROM runs r
                        WHERE r.project_id = :p
                        ORDER BY r.created_at DESC
                        LIMIT :n
                        """
                    ),
                    {"p": project_id, "n": limit},
                )
            ).all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "size": r.size,
                "testSetVersion": r.test_set_version,
                "done": r.progress_done,
                "total": r.progress_total,
                "stage": r.stage,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "finishedAt": r.updated_at.isoformat() if r.updated_at else None,
                "error": r.error,
                "failureCount": len(r.failures or []) if r.failures is not None else 0,
            }
            for r in rows
        ]

    async def latest_completed_run(self, project_id: str) -> dict | None:
        """The most recent finished run's result, for the fix loop to read from."""
        async with self._sessions() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT id, result FROM runs WHERE project_id = :p"
                        " AND status = 'done' AND result IS NOT NULL"
                        " AND kind = 'project'"
                        " ORDER BY updated_at DESC LIMIT 1"
                    ),
                    {"p": project_id},
                )
            ).first()
        return row.result if row else None

    async def save_grades(
        self,
        run_id: str,
        project_id: str | None,
        size: str,
        grades: list[DimensionGrade],
    ) -> None:
        if not grades:
            return
        async with self._sessions() as s:
            for g in grades:
                await s.execute(
                    text(
                        """
                        INSERT INTO grades (id, run_id, project_id, dimension, letter,
                                            failure_rate, graded, failures, incomplete,
                                            size, created_at)
                        VALUES (replace(gen_random_uuid()::text, '-', ''), :run, :proj,
                                :dim, :letter, :rate, :graded, :failures, :incomplete,
                                :size, now())
                        """
                    ),
                    {
                        "run": run_id,
                        "proj": project_id,
                        "dim": g.dimension,
                        "letter": g.letter,
                        "rate": g.failure_rate,
                        "graded": g.graded,
                        "failures": g.failures,
                        "incomplete": g.incomplete,
                        "size": size,
                    },
                )
            await s.commit()

    async def trend(self, project_id: str, limit: int = 30) -> list[dict]:
        """Grades over time, oldest first, for plotting.

        Carries the test-set version on every point so the UI can mark where the
        questions changed - a grade move across that line is not a regression.
        """
        async with self._sessions() as s:
            rows = (
                await s.execute(
                    text(
                        """
                        SELECT g.run_id, g.dimension, g.letter, g.failure_rate,
                               g.graded, g.failures, g.size, g.created_at,
                               r.test_set_version
                        FROM grades g
                        JOIN runs r ON r.id = g.run_id
                        WHERE g.project_id = :p
                        ORDER BY g.created_at ASC
                        LIMIT :n
                        """
                    ),
                    {"p": project_id, "n": limit},
                )
            ).all()
        return [
            {
                "runId": r.run_id,
                "dimension": r.dimension,
                "letter": r.letter,
                "failureRate": float(r.failure_rate),
                "graded": r.graded,
                "failures": r.failures,
                "size": r.size,
                "at": r.created_at.isoformat() if r.created_at else None,
                "testSetVersion": r.test_set_version,
            }
            for r in rows
        ]

    async def latest_grades(self, project_id: str) -> list[dict]:
        async with self._sessions() as s:
            rows = (
                await s.execute(
                    text(
                        """
                        SELECT DISTINCT ON (dimension)
                               dimension, letter, failure_rate, graded, failures,
                               incomplete, size, run_id, created_at
                        FROM grades
                        WHERE project_id = :p
                        ORDER BY dimension, created_at DESC
                        """
                    ),
                    {"p": project_id},
                )
            ).all()
        return [
            {
                "dimension": r.dimension,
                "letter": r.letter,
                "failureRate": float(r.failure_rate),
                "graded": r.graded,
                "failures": r.failures,
                "incomplete": r.incomplete,
                "size": r.size,
                "runId": r.run_id,
                "at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
