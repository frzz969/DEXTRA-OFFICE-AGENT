"""Identitas dan akses: users, roles, permissions, sessions.

Sejak P7 tabel ini adalah sumber keputusan otorisasi untuk jalur sesi manusia.
Token MCP lama (`DEXTRA_AGENT_TOKEN`/`DEXTRA_OPS_TOKEN`) tetap bekerja sebagai
jalur kompatibilitas, tetapi tidak lagi menjadi satu-satunya jalur.

Yang sengaja dijaga:

- `User` tidak menyimpan password mentah. `password_hash` memakai scrypt dengan
  salt per pengguna (lihat `core/passwords.py`).
- `Role` dimiliki tenant. Role sistem (`is_system`, `tenant_id` NULL) berlaku di
  semua tenant dan dijaga unik oleh partial index — bukan oleh asumsi di kode.
- `Session` menyimpan hash token, bukan token. Sesi punya dua batas waktu:
  `expires_at` (absolut) dan `idle_expires_at` (diperpanjang saat dipakai).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, IdMixin, TimestampMixin, new_id, utcnow


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Diisi hanya bila identitas benar-benar diverifikasi.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- P8: kredensial manusia ---
    #: `NULL` berarti pengguna belum punya password dan tidak bisa login dengan
    #: password. Tidak ada password default yang dibuat diam-diam.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: TOTP. `mfa_enabled` hanya True setelah enrollment diverifikasi dengan
    #: kode yang benar — bukan saat secret dibuat.
    #: Ciphertext at-rest (lihat core/mfa_crypto.py). Nilai lama berupa base32
    #: plaintext tetap dibaca; enrollment baru selalu terenkripsi bila kunci ada.
    mfa_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Langkah waktu TOTP terakhir yang dipakai. Mencegah kode yang sama dipakai
    #: dua kali dalam jendela 30 detiknya.
    mfa_last_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", lazy="selectin")


class Role(Base, IdMixin, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="role_tenant_name"),
        # Role sistem berlaku lintas tenant. NULL tidak saling bentrok di unique
        # constraint biasa, jadi keunikannya dijaga partial index.
        Index(
            "uq_roles_system_name",
            "name",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
            sqlite_where=text("tenant_id IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    #: NULL = role sistem yang berlaku di semua tenant.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", lazy="selectin"
    )


class Permission(Base, IdMixin, TimestampMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    #: Capability yang diwakili, harus ada di core.security.CAPABILITIES.
    capability: Mapped[str] = mapped_column(String(64), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="user_role"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ur"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="role_permission"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rp"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )


class Session(Base, IdMixin):
    """Sesi login. Token sesi disimpan sebagai hash, bukan plaintext."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_sessions_tenant_created", "tenant_id", "issued_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    #: Tenant aktif untuk sesi ini. Principal selalu dievaluasi di dalam tenant.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    #: Hash token CSRF. Token mentah ada di cookie yang bisa dibaca JavaScript
    #: (double-submit), hash-nya di sini untuk dibandingkan.
    csrf_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    #: Batas absolut. Tidak pernah diperpanjang.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Batas idle. Diperpanjang saat sesi dipakai.
    idle_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Sesi hasil rotasi menunjuk sesi sebelumnya.
    rotated_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    #: True hanya bila langkah MFA kedua benar-benar lolos pada sesi ini.
    mfa_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
