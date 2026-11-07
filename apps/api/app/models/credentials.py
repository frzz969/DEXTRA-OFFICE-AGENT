"""Kredensial mesin: service account dan API token.

Satu tabel kredensial untuk dua jenis pemilik. Service account adalah *identitas*
(worker, MCP server, agent); API token adalah *kredensial* yang dipakai identitas
itu untuk membuktikan dirinya. Memisahkan keduanya mencegah duplikasi sistem
token: rotasi berarti menerbitkan token baru dan mencabut yang lama, bukan
membuat mekanisme kedua.

Yang tidak pernah disimpan: secret token mentah. Hanya `token_hash` (SHA-256 dari
secret) dan `token_prefix` (potongan untuk ditampilkan di inventaris). Token
lengkap dikembalikan tepat sekali, saat dibuat.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin

SERVICE_ACCOUNT_KINDS = ("worker", "mcp", "agent", "integration")
SERVICE_ACCOUNT_STATUSES = ("active", "disabled", "revoked")
TOKEN_STATUSES = ("active", "revoked")


class ServiceAccount(Base, IdMixin, TimestampMixin):
    """Identitas non-manusia. Tidak pernah memakai akun manusia."""

    __tablename__ = "service_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="service_account_name"),
        Index("ix_service_accounts_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    #: Capability yang boleh dipakai identitas ini. Irisan dengan token, bukan
    #: pengganti: token tidak boleh memberi lebih dari yang dimiliki identitas.
    scopes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    def is_active(self) -> bool:
        return self.status == "active" and self.revoked_at is None


class ApiToken(Base, IdMixin, TimestampMixin):
    __tablename__ = "api_tokens"
    __table_args__ = (
        # Pemilik token harus tepat satu: manusia atau service account.
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND service_account_id IS NULL) "
            "OR (owner_user_id IS NULL AND service_account_id IS NOT NULL)",
            name="api_token_single_owner",
        ),
        Index("ix_api_tokens_tenant_status", "tenant_id", "status"),
        Index("ix_api_tokens_prefix", "token_prefix"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Potongan awal secret, untuk ditampilkan di inventaris. Bukan rahasia.
    token_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("service_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scopes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Jejak rotasi: token pengganti menunjuk token yang digantikannya.
    rotated_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("api_tokens.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
