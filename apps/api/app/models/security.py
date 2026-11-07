"""Peristiwa keamanan dan penahan brute-force.

Dua tabel, dua tujuan berbeda:

- `security_events` adalah catatan apa yang terjadi pada identitas: login,
  kegagalan, pencabutan sesi, pembuatan/pencabutan token, akses ditolak. Ini
  bukan salinan audit chain. Audit chain mencatat keputusan tata kelola
  (plan, approval, mandate, eksekusi); security event mencatat peristiwa
  identitas. Keduanya ditulis di tempat yang berbeda dan tidak saling
  menggantikan.
- `login_throttles` menyimpan hitungan gagal login di database, bukan di memori
  proses. Penghitung di memori hilang saat proses restart dan tidak berlaku
  lintas worker — untuk brute-force, itu berarti perlindungan yang bisa
  direset dengan me-restart proses.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, TimestampMixin, utcnow

#: Jenis peristiwa yang dikenal. Ditulis eksplisit supaya tidak ada string bebas
#: yang membuat statistik Security Center tidak bisa dihitung.
SECURITY_EVENT_TYPES = (
    "login_succeeded",
    "login_failed",
    "login_throttled",
    "logout",
    "session_created",
    "session_revoked",
    "session_expired",
    "mfa_enrolled",
    "mfa_disabled",
    "mfa_failed",
    "password_changed",
    "password_reset",
    "token_created",
    "token_revoked",
    "token_expired",
    "token_rejected",
    "service_account_created",
    "service_account_disabled",
    "service_account_revoked",
    "access_denied",
    "csrf_rejected",
)

SEVERITIES = ("info", "warning", "critical")
OUTCOMES = ("success", "failure", "denied")


class SecurityEvent(Base, IdMixin):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_tenant_at", "tenant_id", "at"),
        Index("ix_security_events_type_at", "event_type", "at"),
    )

    #: Null hanya untuk peristiwa yang terjadi sebelum tenant diketahui
    #: (mis. login gagal dengan email tak dikenal). Tidak pernah ditebak.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_service_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("service_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    #: Label yang dibaca manusia saat baris pemiliknya sudah dihapus.
    actor_label: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class LoginThrottle(Base, IdMixin, TimestampMixin):
    __tablename__ = "login_throttles"
    __table_args__ = (UniqueConstraint("kind", "identifier", name="login_throttle_subject"),)

    #: "email" atau "ip". Dua dimensi terpisah supaya penyerang tidak bisa
    #: menghindari batas per-akun dengan berpindah IP, atau sebaliknya.
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
