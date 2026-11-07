"""Eksekusi: jejak, langkah, idempotensi.

Satu kontrak idempotensi: `idempotency_key = mandate_id:action_id:params_digest`
dan ia unik di level database (kolom unik + UniqueConstraint
(mandate_id, action_id, params_digest) — ketiganya sejalan). Retry dengan
params yang sama mengembalikan baris yang sudah ada; retry dengan params yang
berubah mendapat kunci berbeda dan ditolak oleh validasi ulang mandate
(PARAMS_CHANGED), bukan diam-diam mengembalikan hasil lama.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, IdMixin, TimestampMixin, utcnow

EXECUTION_STATUSES = ("pending", "running", "succeeded", "failed", "blocked", "skipped")


class Execution(Base, IdMixin, TimestampMixin):
    __tablename__ = "executions"
    __table_args__ = (
        # SATU kontrak: kunci idempotensi = (mandate_id, action_id, params_digest).
        # Constraint ini, kolom idempotency_key yang unik, dan kunci yang dibangun
        # service harus selalu sejalan — tidak ada dua definisi yang berbeda.
        UniqueConstraint(
            "mandate_id", "action_id", "params_digest", name="execution_mandate_action_params"
        ),
    )

    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: Tenant pemilik eksekusi. Diwarisi dari mandate, tidak dari klien.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: Adapter yang benar-benar dipakai. Satu-satunya penulis adalah
    #: execution/service.py ("mock"); default kolom disamakan di sini agar tidak
    #: ada huruf kedua yang membawa nilai yang berbeda.
    adapter: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    #: params_digest(params) — bagian ketiga idempotency_key, disimpan terpisah
    #: supaya constraint (mandate_id, action_id, params_digest) bisa ditegakkan
    #: di level database.
    params_digest: Mapped[str | None] = mapped_column(
        String(128),
        # Backfill: baris lama sudah terlanjur ada; jangan paksakan NOT NULL di model
        # agar fresh DB=dari-model tetap jalan. Migrasi 27ba08c94572 mengisi nilai
        # lama dari idempotency_key; baris tanpa itu ditandai dan dicatat.
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)

    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", lazy="selectin"
    )


class ExecutionStep(Base, IdMixin):
    __tablename__ = "execution_steps"

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    execution: Mapped[Execution] = relationship(back_populates="steps")


class ActionRecord(Base, IdMixin):
    """Parameter aksi yang benar-benar dieksekusi, disimpan untuk pembanding hash."""

    __tablename__ = "action_records"

    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    params_hash: Mapped[str] = mapped_column(String(128), nullable=False)
