"""Tata kelola: policy, evaluasi, approval, mandate.

Mandate adalah kontrol terkuat di sistem ini. Ia mengikat satu tindakan konkret:
plan, aksi, hash parameter, penerima, approver, masa berlaku, dan nonce. Eksekusi
wajib memeriksa ulang mandate tepat sebelum tindakan dilakukan — bukan hanya
saat approval.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, IdMixin, TimestampMixin, utcnow

MANDATE_STATUSES = (
    "draft",
    "proposed",
    "validated",
    "pending_approval",
    "approved",
    "issued",
    "executing",
    "completed",
    "rejected",
    "expired",
    "revoked",
    "blocked",
    "failed",
    "cancelled",
)


class Policy(Base, IdMixin, TimestampMixin):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="policy_tenant_slug"),)

    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="organization", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    versions: Mapped[list["PolicyVersion"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan", lazy="selectin"
    )


class PolicyVersion(Base, IdMixin, TimestampMixin):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "version", name="policy_version"),)

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rules_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    change_note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    policy: Mapped[Policy] = relationship(back_populates="versions")


class PolicyEvaluation(Base, IdMixin):
    """Hasil evaluasi deterministik. Disimpan supaya keputusan bisa direproduksi."""

    __tablename__ = "policy_evaluations"

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    policy_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # allow | deny | review
    reason_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Approval(Base, IdMixin, TimestampMixin):
    __tablename__ = "approvals"

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: Tenant pemilik keputusan. NULL berarti baris lama dari sebelum P9; baris
    #: seperti itu tidak terlihat oleh pemanggil yang terikat tenant.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    #: String dari klien. Server mencatatnya dan TIDAK memverifikasinya.
    approver_id: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # approved | rejected | revision
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    mandate_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class Mandate(Base, IdMixin, TimestampMixin):
    __tablename__ = "mandates"

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: Tenant pemilik mandate. Wajib cocok dengan tenant pemanggil saat dipakai.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    approval_id: Mapped[str | None] = mapped_column(
        ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_scope: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    recipient_scope: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    params_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    approver_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    #: Nonce bersifat sekali pakai. Diisi tepat sebelum aksi dijalankan; eksekusi
    #: berikutnya dengan mandate yang sama ditolak meskipun idempotency key-nya
    #: berbeda (mis. action_type lain untuk action_id yang sama).
    nonce_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_by_execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="issued", nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    def is_usable(self, now: datetime | None = None) -> bool:
        moment = now or utcnow()
        if self.status not in ("issued", "approved"):
            return False
        if self.revoked_at is not None:
            return False
        expires = self.expires_at
        # SQLite mengembalikan datetime naif; samakan agar perbandingan tidak error.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=moment.tzinfo)
        return expires > moment
