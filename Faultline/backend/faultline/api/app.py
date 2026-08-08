"""The HTTP surface.

Anything that starts or inspects an Attack Run goes through here. The browser polls
`GET /runs/{id}` a few seconds apart, which is deliberately boring: it works through
every layer we have, and on Render the poll is itself what wakes a service that has
spun down.

Runs are rows in Postgres, claimed with FOR UPDATE SKIP LOCKED by a worker task. The
row is the source of truth, so a run interrupted by a restart is reclaimed on the next
claim rather than lost. The worker executes the pipeline in a thread - it makes
blocking provider calls one after another - and reaches the database through a facade
that submits coroutines back to this loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from faultline import config
from faultline.api.projects import repo as project_repo
from faultline.api.projects import require_user, router as projects_router
from faultline.jobs.bridge import SyncFacade
from faultline.jobs.postgres_store import PostgresJobStore
from faultline.jobs.store import JobStatus
from faultline.packs.loader import load_builtin
from faultline.providers.budget import pacific_day, seconds_until_reset
from faultline.runs.orchestrator import (
    DEFAULT_CASE_COUNT,
    RunOrchestrator,
    load_punchbag_cases,
)
from faultline.runs.patch_runner import PatchRunner
from faultline.runs.project_runner import FULL_CASES, SMOKE_CASES, ProjectRunner

log = logging.getLogger("faultline.api")

# Anonymous protection. Per-IP so one visitor cannot monopolise the demo, and a
# global daily cap so the public punchbag can never exhaust the allowance that
# signed-in runs draw on.
PUNCHBAG_RUNS_PER_IP_PER_DAY = 5
PUNCHBAG_RUNS_PER_DAY = 15
PROJECT_RUNS_PER_USER_PER_DAY = 6

store = PostgresJobStore()
_stop = asyncio.Event()


def _migrate() -> None:
    """Apply migrations at startup.

    Render's free tier has no pre-deploy hook, so this is where the schema is
    brought up to date. Safe on a single instance; with several, this would need
    to move to a release step.
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(config.BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(config.BACKEND_ROOT / "migrations"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.environ.get("FAULTLINE_DATABASE_URL"):
        try:
            # In a thread: alembic's env.py calls asyncio.run, which cannot nest.
            await asyncio.to_thread(_migrate)
            log.info("database schema is up to date")
        except Exception:
            log.exception("migrations failed; the service will start read-degraded")
    worker = asyncio.create_task(_drain(), name="drain")
    log.info("queue worker started")
    yield
    _stop.set()
    worker.cancel()


def _allowed_origins() -> list[str]:
    configured = os.environ.get("FAULTLINE_ALLOWED_ORIGINS", "").strip()
    local = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if not configured:
        return local
    return local + [o.strip() for o in configured.split(",") if o.strip()]


app = FastAPI(title="Faultline", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.include_router(projects_router)


class StartPunchbagRun(BaseModel):
    rule_ids: list[str] = Field(default_factory=list)
    count: int = DEFAULT_CASE_COUNT


class StartProjectRun(BaseModel):
    size: str = "smoke"


class RunView(BaseModel):
    id: str
    status: str
    stage: str
    done: int
    total: int
    percent: int
    result: dict[str, Any] | None = None
    error: str | None = None
    replay_of: str | None = None
    # Lets the run page offer to fix what it just found.
    project_id: str | None = None


def _client_ip(request: Request, forwarded: str | None) -> str:
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _view(job) -> RunView:
    return RunView(
        id=job.id,
        status=job.status.value,
        stage=job.stage,
        done=job.progress_done,
        total=job.progress_total,
        percent=job.percent,
        result=job.result,
        error=job.error,
        project_id=job.project_id,
    )


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Also the wake-up endpoint for the keep-alive cron."""
    database = "unconfigured"
    if os.environ.get("FAULTLINE_DATABASE_URL"):
        try:
            await store.rate("healthz", pacific_day())
            database = "ok"
        except Exception:
            database = "unreachable"
    return {
        "ok": database != "unreachable",
        "database": database,
        "day": pacific_day(),
        "resets_in": seconds_until_reset(),
    }


@app.get("/packs")
async def packs() -> dict[str, Any]:
    pack = load_builtin("system-prompt-leak")
    punchbag_rules = {c.rule_id for c in load_punchbag_cases()}
    return {
        "id": pack.id,
        "name": pack.name,
        "version": pack.version,
        "summary": pack.summary.strip(),
        "rules": [
            {
                "id": r.id,
                "title": r.title,
                "rule": r.rule.strip(),
                "inPunchbag": r.id in punchbag_rules,
            }
            for r in pack.rules
        ],
    }


@app.post("/punchbag/runs", response_model=RunView)
async def start_punchbag_run(
    body: StartPunchbagRun,
    request: Request,
    x_forwarded_for: str | None = Header(default=None),
) -> RunView:
    ip = _client_ip(request, x_forwarded_for)
    day = pacific_day()

    if await store.rate(f"ip:{ip}", day) >= PUNCHBAG_RUNS_PER_IP_PER_DAY:
        raise HTTPException(429, "You have used today's demo runs. Try again tomorrow.")
    if await store.rate("punchbag:global", day) >= PUNCHBAG_RUNS_PER_DAY:
        recorded = await _most_recent_punchbag_run()
        if recorded is None:
            raise HTTPException(
                503, "The live demo is resting until tomorrow. Nothing recorded yet."
            )
        view = _view(recorded)
        view.replay_of = recorded.id
        return view

    count = max(1, min(body.count, 8))
    job = await store.enqueue(
        "punchbag",
        {"pack_id": "system-prompt-leak", "rule_ids": body.rule_ids, "count": count},
        total=count * 2,
    )
    await store.bump_rate(f"ip:{ip}", day)
    await store.bump_rate("punchbag:global", day)
    return _view(job)


@app.post("/projects/{project_id}/runs", response_model=RunView, status_code=201)
async def start_project_run(
    project_id: str,
    body: StartProjectRun,
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> RunView:
    user = require_user(x_faultline_token, x_faultline_user)
    project = await project_repo.get(project_id, user)
    if project is None:
        raise HTTPException(404, "No such project.")

    day = pacific_day()
    if await store.rate(f"user:{user}", day) >= PROJECT_RUNS_PER_USER_PER_DAY:
        raise HTTPException(
            429,
            "You've used today's runs. The free model allowance resets at midnight "
            "Pacific.",
        )

    size = "full" if body.size == "full" else "smoke"
    cases = FULL_CASES if size == "full" else SMOKE_CASES
    job = await store.enqueue(
        "project",
        {"project_id": project_id, "user_id": user, "size": size},
        total=cases * 2,
        project_id=project_id,
        size=size,
    )
    await store.bump_rate(f"user:{user}", day)
    log.info("user %s started a %s run on project %s", user, size, project_id)
    return _view(job)


@app.post("/projects/{project_id}/patch", response_model=RunView, status_code=201)
async def propose_patch(
    project_id: str,
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> RunView:
    """Propose a hardened prompt and verify it on the same pinned cases."""
    user = require_user(x_faultline_token, x_faultline_user)
    project = await project_repo.get(project_id, user)
    if project is None:
        raise HTTPException(404, "No such project.")

    latest = await project_repo.latest_completed_run(project_id)
    failures = (latest or {}).get("failures") or []
    if not failures:
        raise HTTPException(
            409, "There are no leaks to fix yet. Run the suite first."
        )

    day = pacific_day()
    if await store.rate(f"user:{user}", day) >= PROJECT_RUNS_PER_USER_PER_DAY:
        raise HTTPException(
            429,
            "You've used today's runs. The free model allowance resets at midnight "
            "Pacific.",
        )

    job = await store.enqueue(
        "patch",
        {"project_id": project_id, "user_id": user, "failures": failures},
        total=1 + SMOKE_CASES * 2,
        project_id=project_id,
        size="smoke",
    )
    await store.bump_rate(f"user:{user}", day)
    return _view(job)


@app.get("/runs/{job_id}", response_model=RunView)
async def get_run(job_id: str) -> RunView:
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(404, "No such run.")
    return _view(job)


@app.post("/runs/{job_id}/cancel", response_model=RunView)
async def cancel_run(job_id: str) -> RunView:
    if not await store.cancel(job_id):
        raise HTTPException(409, "That run has already finished.")
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(404, "No such run.")
    return _view(job)


async def _most_recent_punchbag_run():
    from sqlalchemy import text

    from faultline.db.engine import session_factory

    async with session_factory()() as s:
        row = (
            await s.execute(
                text(
                    "SELECT id FROM runs WHERE kind = 'punchbag' AND status = 'done'"
                    " AND result IS NOT NULL ORDER BY updated_at DESC LIMIT 1"
                )
            )
        ).first()
    return await store.get(row.id) if row else None


# -- the worker -----------------------------------------------------------


async def _drain() -> None:
    loop = asyncio.get_running_loop()
    sync_store = SyncFacade(store, loop)
    sync_repo = SyncFacade(project_repo, loop)
    punchbag = RunOrchestrator(sync_store, anonymous=True)
    projects = ProjectRunner(sync_store, sync_repo)
    patches = PatchRunner(sync_store, sync_repo)

    while not _stop.is_set():
        try:
            job = await store.claim()
        except Exception:
            log.exception("could not claim a run; backing off")
            await asyncio.sleep(5)
            continue

        if job is None:
            await asyncio.sleep(1.0)
            continue

        log.info("draining %s run %s", job.kind, job.id)
        runner = {"project": projects, "patch": patches}.get(job.kind, punchbag)
        try:
            # In a thread: the pipeline blocks on provider calls and must not
            # occupy the loop that is serving progress polls.
            await asyncio.to_thread(runner.execute, job.id, job.payload)
        except Exception as e:
            log.exception("run %s failed", job.id)
            await store.finish(job.id, JobStatus.FAILED, error=str(e))
