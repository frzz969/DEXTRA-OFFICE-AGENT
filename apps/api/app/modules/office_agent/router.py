"""Integrasi Office Agent ke fondasi tata kelola.

Alur yang dijaga:

    dokumen (tidak dipercaya)
      -> Office Agent: intake, normalisasi, dekomposisi, klarifikasi
      -> POST /office-agent/plans        (create_request, tersimpan per tenant)
      -> POST .../actions/{id}/approve   (approve, manusia)
      -> Approval Engine -> Mandate Engine
      -> POST /executions                (execute, Execution Gateway)
      -> Audit Chain

Modul ini hanya mengisi dua kotak pertama dan menyerahkan sisanya ke mesin yang
sudah ada. Tidak ada gateway kedua, tidak ada audit store kedua, tidak ada
penerbitan mandate sendiri.

Identitas: rencana boleh dikirim oleh sesi manusia atau oleh service account
(worker Office Agent). Keduanya menghasilkan `tenant_id` yang sama dan
capability yang dihitung server. Tidak ada jalur "agent mode" yang melewati
otorisasi.
"""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...governance import approval as approval_service
from ...governance.mandate import MandateError
from ...models.office import OfficePlanRequest
from ...repositories import audit as audit_repo

router = APIRouter(tags=["office-agent"])


class OfficeAction(BaseModel):
    action_id: str = Field(min_length=1, max_length=64)
    action_type: str = Field(min_length=1, max_length=64)
    params: dict = Field(default_factory=dict)
    #: Dari mana tindakan ini berasal di dokumen (blok, baris).
    source_ref: dict = Field(default_factory=dict)


class OfficePlanPayload(BaseModel):
    request_id: str = Field(min_length=4, max_length=96)
    plan_id: str = Field(min_length=1, max_length=96)
    plan_hash: str = Field(default="", max_length=128)
    source: dict = Field(default_factory=dict)
    document: dict = Field(default_factory=dict)
    actions: list[OfficeAction] = Field(min_length=1, max_length=50)
    findings: list[dict] = Field(default_factory=list, max_length=100)
    validation: dict = Field(default_factory=dict)


class ApproveActionRequest(BaseModel):
    reason: str = Field(default="", max_length=500)
    ttl_minutes: int = Field(default=30, ge=1, le=1440)
    decision: str = Field(default="approved", pattern="^(approved|rejected)$")


def _serialize(row: OfficePlanRequest) -> dict:
    return {
        "id": row.id,
        "request_id": row.request_id,
        "plan_id": row.plan_id,
        "plan_hash": row.plan_hash,
        "status": row.status,
        "actions": json.loads(row.actions_json or "[]"),
        "findings": json.loads(row.findings_json or "[]"),
        "validation": json.loads(row.validation_json or "{}"),
        "created_at": row.created_at.isoformat(),
    }


def _hash_actions(actions: list[dict]) -> str:
    canonical = json.dumps(actions, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@router.post("/office-agent/plans", status_code=201)
def submit_plan(
    payload: OfficePlanPayload,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    tenant_id = require_tenant(caller)
    existing = db.scalar(
        select(OfficePlanRequest).where(
            OfficePlanRequest.tenant_id == tenant_id,
            OfficePlanRequest.request_id == payload.request_id,
        )
    )
    if existing is not None:
        # Idempotensi: kiriman ulang mengembalikan rencana yang sama, bukan
        # menduplikasi tindakan yang nanti akan disetujui dua kali.
        return _serialize(existing)

    actions = [action.model_dump() for action in payload.actions]
    seen = set()
    for action in actions:
        if action["action_id"] in seen:
            raise HTTPException(
                status_code=422, detail=f"action_id duplikat: {action['action_id']}"
            )
        seen.add(action["action_id"])

    row = OfficePlanRequest(
        id=new_id("ofp"),
        tenant_id=tenant_id,
        request_id=payload.request_id,
        plan_id=payload.plan_id,
        plan_hash=payload.plan_hash or _hash_actions(actions),
        source_json=json.dumps(payload.source, sort_keys=True),
        document_json=json.dumps(payload.document, sort_keys=True),
        actions_json=json.dumps(actions, sort_keys=True),
        findings_json=json.dumps(payload.findings, sort_keys=True),
        validation_json=json.dumps(payload.validation, sort_keys=True),
        status="received",
        created_by_user_id=caller.principal_id if caller.auth_kind == "session" else None,
        created_by_service_account_id=caller.principal_id
        if caller.auth_kind == "service_token"
        else None,
    )
    db.add(row)
    audit_repo.append_event(
        db,
        event_type="office_plan_received",
        actor="service" if caller.auth_kind == "service_token" else "user",
        scope=caller.scope,
        action="submit_office_plan",
        resource=row.plan_id,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={
            "request_id": row.request_id,
            "actions": len(actions),
            "findings": len(payload.findings),
        },
    )
    db.commit()
    return _serialize(row)


@router.get("/office-agent/plans")
def list_plans(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    rows = db.scalars(
        select(OfficePlanRequest)
        .where(OfficePlanRequest.tenant_id == tenant_id)
        .order_by(OfficePlanRequest.created_at.desc())
        .limit(100)
    ).all()
    return {"items": [_serialize(row) for row in rows]}


@router.get("/office-agent/plans/{plan_id}")
def get_plan(
    plan_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    row = db.scalar(
        select(OfficePlanRequest).where(
            OfficePlanRequest.tenant_id == tenant_id, OfficePlanRequest.plan_id == plan_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Rencana tidak ditemukan.")
    return _serialize(row)


@router.post("/office-agent/plans/{plan_id}/actions/{action_id}/approve", status_code=201)
def approve_action(
    plan_id: str,
    action_id: str,
    payload: ApproveActionRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("approve")),
) -> dict:
    """Persetujuan manusia atas satu tindakan. Menerbitkan mandate lewat engine."""
    tenant_id = require_tenant(caller)
    row = db.scalar(
        select(OfficePlanRequest).where(
            OfficePlanRequest.tenant_id == tenant_id, OfficePlanRequest.plan_id == plan_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Rencana tidak ditemukan.")

    actions = json.loads(row.actions_json or "[]")
    action = next((item for item in actions if item["action_id"] == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Tindakan tidak ditemukan pada rencana ini.")

    request = approval_service.DecisionRequest(
        plan_id=row.plan_id,
        action_id=action["action_id"],
        action_type=action["action_type"],
        params=action.get("params") or {},
        plan_hash=row.plan_hash,
        # Approver yang tercatat adalah principal terverifikasi, bukan string
        # yang dikirim klien.
        approver_id=caller.principal_id or "",
        decision=payload.decision,
        reason=payload.reason,
        ttl_minutes=payload.ttl_minutes,
        tenant_id=tenant_id,
    )
    try:
        approval, mandate = approval_service.record_decision(
            db, request, actor="office_agent", scope=caller.scope
        )
    except MandateError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": exc.message}
        ) from exc

    if payload.decision == "rejected":
        row.status = "rejected"
    else:
        row.status = "partially_approved"
    db.commit()
    return {
        "approval_id": approval.id,
        "mandate_id": mandate.id if mandate else None,
        "action_id": action["action_id"],
        "decision": approval.decision,
        "next": "POST /api/v1/executions dengan mandate_id untuk mengeksekusi.",
    }
