"""Skill Registry API.

Membaca katalog boleh dilakukan setiap anggota tenant. Mengubahnya menuntut
`manage_integrations` — katalog skill adalah konfigurasi, bukan pekerjaan harian.

Skill sistem (`tenant_id` NULL) terlihat oleh semua tenant tetapi tidak bisa
diubah lewat API tenant.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.session import get_db
from ...repositories import audit as audit_repo
from ...repositories import skills as skill_repo

router = APIRouter(tags=["skills"])


class CreateSkillRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=96)
    display_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    version: str = Field(default="0.1.0", max_length=32)
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list, max_length=10)
    manifest: dict = Field(default_factory=dict)
    notes: str = Field(default="", max_length=500)


class NewVersionRequest(BaseModel):
    version: str = Field(min_length=5, max_length=32)
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list, max_length=10)
    manifest: dict = Field(default_factory=dict)
    notes: str = Field(default="", max_length=500)


class StatusRequest(BaseModel):
    status: str = Field(pattern="^(active|disabled|deprecated)$")


def _serialize_version(row) -> dict:
    return {
        "version": row.version,
        "status": row.status,
        "input_schema": json.loads(row.input_schema_json or "{}"),
        "output_schema": json.loads(row.output_schema_json or "{}"),
        "required_capabilities": json.loads(row.required_capabilities_json or "[]"),
        "notes": row.notes,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat(),
    }


def _serialize(skill, versions: list | None = None) -> dict:
    payload = {
        "id": skill.id,
        "slug": skill.slug,
        "display_name": skill.display_name,
        "description": skill.description,
        "status": skill.status,
        "latest_version": skill.latest_version,
        "is_system": skill.tenant_id is None,
        "created_at": skill.created_at.isoformat(),
    }
    if versions is not None:
        payload["versions"] = [_serialize_version(row) for row in versions]
    return payload


@router.get("/skills")
def list_skills(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    rows = skill_repo.list_skills(db, tenant_id)
    return {"items": [_serialize(row) for row in rows]}


@router.get("/skills/{slug}")
def get_skill(
    slug: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    skill = skill_repo.get_skill(db, tenant_id=tenant_id, slug=slug)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan.")
    return _serialize(skill, skill_repo.list_versions(db, skill.id))


@router.post("/skills", status_code=201)
def create_skill(
    payload: CreateSkillRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    try:
        skill, version = skill_repo.create_skill(
            db,
            tenant_id=tenant_id,
            slug=payload.slug,
            display_name=payload.display_name,
            description=payload.description,
            version=payload.version,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            required_capabilities=payload.required_capabilities,
            manifest=payload.manifest,
            created_by_user_id=caller.principal_id,
            notes=payload.notes,
        )
    except skill_repo.SkillError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc

    audit_repo.append_event(
        db,
        event_type="skill_registered",
        actor="user",
        scope=caller.scope,
        action="register_skill",
        resource=skill.slug,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={"version": version.version, "status": skill.status},
    )
    db.commit()
    return _serialize(skill, [version])


@router.post("/skills/{slug}/versions", status_code=201)
def add_version(
    slug: str,
    payload: NewVersionRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    skill = skill_repo.get_skill(db, tenant_id=tenant_id, slug=slug)
    if skill is None or skill.tenant_id is None:
        # Skill sistem tidak bisa diberi versi oleh tenant.
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan.")
    try:
        row = skill_repo.add_version(
            db,
            skill,
            version=payload.version,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            required_capabilities=payload.required_capabilities,
            manifest=payload.manifest,
            created_by_user_id=caller.principal_id,
            notes=payload.notes,
        )
    except skill_repo.SkillError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc

    audit_repo.append_event(
        db,
        event_type="skill_version_added",
        actor="user",
        scope=caller.scope,
        action="add_skill_version",
        resource=skill.slug,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={"version": row.version},
    )
    db.commit()
    return _serialize_version(row)


@router.post("/skills/{slug}/status")
def set_status(
    slug: str,
    payload: StatusRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    skill = skill_repo.get_skill(db, tenant_id=tenant_id, slug=slug)
    if skill is None or skill.tenant_id is None:
        raise HTTPException(status_code=404, detail="Skill tidak ditemukan.")
    previous = skill.status
    try:
        skill_repo.set_status(db, skill, payload.status)
    except skill_repo.SkillError as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc

    audit_repo.append_event(
        db,
        event_type="skill_status_changed",
        actor="user",
        scope=caller.scope,
        action="change_skill_status",
        resource=skill.slug,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={"from": previous, "to": skill.status},
    )
    db.commit()
    return _serialize(skill, skill_repo.list_versions(db, skill.id))
