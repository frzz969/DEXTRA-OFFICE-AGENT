"""Skill Registry: metadata, versi, dan keterikatan permission.

Yang disimpan di sini adalah *katalog*, bukan mesin validasi kedua. Validator
manifest lengkap (subset JSON Schema, semver, siklus dependensi) sudah ada di
`packages/skill-registry` dan tetap menjadi rujukan. Backend Python menegakkan
bagian yang menyangkut otorisasi dan siklus hidup:

- slug dan versi unik per tenant;
- capability yang diminta harus ada di katalog dan tidak boleh capability
  istimewa (approve/execute/manage_*) — skill tidak boleh memberi dirinya
  wewenang yang hanya boleh dipegang manusia;
- status hanya bergerak lewat transisi yang diizinkan.

Memvalidasi ulang seluruh manifest di sini akan menghasilkan dua validator yang
menyimpang. Itu bukan kehati-hatian, itu duplikasi.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin

SKILL_STATUSES = ("draft", "active", "disabled", "deprecated")

#: Transisi status yang diizinkan. Tidak ada jalan pintas dari draft ke active
#: tanpa melewati validasi; dan skill yang deprecated tidak bisa diaktifkan lagi.
SKILL_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("active", "disabled"),
    "active": ("disabled", "deprecated"),
    "disabled": ("active", "deprecated"),
    "deprecated": (),
}

#: Capability yang tidak boleh dimiliki sebuah skill. Skill dijalankan *di dalam*
#: mandat; memberi skill hak menyetujui atau mengeksekusi akan melewati seluruh
#: rantai tata kelola.
RESERVED_SKILL_CAPABILITIES = (
    "approve",
    "issue_mandate",
    "revoke_mandate",
    "execute",
    "edit_policy",
    "manage_users",
    "manage_integrations",
)


class Skill(Base, IdMixin, TimestampMixin):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="skill_slug"),
        Index("ix_skills_tenant_status", "tenant_id", "status"),
    )

    #: NULL = skill sistem, terlihat oleh semua tenant tetapi tidak bisa diubah
    #: oleh tenant mana pun.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(96), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    latest_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SkillVersion(Base, IdMixin, TimestampMixin):
    __tablename__ = "skill_versions"
    __table_args__ = (UniqueConstraint("skill_id", "version", name="skill_version"),)

    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    input_schema_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    output_schema_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    required_capabilities_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowDefinition(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflow_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", "version", name="workflow_name_version"),
        Index("ix_workflow_definitions_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    steps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class WorkflowRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="workflow_run_idempotency"),
        Index("ix_workflow_runs_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="running", nullable=False)
    #: Status: running | waiting_approval | succeeded | failed | cancelled
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    state_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    #: Titik pemulihan: state setelah langkah terakhir yang berhasil.
    checkpoint_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class WorkflowStepRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflow_step_runs"
    __table_args__ = (UniqueConstraint("run_id", "step_id", name="workflow_step_run"),)

    run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    #: pending | running | succeeded | failed | waiting_approval | skipped
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, default="null", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Diisi bila langkah ini adalah gerbang persetujuan manusia.
    approved_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
