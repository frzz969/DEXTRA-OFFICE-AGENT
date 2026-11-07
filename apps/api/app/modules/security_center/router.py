"""Security Center: backend untuk peristiwa, sesi, dan inventaris keamanan.

Semua angka berasal dari tabel yang benar-benar diisi jalur autentikasi. Tidak
ada metrik yang dikarang, tidak ada "skor risiko" yang tidak bisa ditelusuri ke
barisnya.

Dua tingkat akses:

- `view_audit` (auditor, approver, admin) — membaca peristiwa dan ringkasan.
- `manage_users` (admin) — mencabut sesi milik orang lain.

Pemisahan ini disengaja: auditor harus bisa memeriksa tanpa bisa mengubah.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.base import utcnow
from ...database.session import get_db
from ...models.identity import Session as SessionRow
from ...models.identity import User
from ...repositories import audit as audit_repo
from ...repositories import credentials as cred
from ...repositories import security as security_repo
from ...repositories import sessions as session_repo

router = APIRouter(tags=["security"])


@router.get("/security/overview")
def overview(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    tenant_id = require_tenant(caller)
    payload = security_repo.tenant_overview(db, tenant_id)
    payload["capabilities"] = {
        "can_revoke_sessions": caller.can("manage_users"),
    }
    return payload


@router.get("/security/events")
def events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None, max_length=48),
    hours: int = Query(default=168, ge=1, le=2160),
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    tenant_id = require_tenant(caller)
    since = utcnow() - timedelta(hours=hours)
    rows = security_repo.list_events(
        db, tenant_id, limit=limit, offset=offset, event_type=event_type, since=since
    )
    total = security_repo.count_events(db, tenant_id, event_type=event_type, since=since)
    return {
        "items": [
            {
                "id": row.id,
                "at": row.at.isoformat(),
                "event_type": row.event_type,
                "severity": row.severity,
                "outcome": row.outcome,
                "actor_label": row.actor_label,
                "actor_user_id": row.actor_user_id,
                "actor_service_account_id": row.actor_service_account_id,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "detail": row.detail_json,
            }
            for row in rows
        ],
        "total": total,
        "window_hours": hours,
    }


@router.get("/security/login-history")
def login_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    """Riwayat login dari security_events, bukan dari tabel terpisah.

    Satu sumber: kalau login dicatat di dua tempat, cepat atau lambat keduanya
    berbeda dan tidak ada yang tahu mana yang benar.
    """
    tenant_id = require_tenant(caller)
    types = ("login_succeeded", "login_failed", "login_throttled", "logout")
    rows = []
    for event_type in types:
        rows.extend(
            security_repo.list_events(db, tenant_id, limit=limit, event_type=event_type)
        )
    rows.sort(key=lambda row: row.at, reverse=True)
    return {
        "items": [
            {
                "at": row.at.isoformat(),
                "event_type": row.event_type,
                "outcome": row.outcome,
                "actor_label": row.actor_label,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "detail": row.detail_json,
            }
            for row in rows[:limit]
        ]
    }


@router.get("/security/sessions")
def tenant_sessions(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Sesi aktif seluruh anggota tenant. Hanya admin."""
    tenant_id = require_tenant(caller)
    now = utcnow()
    rows = db.scalars(
        select(SessionRow)
        .where(
            SessionRow.tenant_id == tenant_id,
            SessionRow.revoked_at.is_(None),
            SessionRow.expires_at > now.replace(tzinfo=None),
        )
        .order_by(SessionRow.issued_at.desc())
    ).all()
    #: Hanya pengguna yang muncul di sesi tenant ini. `select(User)` tanpa filter
    #: membaca seluruh pengguna di database — tidak bocor hari ini karena hasilnya
    #: hanya dipakai sebagai peta, tetapi itu kebiasaan yang menjadi kebocoran
    #: begitu seseorang memakainya untuk hal lain.
    user_ids = {row.user_id for row in rows}
    users = (
        {user.id: user for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()}
        if user_ids
        else {}
    )
    return {
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "user_email": users[row.user_id].email if row.user_id in users else None,
                "issued_at": row.issued_at.isoformat(),
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "expires_at": row.expires_at.isoformat(),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "mfa_verified": row.mfa_verified,
            }
            for row in rows
        ]
    }


@router.post("/security/sessions/{session_id}/revoke")
def revoke_tenant_session(
    session_id: str,
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    tenant_id = require_tenant(caller)
    row = db.get(SessionRow, session_id)
    # Sesi tenant lain tidak dibedakan dari sesi yang tidak ada.
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    session_repo.revoke_session(db, row, "revoked_by_admin")
    security_repo.record_event(
        db,
        event_type="session_revoked",
        tenant_id=tenant_id,
        severity="warning",
        actor_user_id=caller.principal_id,
        actor_label=caller.email or "",
        ip_address=(request.client.host if request.client else "") or "",
        user_agent=request.headers.get("user-agent", "")[:255],
        detail={"session_id": row.id, "target_user_id": row.user_id, "by": "admin"},
    )
    audit_repo.append_event(
        db,
        event_type="session_revoked",
        actor="user",
        scope=caller.scope,
        action="revoke_session",
        resource=row.id,
        decision="deny",
        tenant_id=caller.tenant_id,
        detail={"target_user_id": row.user_id},
    )
    db.commit()
    return {"revoked": True, "id": row.id}


@router.get("/security/tokens")
def token_inventory(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    """Inventaris token tenant. Tidak pernah memuat secret — hanya prefix."""
    tenant_id = require_tenant(caller)
    rows = cred.list_tokens(db, tenant_id)
    accounts = {a.id: a for a in cred.list_service_accounts(db, tenant_id)}
    return {
        "items": [
            {
                "id": token.id,
                "name": token.name,
                "prefix": token.token_prefix,
                "status": token.status,
                "owner": "service" if token.service_account_id else "user",
                "owner_name": accounts[token.service_account_id].name
                if token.service_account_id in accounts
                else token.owner_user_id,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
            }
            for token in rows
        ]
    }


@router.get("/security/service-identities")
def service_identity_inventory(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    accounts = cred.list_service_accounts(db, tenant_id)
    tokens = cred.list_tokens(db, tenant_id)
    active_by_account: dict[str, int] = {}
    for token in tokens:
        if token.service_account_id and token.status == "active":
            active_by_account[token.service_account_id] = (
                active_by_account.get(token.service_account_id, 0) + 1
            )
    return {
        "items": [
            {
                "id": account.id,
                "name": account.name,
                "kind": account.kind,
                "status": account.status,
                "active_tokens": active_by_account.get(account.id, 0),
                "created_at": account.created_at.isoformat(),
                "revoked_at": account.revoked_at.isoformat() if account.revoked_at else None,
            }
            for account in accounts
        ]
    }


@router.get("/security/mfa-status")
def mfa_status(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Status MFA per anggota. Angka, bukan label 'aman'."""
    tenant_id = require_tenant(caller)
    from ...models.tenant import Membership

    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == tenant_id, Membership.status == "active")
        .order_by(User.email)
    ).all()
    items = [
        {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "mfa_enabled": user.mfa_enabled,
            "mfa_enrolled_at": user.mfa_enrolled_at.isoformat() if user.mfa_enrolled_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
        for user, _membership in rows
    ]
    enabled = sum(1 for item in items if item["mfa_enabled"])
    return {"items": items, "enabled": enabled, "total": len(items)}
