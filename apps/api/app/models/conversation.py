"""Percakapan dan pesan sebagai sistem pencatat di sisi backend.

Blueprint fase 1 membutuhkan percakapan yang bisa diaudit dan terikat tenant,
bukan riwayat yang hanya hidup di state frontend. Tabel di sini menyimpan
percakapan (`conversations`) dan pesan (`conversation_messages`) apa adanya:
teks pesan sebagai data, atribusi tenant eksplisit, dan tanpa kolom yang
menyamar sebagai sesi login.

Catatan penamaan: `sessions` sudah berarti sesi autentikasi (cookie login).
Karena itu tidak ada `session`/`session_id` di sini — percakapan adalah
`conversation`, dan pesan adalah `message`.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin

CONVERSATION_STATUSES = ("active", "archived")
MESSAGE_ROLES = ("user", "assistant", "system", "tool")


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class ConversationMessage(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index(
            "ix_conversation_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    #: Denormalisasi tenant supaya `scope_to_tenant` bisa membatasi query pesan
    #: tanpa join ke `conversations`.
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
