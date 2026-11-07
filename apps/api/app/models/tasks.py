"""Manajemen kerja: work package dan task.

Status mengikuti lifecycle yang sudah dipakai dashboard existing, bukan
diciptakan ulang: draft, pending_approval, approved, executing, completed,
rejected, revoked, failed, cancelled.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, IdMixin, TimestampMixin

WORK_STATUSES = (
    "draft",
    "assigned",
    "in_progress",
    "review",
    "pending_approval",
    "approved",
    "executing",
    "completed",
    "rejected",
    "revoked",
    "failed",
    "cancelled",
)


class WorkPackage(Base, IdMixin, TimestampMixin):
    __tablename__ = "work_packages"

    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, default="org_001")
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="work_package", cascade="all, delete-orphan", lazy="selectin"
    )


class Task(Base, IdMixin, TimestampMixin):
    __tablename__ = "tasks"

    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    work_package_id: Mapped[str] = mapped_column(
        ForeignKey("work_packages.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="todo", nullable=False)
    #: Urutan hanya untuk tampilan papan; server tidak menyimpan posisi kartu.
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    work_package: Mapped[WorkPackage] = relationship(back_populates="tasks")
