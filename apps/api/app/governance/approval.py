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

from ..database.base import new_id
from ..models.governance import Approval, Mandate, PolicyEvaluation
from ..repositories import audit as audit_repo
from . import mandate as mandate_service
from . import policy as policy_engine
from .mandate import MandateError


class PolicyDenied(Exception):
    """Policy menolak aksi. Pemanggil wajib meng-commit audit sebelum 409."""

    def __init__(self, evaluation: PolicyEvaluation) -> None:
        super().__init__(evaluation.detail)
        self.evaluation = evaluation


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
    #: Temuan Office Agent. Dipakai untuk flag injeksi; jalur /approvals tidak
    #: punya temuan dan mengirim tuple kosong.
    findings: tuple[dict, ...] = ()


EMAIL_ACTIONS = frozenset({"send_email", "email"})
CALENDAR_ACTIONS = frozenset({"create_calendar_event", "calendar"})
TASK_ACTIONS = frozenset({"create_task", "task"})
STATE_CHANGING_ACTIONS = EMAIL_ACTIONS | CALENDAR_ACTIONS | TASK_ACTIONS

#: Reason code lokal untuk pemetaan yang tidak lengkap. Bukan aturan baru:
#: hasilnya selalu `review`, yang hanya boleh diteruskan oleh approval manusia.
POLICY_INPUT_INCOMPLETE = "POLICY_INPUT_INCOMPLETE"


def _recipients_from_params(params: dict) -> tuple[str, ...]:
    raw = params.get("recipients")
    if raw is None:
        raw = params.get("to")
    if raw is None:
        return ()
    items = [raw] if isinstance(raw, str) else list(raw) if isinstance(raw, (list, tuple)) else []
    recipients: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        for part in item.replace(";", ",").split(","):
            value = part.strip()
            if value:
                recipients.append(value)
    return tuple(recipients)


def _parse_at(params: dict) -> datetime | None:
    """Ambil waktu dari `at`/`start`/`time`; None berarti tidak diketahui."""
    for key in ("at", "start", "time"):
        raw = params.get(key)
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
            except ValueError:
                return None
    return None


def _contains_injection(findings: tuple[dict, ...]) -> bool:
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get("contains_injection") is True:
            return True
        code = str(finding.get("code") or finding.get("type") or "").upper()
        if "INJECT" in code:
            return True
        if str(finding.get("severity") or "").lower() == "injection":
            return True
    return False


def plan_input_for_action(
    action_type: str, params: dict, findings: tuple[dict, ...]
) -> tuple[policy_engine.PlanInput, tuple[str, ...]]:
    """Petakan aksi ke `PlanInput` secara konservatif.

    Data yang tidak ada atau tidak bisa dibaca tidak boleh berubah menjadi
    `allow`: pemanggil mengubahnya menjadi `review`. Tidak ada aturan baru di
    sini — hanya pengisian input yang sudah dimiliki policy engine.
    """
    normalized = (action_type or "").lower()
    recipients = _recipients_from_params(params)
    at = _parse_at(params)
    allowed_raw = params.get("allowed_recipients")
    allowed = (
        tuple(str(item) for item in allowed_raw if isinstance(item, str))
        if isinstance(allowed_raw, (list, tuple))
        else ()
    )
    candidates_raw = params.get("recipient_candidates")
    recipient_candidates = (
        candidates_raw
        if isinstance(candidates_raw, int) and not isinstance(candidates_raw, bool)
        else 1
    )

    unknowns: list[str] = []
    if normalized in EMAIL_ACTIONS:
        if not recipients:
            unknowns.append("MISSING_RECIPIENTS")
    elif normalized in CALENDAR_ACTIONS:
        if at is None:
            unknowns.append("MISSING_OR_INVALID_TIME")
    elif normalized not in TASK_ACTIONS:
        unknowns.append("UNKNOWN_ACTION_TYPE")

    plan = policy_engine.PlanInput(
        action_type=normalized,
        recipients=recipients,
        allowed_recipients=allowed,
        recipient_candidates=recipient_candidates,
        at=at,
        recipient_count=len(recipients) or 1,
        contains_injection=_contains_injection(findings),
    )
    return plan, tuple(unknowns)


def _record_policy_evaluation(
    db: Session,
    *,
    request: DecisionRequest,
    plan: policy_engine.PlanInput,
    unknowns: tuple[str, ...],
) -> PolicyEvaluation:
    result = policy_engine.evaluate(plan)
    decision = result.decision
    reason_code = result.reason_code
    detail = result.detail
    if unknowns:
        decision = policy_engine.REVIEW
        reason_code = POLICY_INPUT_INCOMPLETE
        detail = "Data untuk evaluasi tidak lengkap: " + ", ".join(unknowns)
    row = PolicyEvaluation(
        id=new_id("pev"),
        plan_id=request.plan_id,
        tenant_id=request.tenant_id,
        policy_slug="approval-path",
        decision=decision,
        reason_code=reason_code,
        detail=detail,
    )
    db.add(row)
    db.flush()
    return row


def record_decision(
    db: Session,
    request: DecisionRequest,
    *,
    actor: str = "dashboard",
    scope: str = "ops",
) -> tuple[Approval, Mandate | None]:
    policy_row: PolicyEvaluation | None = None
    if request.decision == "approved":
        plan, unknowns = plan_input_for_action(
            request.action_type, request.params, request.findings
        )
        policy_row = _record_policy_evaluation(
            db, request=request, plan=plan, unknowns=unknowns
        )
        if policy_row.decision == policy_engine.DENY:
            audit_repo.append_event(
                db,
                event_type="action_blocked",
                actor=actor,
                scope=scope,
                action="approval_policy",
                resource=request.plan_id,
                decision="deny",
                plan_id=request.plan_id,
                tenant_id=request.tenant_id,
                detail={
                    "code": policy_row.reason_code,
                    "message": policy_row.detail,
                    "policy_evaluation_id": policy_row.id,
                    "action_id": request.action_id,
                    "action_type": request.action_type,
                },
            )
            raise PolicyDenied(policy_row)

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
