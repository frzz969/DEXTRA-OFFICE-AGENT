"""Repository peristiwa keamanan dan penahan brute-force.

Pembacaan selalu difilter tenant. Baris dengan `tenant_id` NULL (login gagal
sebelum tenant diketahui) tidak pernah muncul di tampilan tenant mana pun —
hanya di ringkasan platform yang tidak diekspos ke tenant.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.base import new_id, utcnow
from ..models.security import (
    OUTCOMES,
    SECURITY_EVENT_TYPES,
    SEVERITIES,
    LoginThrottle,
    SecurityEvent,
)

#: Kebijakan default penahan login. Bisa diubah pemanggil (P8 membacanya dari
#: konfigurasi), tetapi nilai default tidak boleh "tidak ada batas".
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_MINUTES = 15
LOGIN_LOCK_MINUTES = 15


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def record_event(
    db: Session,
    *,
    event_type: str,
    tenant_id: str | None = None,
    severity: str = "info",
    outcome: str = "success",
    actor_user_id: str | None = None,
    actor_service_account_id: str | None = None,
    actor_label: str = "",
    ip_address: str = "",
    user_agent: str = "",
    detail: dict | None = None,
    at: datetime | None = None,
) -> SecurityEvent:
    """Tulis satu peristiwa. Tipe/severity/outcome divalidasi, bukan bebas."""
    if event_type not in SECURITY_EVENT_TYPES:
        raise ValueError(f"event_type tidak dikenal: {event_type}")
    if severity not in SEVERITIES:
        raise ValueError(f"severity tidak dikenal: {severity}")
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome tidak dikenal: {outcome}")

    event = SecurityEvent(
        id=new_id("sec"),
        tenant_id=tenant_id,
        at=at or utcnow(),
        event_type=event_type,
        severity=severity,
        outcome=outcome,
        actor_user_id=actor_user_id,
        actor_service_account_id=actor_service_account_id,
        actor_label=(actor_label or "")[:160],
        ip_address=(ip_address or "")[:64],
        user_agent=(user_agent or "")[:255],
        detail_json=json.dumps(detail or {}, sort_keys=True, default=str),
    )
    db.add(event)
    db.flush()
    return event


def list_events(
    db: Session,
    tenant_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    since: datetime | None = None,
) -> list[SecurityEvent]:
    query = select(SecurityEvent).where(SecurityEvent.tenant_id == tenant_id)
    if event_type:
        query = query.where(SecurityEvent.event_type == event_type)
    if since:
        query = query.where(SecurityEvent.at >= since)
    query = query.order_by(SecurityEvent.at.desc(), SecurityEvent.id.desc())
    return list(db.scalars(query.limit(max(1, min(limit, 200))).offset(max(0, offset))).all())


def count_events(
    db: Session,
    tenant_id: str,
    *,
    event_type: str | None = None,
    since: datetime | None = None,
) -> int:
    query = select(func.count(SecurityEvent.id)).where(SecurityEvent.tenant_id == tenant_id)
    if event_type:
        query = query.where(SecurityEvent.event_type == event_type)
    if since:
        query = query.where(SecurityEvent.at >= since)
    return int(db.scalar(query) or 0)


def event_counts_by_type(db: Session, tenant_id: str, *, since: datetime) -> dict[str, int]:
    rows = db.execute(
        select(SecurityEvent.event_type, func.count(SecurityEvent.id))
        .where(SecurityEvent.tenant_id == tenant_id, SecurityEvent.at >= since)
        .group_by(SecurityEvent.event_type)
    ).all()
    return {event_type: int(total) for event_type, total in rows}


# --- Penahan brute-force ---------------------------------------------------


def _get_throttle(db: Session, kind: str, identifier: str) -> LoginThrottle | None:
    return db.scalar(
        select(LoginThrottle).where(LoginThrottle.kind == kind, LoginThrottle.identifier == identifier)
    )


def locked_until(db: Session, kind: str, identifier: str, *, now: datetime | None = None) -> datetime | None:
    """Kunci aktif untuk subjek ini, atau None."""
    row = _get_throttle(db, kind, identifier)
    if row is None:
        return None
    moment = now or utcnow()
    until = _as_utc(row.locked_until)
    if until is None or until <= moment:
        return None
    return until


def register_failure(
    db: Session,
    kind: str,
    identifier: str,
    *,
    now: datetime | None = None,
    max_failures: int = LOGIN_MAX_FAILURES,
    window_minutes: int = LOGIN_WINDOW_MINUTES,
    lock_minutes: int = LOGIN_LOCK_MINUTES,
) -> tuple[int, datetime | None]:
    """Catat kegagalan dan kunci bila melewati batas. Kembalikan (hitung, kunci)."""
    moment = now or utcnow()
    row = _get_throttle(db, kind, identifier)
    if row is None:
        row = LoginThrottle(
            id=new_id("thr"),
            kind=kind,
            identifier=identifier,
            failure_count=0,
            first_failure_at=moment,
            last_failure_at=moment,
        )
        db.add(row)
        db.flush()

    first = _as_utc(row.first_failure_at)
    if first is None or (moment - first) > timedelta(minutes=window_minutes):
        # Jendela baru: hitungan lama tidak relevan lagi.
        row.failure_count = 0
        row.first_failure_at = moment

    row.failure_count = int(row.failure_count or 0) + 1
    row.last_failure_at = moment
    if row.failure_count >= max_failures:
        row.locked_until = moment + timedelta(minutes=lock_minutes)
    db.flush()
    return row.failure_count, _as_utc(row.locked_until)


def clear_failures(db: Session, kind: str, identifier: str) -> None:
    row = _get_throttle(db, kind, identifier)
    if row is None:
        return
    row.failure_count = 0
    row.first_failure_at = None
    row.locked_until = None
    db.flush()


# --- Ringkasan Security Center --------------------------------------------


def _naive_utc(moment: datetime) -> datetime:
    """SQLite menyimpan DATETIME tanpa zona; perbandingan harus apel ke apel."""
    if moment.tzinfo is not None:
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


def tenant_overview(db: Session, tenant_id: str, *, now: datetime | None = None) -> dict:
    """Angka nyata dari tabel nyata.

    Tidak ada nilai yang dikarang: kalau tabel kosong, hasilnya nol — bukan
    estimasi atau rata-rata yang tidak bisa ditelusuri.
    """
    from sqlalchemy import or_

    from ..models.credentials import ApiToken, ServiceAccount
    from ..models.identity import Session as SessionRow, User
    from ..models.tenant import Membership

    moment = now or utcnow()
    naive = _naive_utc(moment)

    active_sessions = db.scalar(
        select(func.count(SessionRow.id)).where(
            SessionRow.tenant_id == tenant_id,
            SessionRow.revoked_at.is_(None),
            SessionRow.expires_at > naive,
            or_(SessionRow.idle_expires_at.is_(None), SessionRow.idle_expires_at > naive),
        )
    )
    active_tokens = db.scalar(
        select(func.count(ApiToken.id)).where(
            ApiToken.tenant_id == tenant_id,
            ApiToken.status == "active",
            or_(ApiToken.expires_at.is_(None), ApiToken.expires_at > naive),
        )
    )
    total_tokens = db.scalar(
        select(func.count(ApiToken.id)).where(ApiToken.tenant_id == tenant_id)
    )
    active_services = db.scalar(
        select(func.count(ServiceAccount.id)).where(
            ServiceAccount.tenant_id == tenant_id,
            ServiceAccount.status == "active",
        )
    )
    members = db.scalar(
        select(func.count(Membership.id)).where(
            Membership.tenant_id == tenant_id, Membership.status == "active"
        )
    )
    mfa_users = db.scalar(
        select(func.count(Membership.id))
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.tenant_id == tenant_id,
            Membership.status == "active",
            User.mfa_enabled.is_(True),
        )
    )

    since = moment - timedelta(hours=24)
    counts = event_counts_by_type(db, tenant_id, since=since)
    failed_logins = counts.get("login_failed", 0) + counts.get("login_throttled", 0)
    denied = counts.get("access_denied", 0) + counts.get("csrf_rejected", 0)

    return {
        "tenant_id": tenant_id,
        "generated_at": moment.isoformat(),
        "sessions": {"active": int(active_sessions or 0)},
        "tokens": {"active": int(active_tokens or 0), "total": int(total_tokens or 0)},
        "service_accounts": {"active": int(active_services or 0)},
        "members": {"active": int(members or 0), "mfa_enabled": int(mfa_users or 0)},
        "last_24h": {
            "events_by_type": counts,
            "failed_logins": failed_logins,
            "denied": denied,
        },
    }
