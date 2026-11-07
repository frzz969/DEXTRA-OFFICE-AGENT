"""Mandate: daftar, detail, dan pencabutan."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import assert_tenant_access, scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.session import get_db
from ...governance import mandate as mandate_service
from ...governance.mandate import MandateError
from ...models.governance import Mandate
from ...repositories import audit as audit_repo

router = APIRouter(tags=["mandates"])


class RevokeRequest(BaseModel):
    reason: str


def _serialize(m: Mandate) -> dict:
    return {
        "id": m.id,
        "plan_id": m.plan_id,
        "approval_id": m.approval_id,
        "action_id": m.action_id,
        "action_type": m.action_type,
        "resource_scope": m.resource_scope,
        "recipient_scope": m.recipient_scope,
        "params_hash": m.params_hash,
        "approver_id": m.approver_id,
        "status": m.status,
        "issued_at": m.issued_at.isoformat(),
        "expires_at": m.expires_at.isoformat(),
        "revoked_at": m.revoked_at.isoformat() if m.revoked_at else None,
        "usable": m.is_usable(),
    }


@router.get("/mandates")
def list_mandates(
    db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    statement = scope_to_tenant(select(Mandate), Mandate, caller)
    rows = db.scalars(statement.order_by(Mandate.issued_at.desc()).limit(200)).all()
    return {"items": [_serialize(m) for m in rows]}


@router.get("/mandates/{mandate_id}")
def get_mandate(
    mandate_id: str, db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    mandate = db.get(Mandate, mandate_id)
    if mandate is None:
        raise HTTPException(status_code=404, detail="Mandate tidak ditemukan.")
    assert_tenant_access(caller, mandate.tenant_id, resource="Mandate")
    return _serialize(mandate)


@router.post("/mandates/{mandate_id}/revoke")
def revoke(
    mandate_id: str,
    payload: RevokeRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("revoke_mandate")),
) -> dict:
    existing = db.get(Mandate, mandate_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Mandate tidak ditemukan.")
    assert_tenant_access(caller, existing.tenant_id, resource="Mandate")
    try:
        mandate = mandate_service.revoke(db, mandate_id, payload.reason)
    except MandateError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message}) from exc
    audit_repo.append_event(
        db,
        event_type="mandate_revoked",
        actor="dashboard",
        scope=caller.scope,
        action="revoke_mandate",
        resource=mandate_id,
        decision="allow",
        plan_id=mandate.plan_id,
        mandate_id=mandate.id,
        tenant_id=caller.tenant_id,
        detail={"reason": payload.reason},
    )
    db.commit()
    return _serialize(mandate)
