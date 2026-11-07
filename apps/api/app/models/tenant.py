"""Tenant dan keanggotaan.

Tenant adalah batas keras pemisahan data. Setiap baris yang dapat dibaca lewat
API milik tepat satu tenant, dan repository menolak query tanpa filter tenant.
Batas ini ditegakkan di server — bukan dengan menyembunyikan menu di dashboard.

Catatan desain: `Membership` menghubungkan satu user ke satu tenant dengan satu
role. User yang sama boleh menjadi anggota beberapa tenant; identitasnya tetap
satu (`users.email` unik global), sehingga tidak ada struktur identitas kedua.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin

TENANT_STATUSES = ("active", "suspended")
MEMBERSHIP_STATUSES = ("active", "invited", "suspended")


class Tenant(Base, IdMixin, TimestampMixin):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    def is_active(self) -> bool:
        return self.status == "active"


class Membership(Base, IdMixin, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="membership_user"),
        Index("ix_memberships_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    #: Tenant yang dipakai saat login tanpa pilihan eksplisit.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: Diisi hanya bila undangan sudah diterima. Selama kosong, keanggotaan
    #: tidak memberi akses apa pun meski barisnya ada.
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
