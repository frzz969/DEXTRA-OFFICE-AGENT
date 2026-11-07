"""Policy: registri, evaluasi deterministik, dan perubahan ber-versi.

Endpoint evaluasi sengaja memanggil fungsi murni, bukan model. Kalau hasilnya
berbeda untuk masukan yang sama, itu bug — bukan kreativitas.

Perubahan aturan tidak menimpa baris lama: `rules_json` baru selalu menjadi
`PolicyVersion` baru dengan nomor lanjut. Evaluasi yang sudah tercatat tetap bisa
dipahami dengan versi aturan yang berlaku saat itu.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...governance import policy as policy_engine
from ...models.governance import Policy, PolicyEvaluation, PolicyVersion

router = APIRouter(tags=["policies"])


class EvaluateRequest(BaseModel):
    action_type: str
    recipients: list[str] = Field(default_factory=list)
    allowed_recipients: list[str] = Field(default_factory=list)
    recipient_candidates: int = 1
    at: datetime | None = None
    recipient_count: int = 1
    bulk_threshold: int = 25
    is_holiday: bool = False
    is_friday_prayer: bool = False
    contains_injection: bool = False
    #: Slug policy yang diminta dievaluasi. Bila diisi, policy itu harus milik
    #: tenant pemanggil; policy milik tenant lain → 404 (bukan dievaluasi diam-diam).
    policy_slug: str | None = None
    plan_id: str = ""


class PolicyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    scope: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None
    #: Bila diisi, dibuat `PolicyVersion` baru — bukan menimpa versi sebelumnya.
    rules_json: str | None = Field(default=None, max_length=20000)
    change_note: str = Field(default="", max_length=500)


def _resolve_policy(db: Session, slug: str, caller: CallerContext) -> Policy:
    policy = db.scalar(scope_to_tenant(select(Policy).where(Policy.slug == slug), Policy, caller))
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy tidak ditemukan.")
    return policy


@router.get("/policies")
def list_policies(
    db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    rows = db.scalars(
        scope_to_tenant(select(Policy), Policy, caller).order_by(Policy.slug)
    ).all()
    return {
        "items": [
            {
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "scope": p.scope,
                "is_active": p.is_active,
                "versions": len(p.versions),
            }
            for p in rows
        ],
        #: Penulisan hanya lewat PATCH/DELETE dengan capability `edit_policy`.
        "writable": True,
    }


@router.get("/policies/{slug}/versions")
def list_policy_versions(
    slug: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    policy = _resolve_policy(db, slug, caller)
    versions = sorted(policy.versions, key=lambda v: v.version)
    return {
        "policy_id": policy.id,
        "slug": policy.slug,
        "items": [
            {
                "id": v.id,
                "version": v.version,
                "rules_json": v.rules_json,
                "change_note": v.change_note,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.patch("/policies/{slug}")
def update_policy(
    slug: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("edit_policy")),
) -> dict:
    require_tenant(caller)
    policy = _resolve_policy(db, slug, caller)

    for name in ("title", "scope", "is_active"):
        value = getattr(payload, name)
        if value is not None:
            setattr(policy, name, value)

    created_version = None
    if payload.rules_json is not None:
        next_version = max((v.version for v in policy.versions), default=0) + 1
        created_version = PolicyVersion(
            id=new_id("pov"),
            policy_id=policy.id,
            version=next_version,
            rules_json=payload.rules_json,
            change_note=payload.change_note,
        )
        db.add(created_version)

    db.commit()
    db.refresh(policy)
    return {
        "id": policy.id,
        "slug": policy.slug,
        "title": policy.title,
        "scope": policy.scope,
        "is_active": policy.is_active,
        "versions": len(policy.versions),
        "version": created_version.version if created_version is not None else None,
    }


@router.delete("/policies/{slug}")
def delete_policy(
    slug: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("edit_policy")),
) -> dict:
    require_tenant(caller)
    policy = _resolve_policy(db, slug, caller)
    policy_id = policy.id
    db.delete(policy)
    db.commit()
    return {"deleted": True, "slug": slug, "id": policy_id}


@router.post("/policies/evaluate")
def evaluate(
    payload: EvaluateRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    #: Evaluasi tanpa tenant ditolak (400): tenant_id hasil evaluasi tidak boleh
    #: ditebak, dan tenantless caller tidak boleh mengevaluasi policy.
    tenant_id = require_tenant(caller)
    if payload.policy_slug:
        statement = scope_to_tenant(
            select(Policy).where(Policy.slug == payload.policy_slug), Policy, caller
        )
        if db.scalar(statement) is None:
            raise HTTPException(status_code=404, detail="Policy tidak ditemukan.")
    result = policy_engine.evaluate(
        policy_engine.PlanInput(
            action_type=payload.action_type,
            recipients=tuple(payload.recipients),
            allowed_recipients=tuple(payload.allowed_recipients),
            recipient_candidates=payload.recipient_candidates,
            at=payload.at,
            is_holiday=payload.is_holiday,
            is_friday_prayer=payload.is_friday_prayer,
            recipient_count=payload.recipient_count,
            bulk_threshold=payload.bulk_threshold,
            contains_injection=payload.contains_injection,
        )
    )
    digest = hashlib.sha256(
        f"{payload.plan_id!r}:{tenant_id}:{result.decision}:{result.reason_code}".encode("utf-8")
    ).hexdigest()[:24]
    evaluation_id = f"pev_{digest}"
    suffix = 1
    while db.get(PolicyEvaluation, evaluation_id) is not None:
        suffix += 1
        evaluation_id = f"pev_{digest}_{suffix}"
    db.add(
        PolicyEvaluation(
            id=evaluation_id,
            plan_id=payload.plan_id or payload.action_type,
            tenant_id=tenant_id,
            policy_slug=payload.policy_slug or "recipient-scope",
            decision=result.decision,
            reason_code=result.reason_code,
            detail=result.detail,
        )
    )
    db.commit()
    return {
        "decision": result.decision,
        "reason_code": result.reason_code,
        "detail": result.detail,
        "findings": [
            {"code": f.code, "decision": f.decision, "message": f.message} for f in result.findings
        ],
    }
