"""Repository sesi manusia.

Token sesi dan token CSRF disimpan sebagai hash. Sesi punya dua batas waktu:

- `expires_at` — absolut. Tidak pernah diperpanjang. Login ulang diperlukan.
- `idle_expires_at` — diperpanjang saat sesi dipakai, dengan ambang 60 detik
  supaya setiap permintaan tidak menjadi UPDATE.

Rotasi dilakukan saat tingkat kepercayaan berubah (verifikasi MFA, ganti
password). Sesi lama dicabut, bukan dibiarkan hidup dengan `rotated_from_id`
sebagai jejak.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..core.config import get_settings
from ..core.tokens import hash_token
from ..database.base import new_id, utcnow
from ..models.identity import Session as SessionRow

#: Ambang minimum sebelum `idle_expires_at` diperpanjang lagi.
IDLE_REFRESH_SECONDS = 60


@dataclass(frozen=True)
class IssuedSession:
    session_id: str
    token: str
    csrf_token: str
    expires_at: datetime
    idle_expires_at: datetime


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_session(
    db: DbSession,
    *,
    user_id: str,
    tenant_id: str | None,
    ip_address: str = "",
    user_agent: str = "",
    mfa_verified: bool = False,
    now: datetime | None = None,
) -> IssuedSession:
    settings = get_settings()
    moment = now or utcnow()
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = moment + timedelta(minutes=settings.session_absolute_minutes)
    idle_expires_at = moment + timedelta(minutes=settings.session_idle_minutes)

    row = SessionRow(
        id=new_id("ses"),
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=hash_token(token),
        csrf_hash=hash_token(csrf_token),
        issued_at=moment,
        expires_at=expires_at,
        idle_expires_at=idle_expires_at,
        last_seen_at=moment,
        mfa_verified=mfa_verified,
        ip_address=(ip_address or "")[:64],
        user_agent=(user_agent or "")[:255],
    )
    db.add(row)
    db.flush()
    return IssuedSession(
        session_id=row.id,
        token=token,
        csrf_token=csrf_token,
        expires_at=expires_at,
        idle_expires_at=idle_expires_at,
    )


def find_session(db: DbSession, token: str | None, *, now: datetime | None = None) -> SessionRow | None:
    """Sesi yang masih sah, atau None.

    Kedaluwarsa absolut dan idle sama-sama menutup sesi. Sesi yang ditutup karena
    kedaluwarsa tetap tersimpan (dengan `revoked_at` terisi) supaya riwayatnya
    jujur, bukan dihapus.
    """
    if not token:
        return None
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == hash_token(token)))
    if row is None:
        return None
    if row.revoked_at is not None:
        return None

    moment = now or utcnow()
    expires = _as_utc(row.expires_at)
    if expires is None or expires <= moment:
        return None
    idle = _as_utc(row.idle_expires_at)
    if idle is not None and idle <= moment:
        return None
    return row


def touch_session(db: DbSession, row: SessionRow, *, now: datetime | None = None) -> bool:
    """Perpanjang batas idle bila sudah lewat ambang. True bila diperbarui."""
    settings = get_settings()
    moment = now or utcnow()
    last = _as_utc(row.last_seen_at)
    if last is not None and (moment - last).total_seconds() < IDLE_REFRESH_SECONDS:
        return False
    row.last_seen_at = moment
    candidate = moment + timedelta(minutes=settings.session_idle_minutes)
    absolute = _as_utc(row.expires_at)
    # Batas idle tidak boleh melewati batas absolut.
    row.idle_expires_at = min(candidate, absolute) if absolute else candidate
    db.flush()
    return True


def rotate_session(
    db: DbSession,
    row: SessionRow,
    *,
    mfa_verified: bool | None = None,
    now: datetime | None = None,
) -> IssuedSession:
    """Cabut sesi lama, terbitkan yang baru dengan jejak `rotated_from_id`."""
    issued = create_session(
        db,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        mfa_verified=row.mfa_verified if mfa_verified is None else mfa_verified,
        now=now,
    )
    revoke_session(db, row, "rotated")
    new_row = db.get(SessionRow, issued.session_id)
    if new_row is not None:
        new_row.rotated_from_id = row.id
        db.flush()
    return issued


def revoke_session(db: DbSession, row: SessionRow, reason: str = "logout") -> None:
    if row.revoked_at is not None:
        return
    row.revoked_at = utcnow()
    row.revoked_reason = reason[:64]
    db.flush()


def revoke_all_for_user(
    db: DbSession, user_id: str, *, except_session_id: str | None = None, reason: str = "revoked"
) -> int:
    rows = db.scalars(
        select(SessionRow).where(SessionRow.user_id == user_id, SessionRow.revoked_at.is_(None))
    ).all()
    count = 0
    for row in rows:
        if except_session_id and row.id == except_session_id:
            continue
        revoke_session(db, row, reason)
        count += 1
    return count


def list_active_sessions(
    db: DbSession, *, tenant_id: str, user_id: str, now: datetime | None = None
) -> list[SessionRow]:
    moment = now or utcnow()
    rows = db.scalars(
        select(SessionRow)
        .where(
            SessionRow.user_id == user_id,
            SessionRow.tenant_id == tenant_id,
            SessionRow.revoked_at.is_(None),
        )
        .order_by(SessionRow.issued_at.desc())
    ).all()
    return [
        row
        for row in rows
        if (_as_utc(row.expires_at) or moment) > moment
        and ((_as_utc(row.idle_expires_at) or moment) > moment)
    ]


def verify_csrf(row: SessionRow, token: str | None) -> bool:
    """Double-submit: cookie yang bisa dibaca JS harus cocok dengan hash di sesi."""
    if not token or not row.csrf_hash:
        return False
    import hmac

    return hmac.compare_digest(hash_token(token), row.csrf_hash)
