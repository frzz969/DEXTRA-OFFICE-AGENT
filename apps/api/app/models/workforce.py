"""Workforce: registri agen yang benar-benar ditetapkan.

Hanya empat spesialis yang diakui (§8.4). Menambah baris di sini berarti
menambah agen yang harus benar-benar ada implementasinya — bukan sekadar
mengisi direktori.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, IdMixin, TimestampMixin, new_id


class Agent(Base, IdMixin, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="agent_tenant_slug"),)

    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), default="workbuddy", nullable=False)
    #: active | idle | busy | disabled | error
    status: Mapped[str] = mapped_column(String(16), default="idle", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    capabilities: Mapped[list["AgentCapability"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    versions: Mapped[list["AgentVersion"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )


class AgentCapability(Base, IdMixin):
    __tablename__ = "agent_capabilities"
    __table_args__ = (UniqueConstraint("agent_id", "capability", name="agent_capability"),)

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="capabilities")


class AgentVersion(Base, IdMixin, TimestampMixin):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="agent_version"),)

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="versions")


class AgentAssignment(Base, IdMixin, TimestampMixin):
    __tablename__ = "agent_assignments"
    #: Satu agen tidak bisa ditugaskan dua kali dengan peran yang sama pada task
    #: yang sama. Ditegakkan database, bukan hanya oleh pemeriksaan di kode:
    #: dua permintaan assign yang berjalan bersamaan sama-sama lolos pemeriksaan.
    __table_args__ = (
        UniqueConstraint("task_id", "agent_id", "role", name="agent_assignment_unique"),
    )

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(64), default="executor", nullable=False)
