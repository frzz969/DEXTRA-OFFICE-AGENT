"""Siklus mandate: penerbitan dan validasi ulang tepat sebelum eksekusi.

Aturan yang ditegakkan di sini, bukan di UI:
- mandate harus terikat pada satu action_id dan satu params_hash;
- mandate yang dicabut, kedaluwarsa, atau berstatus salah tidak bisa dipakai;
- nonce unik mencegah penerbitan ganda untuk approval yang sama.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.governance import Approval, Mandate


class MandateError(Exception):
    """Pelanggaran aturan mandate. `code` dipakai sebagai reason code di API."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def params_digest(params: dict) -> str:
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IssueRequest:
    plan_id: str
    approval_id: str
    action_id: str
    action_type: str
    params: dict
    plan_hash: str
    resource_scope: str = ""
    recipient_scope: str = ""
    agent_id: str | None = None
    ttl_minutes: int = 30
    #: Tenant pemilik mandate. Diwarisi dari approval, bukan dari klien.
    tenant_id: str | None = None


def issue(db: Session, request: IssueRequest, now: datetime | None = None) -> Mandate:
    approval = db.get(Approval, request.approval_id)
    if approval is None:
        raise MandateError("APPROVAL_NOT_FOUND", "Approval tidak ditemukan.")
    # Approval dan mandate harus berada di tenant yang sama. Approval tanpa
    # tenant (baris lama) tidak boleh menerbitkan mandate bertuan.
    if request.tenant_id is not None and approval.tenant_id != request.tenant_id:
        raise MandateError(
            "APPROVAL_TENANT_MISMATCH",
            "Approval ini bukan milik tenant pemanggil.",
        )
    if approval.decision != "approved":
        raise MandateError(
            "APPROVAL_NOT_APPROVED",
            f"Approval berstatus {approval.decision}; mandate tidak boleh diterbitkan.",
        )
    if approval.plan_id != request.plan_id:
        raise MandateError(
            "APPROVAL_PLAN_MISMATCH",
            "Approval ini milik plan lain; persetujuan harus mengikat tindakan spesifik.",
        )
    existing = db.scalar(select(Mandate).where(Mandate.approval_id == request.approval_id))
    if existing is not None:
        raise MandateError(
            "MANDATE_ALREADY_ISSUED",
            f"Approval ini sudah menerbitkan mandate {existing.id}.",
        )

    moment = now or datetime.now(timezone.utc)
    mandate = Mandate(
        id=f"mnd_{secrets.token_hex(8)}",
        plan_id=request.plan_id,
        approval_id=request.approval_id,
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        action_id=request.action_id,
        action_type=request.action_type,
        resource_scope=request.resource_scope,
        recipient_scope=request.recipient_scope,
        params_hash=params_digest(request.params),
        plan_hash=request.plan_hash,
        approver_id=approval.approver_id,
        nonce=secrets.token_hex(16),
        status="issued",
        issued_at=moment,
        expires_at=moment + timedelta(minutes=request.ttl_minutes),
    )
    db.add(mandate)
    db.flush()
    return mandate


def validate_for_execution(
    db: Session,
    *,
    mandate_id: str,
    action_id: str,
    params: dict,
    now: datetime | None = None,
) -> Mandate:
    """Dipanggil tepat sebelum aksi dijalankan, bukan hanya saat approval."""
    mandate = db.get(Mandate, mandate_id)
    if mandate is None:
        raise MandateError("MANDATE_NOT_FOUND", "Mandate tidak ditemukan.")
    if mandate.revoked_at is not None:
        raise MandateError("MANDATE_REVOKED", "Mandate sudah dicabut.")
    # Kecocokan aksi dan parameter diperiksa sebelum status/kedaluwarsa: kalau
    # parameter diubah, alasan yang benar adalah PARAMS_CHANGED, bukan "expired".
    # Alasan yang salah membuat orang menduga masalahnya di tempat yang keliru.
    if mandate.action_id != action_id:
        raise MandateError(
            "ACTION_NOT_IN_MANDATE",
            f"Mandate mengikat aksi {mandate.action_id}, bukan {action_id}.",
        )
    if mandate.params_hash != params_digest(params):
        raise MandateError(
            "PARAMS_CHANGED",
            "Parameter aksi berubah sejak disetujui; mandate tidak berlaku.",
        )
    if mandate.status in ("expired", "completed", "cancelled", "rejected"):
        raise MandateError("MANDATE_NOT_USABLE", f"Mandate berstatus {mandate.status}.")
    if not mandate.is_usable(now):
        raise MandateError("MANDATE_EXPIRED", "Mandate sudah kedaluwarsa.")
    return mandate


def revoke(db: Session, mandate_id: str, reason: str, now: datetime | None = None) -> Mandate:
    mandate = db.get(Mandate, mandate_id)
    if mandate is None:
        raise MandateError("MANDATE_NOT_FOUND", "Mandate tidak ditemukan.")
    if mandate.revoked_at is not None:
        return mandate
    mandate.revoked_at = now or datetime.now(timezone.utc)
    mandate.status = "revoked"
    mandate.revoke_reason = reason
    db.flush()
    return mandate
