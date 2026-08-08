"""Authenticated project endpoints.

Identity is asserted by the Next.js proxy, which holds the session and forwards the
user id alongside a shared secret. The browser never reaches these routes directly,
so the token is the boundary: without it, a request is refused before it touches a
query.
"""

from __future__ import annotations

import logging
import os
import re

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from faultline.packs.loader import load_builtin
from faultline.repos.projects import ProjectRepo
from faultline.runs.project_runner import FULL_CASES, SMOKE_CASES

log = logging.getLogger("faultline.api.projects")

router = APIRouter(prefix="/projects", tags=["projects"])
repo = ProjectRepo()

MAX_PROMPT_CHARS = 20_000
MAX_PROJECTS_PER_USER = 20


def require_user(
    x_faultline_token: str | None, x_faultline_user: str | None
) -> str:
    """The trust boundary between the frontend and this service."""
    expected = os.environ.get("FAULTLINE_INTERNAL_TOKEN", "")
    if not expected:
        # Refusing is the safe default: an unset secret must never mean "allow".
        raise HTTPException(503, "This deployment is not configured for sign-in.")
    if x_faultline_token != expected:
        raise HTTPException(401, "Not signed in.")
    if not x_faultline_user:
        raise HTTPException(401, "Not signed in.")
    return x_faultline_user


class CreateProject(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(min_length=20, max_length=MAX_PROMPT_CHARS)
    rule_ids: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        cleaned = re.sub(r"\s+", " ", v).strip()
        if not cleaned:
            raise ValueError("A project needs a name.")
        return cleaned


class ProjectView(BaseModel):
    id: str
    name: str
    targetKind: str
    targetModel: str
    ruleIds: list[str]
    isSimulated: bool
    createdAt: str
    updatedAt: str
    promptPreview: str


def _view(p) -> ProjectView:
    prompt = (p.system_prompt or "").strip()
    return ProjectView(
        id=p.id,
        name=p.name,
        targetKind=p.target_kind,
        targetModel=p.target_model,
        ruleIds=p.rule_ids,
        isSimulated=p.is_simulated,
        createdAt=p.created_at,
        updatedAt=p.updated_at,
        # Never the whole prompt: it is the user's confidential material and the
        # list view has no reason to carry it over the wire.
        promptPreview=prompt[:140] + ("…" if len(prompt) > 140 else ""),
    )


@router.get("")
async def list_projects(
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> dict:
    user = require_user(x_faultline_token, x_faultline_user)
    projects = await repo.list_for_user(user)
    return {"projects": [_view(p).model_dump() for p in projects]}


@router.post("", status_code=201)
async def create_project(
    body: CreateProject,
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> dict:
    user = require_user(x_faultline_token, x_faultline_user)

    existing = await repo.list_for_user(user)
    if len(existing) >= MAX_PROJECTS_PER_USER:
        raise HTTPException(
            409,
            f"You've reached {MAX_PROJECTS_PER_USER} projects. Delete one to add another.",
        )

    pack = load_builtin("system-prompt-leak")
    valid = {r.id for r in pack.rules}
    rules = [r for r in body.rule_ids if r in valid] or sorted(valid)

    project = await repo.create(
        user_id=user,
        name=body.name,
        system_prompt=body.system_prompt,
        target_model="gemini-3.5-flash-lite",
        rule_ids=rules,
        canary=None,
        pack_id=pack.id,
        pack_version=pack.version,
    )
    log.info("user %s created project %s", user, project.id)
    return _view(project).model_dump()


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> dict:
    user = require_user(x_faultline_token, x_faultline_user)
    project = await repo.get(project_id, user)
    if project is None:
        raise HTTPException(404, "No such project.")
    return {
        "project": _view(project).model_dump(),
        "runs": await repo.runs_for_project(project_id),
        "grades": await repo.latest_grades(project_id),
        "trend": await repo.trend(project_id),
        "sizes": {"smoke": SMOKE_CASES, "full": FULL_CASES},
    }


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    x_faultline_token: str | None = Header(default=None),
    x_faultline_user: str | None = Header(default=None),
) -> None:
    user = require_user(x_faultline_token, x_faultline_user)
    if not await repo.delete(project_id, user):
        raise HTTPException(404, "No such project.")
