"""Plan yang datang dari Office Agent.

Office Agent (`packages/office-agent`) menghasilkan rencana dari dokumen yang
tidak dipercaya: hasil dekomposisi, temuan kebijakan, dan daftar tindakan.
Tabel ini menyimpan rencana itu apa adanya sebagai *data*, dengan atribusi
tenant dan principal yang jelas.

Yang tidak dilakukan di sini: mengeksekusi. Persetujuan tetap lewat Approval
Engine, penerbitan mandate lewat Mandate Engine, eksekusi lewat Execution
Gateway. Tabel ini hanya titik masuk yang bisa diaudit.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin

OFFICE_PLAN_STATUSES = ("received", "partially_approved", "approved", "rejected")


class OfficePlanRequest(Base, IdMixin, TimestampMixin):
    __tablename__ = "office_plan_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_id", name="office_plan_request_id"),
        Index("ix_office_plan_requests_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Idempotensi: request_id yang sama tidak membuat baris kedua.
    request_id: Mapped[str] = mapped_column(String(96), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    plan_hash: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    source_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    document_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    actions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    findings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    validation_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="received", nullable=False)
    #: Principal yang mengirim rencana: manusia atau identitas mesin.
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_service_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("service_accounts.id", ondelete="SET NULL"), nullable=True
    )


OFFICE_INTAKE_STATES = ("needs_clarification", "planned", "blocked")


class OfficeIntake(Base, IdMixin, TimestampMixin):
    __tablename__ = "office_intakes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_id", name="office_intake_request_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[str] = mapped_column(String(96), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    intent: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    state: Mapped[str] = mapped_column(String(24), default="needs_clarification", nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    clarification_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    plan_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="deterministic-fallback", nullable=False)
