"""Perekaman keputusan approval dan penerbitan mandate.

Satu implementasi untuk dua pemanggil: endpoint `/approvals` dan jalur Office
Agent. Kalau keduanya menulis sendiri-sendiri, cepat atau lambat satu jalur lupa
menulis audit atau lupa meneruskan `tenant_id` — dan persetujuan yang tidak
tercatat adalah persetujuan yang tidak bisa dipertanggungjawabkan.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.governance import Approval, Mandate
from ..repositories import audit as audit_repo
from . import mandate as mandate_service
from .mandate import MandateError


@dataclass(frozen=True)
class DecisionRequest:
    plan_id: str
    action_id: str
    action_type: str
    params: dict
    plan_hash: str
    approver_id: str
    decision: str
    reason: str = ""
    ttl_minutes: int = 30
    tenant_id: str | None = None


def record_decision(
    db: Session,
    request: DecisionRequest,
    *,
    actor: str = "dashboard",
    scope: str = "ops",
) -> tuple[Approval, Mandate | None]:
    approval = Approval(
        # Suffix acak: stempel waktu saja tidak unik — dua approval bisa masuk di
        # detik yang sama, dan tabrakan primary key akan menggagalkan keputusan
        # yang sah.
        id=f"apr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}",
        plan_id=request.plan_id,
        tenant_id=request.tenant_id,
        approver_id=request.approver_id,
        decision=request.decision,
        reason=request.reason,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(approval)
    db.flush()

    audit_repo.append_event(
        db,
        event_type="approval_recorded",
        actor=actor,
        scope=scope,
        action="submit_approval",
        resource=request.plan_id,
        decision=request.decision,
        plan_id=request.plan_id,
        tenant_id=request.tenant_id,
        detail={"approval_id": approval.id, "approver_id": request.approver_id},
    )

    mandate: Mandate | None = None
    if request.decision == "approved":
        try:
            mandate = mandate_service.issue(
                db,
                mandate_service.IssueRequest(
                    plan_id=request.plan_id,
                    approval_id=approval.id,
                    action_id=request.action_id,
                    action_type=request.action_type,
                    params=request.params,
                    plan_hash=request.plan_hash,
                    ttl_minutes=request.ttl_minutes,
                    tenant_id=request.tenant_id,
                ),
            )
        except MandateError:
            # Rollback dilakukan pemanggil: kegagalan penerbitan mandate harus
            # membatalkan approval yang baru ditulis, bukan menyisakannya.
            raise
        approval.mandate_id = mandate.id
        audit_repo.append_event(
            db,
            event_type="mandate_issued",
            actor=actor,
            scope=scope,
            action="issue_mandate",
            resource=mandate.id,
            decision="allow",
            plan_id=request.plan_id,
            mandate_id=mandate.id,
            tenant_id=request.tenant_id,
            detail={"via": "submit_approval", "approval_id": approval.id},
        )

    return approval, mandate
