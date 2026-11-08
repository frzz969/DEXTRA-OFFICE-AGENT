"""Approval: keputusan manusia yang mengikat tindakan spesifik.

Menyetujui sebuah plan menerbitkan mandate yang terikat pada action_id dan hash
parameter. Persetujuan yang tidak mengikat apa pun bukan persetujuan.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.session import get_db
from ...governance import approval as approval_service
from ...governance.approval import PolicyDenied
from ...governance.mandate import MandateError
from ...models.governance import Approval
from ...models.office import OfficePlanRequest

router = APIRouter(tags=["approvals"])


class ApprovalRequest(BaseModel):
    plan_id: str
    action_id: str
    action_type: str
    params: dict = Field(default_factory=dict)
    plan_hash: str = ""
    #: approver_id TIDAK diterima dari klien: identitas approver adalah
    #: caller.principal_id dari sesi/token terverifikasi. Field lama di sini
    #: membuat audit mencatat klaim klien apa adanya.
    decision: str = Field(pattern="^(approved|rejected|revision)$")
    reason: str = ""
    ttl_minutes: int = 30


@router.get("/approvals")
def list_approvals(
    db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    statement = scope_to_tenant(select(Approval), Approval, caller)
    rows = db.scalars(statement.order_by(Approval.decided_at.desc()).limit(200)).all()
    return {
        "items": [
            {
                "id": a.id,
                "plan_id": a.plan_id,
                "approver_id": a.approver_id,
                "decision": a.decision,
                "reason": a.reason,
                "decided_at": a.decided_at.isoformat(),
                "mandate_id": a.mandate_id,
            }
            for a in rows
        ],
        "note": "approver_id adalah principal terverifikasi dari sesi/token pemanggil.",
    }


@router.post("/approvals", status_code=201)
def decide(
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("approve")),
) -> dict:
    # Verify params against stored plan if exists (governance hole closure)
    plan_row = db.scalar(
        select(OfficePlanRequest).where(
            OfficePlanRequest.tenant_id == caller.tenant_id,
            OfficePlanRequest.plan_id == payload.plan_id,
        )
    )
    if plan_row is not None:
        actions = json.loads(plan_row.actions_json or "[]")
        stored = next((a for a in actions if a.get("action_id") == payload.action_id), None)
        if stored is not None:
            if stored.get("action_type") != payload.action_type:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ACTION_TYPE_MISMATCH", "message": "action_type mismatch"},
                )
            if stored.get("params") != payload.params:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "PARAMS_MISMATCH", "message": "params mismatch"},
                )

    request = approval_service.DecisionRequest(
        plan_id=payload.plan_id,
        action_id=payload.action_id,
        action_type=payload.action_type,
        params=payload.params,
        plan_hash=payload.plan_hash,
        # Approver yang tercatat adalah principal terverifikasi, bukan string
        # yang dikirim klien (lihat office_agent/router.py).
        approver_id=caller.principal_id or "",
        decision=payload.decision,
        reason=payload.reason,
        ttl_minutes=payload.ttl_minutes,
        tenant_id=caller.tenant_id,
    )
    try:
        approval, mandate = approval_service.record_decision(
            db, request, actor="dashboard", scope=caller.scope
        )
    except PolicyDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail={"code": exc.evaluation.reason_code, "message": exc.evaluation.detail}
        ) from exc
    except MandateError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail={"code": exc.code, "message": exc.message}
        ) from exc

    db.commit()
    return {
        "id": approval.id,
        "decision": approval.decision,
        "mandate_id": mandate.id if mandate else None,
    }
