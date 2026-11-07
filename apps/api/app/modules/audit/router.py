"""Audit trail: baca dan verifikasi rantai hash."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.session import get_db
from ...repositories import audit as audit_repo

router = APIRouter(tags=["audit"])


@router.get("/audit-events")
def list_audit_events(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    tenant_id = require_tenant(caller)
    events = audit_repo.list_events(db, limit=limit, offset=offset, tenant_id=tenant_id)
    return {
        "items": [
            {
                "id": e.id,
                "seq": e.seq,
                "at": e.at.isoformat(),
                "event_type": e.event_type,
                "actor": e.actor,
                "scope": e.scope,
                "action": e.action,
                "resource": e.resource,
                "decision": e.decision,
                "plan_id": e.plan_id,
                "mandate_id": e.mandate_id,
                "execution_id": e.execution_id,
                "correlation_id": e.correlation_id,
                "detail": json.loads(e.detail_json or "{}"),
                "entry_hash": e.entry_hash,
            }
            for e in events
        ]
    }


@router.get("/audit-events/verify")
def verify_audit(
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    """Membuktikan rantai utuh. Kalau ada baris yang disunting, `broken_at_seq` menunjuk lokasinya."""
    return audit_repo.verify_chain(db)
