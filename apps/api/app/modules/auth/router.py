"""Autentikasi manusia: login, sesi, MFA, password.

Prinsip yang dipegang:

- **Satu pesan untuk semua kegagalan login.** Email tidak dikenal, password
  salah, tenant salah, dan akun nonaktif menghasilkan respons yang sama. Kalau
  berbeda, endpoint ini menjadi alat enumerasi akun.
- **Tidak ada password default.** Pengguna tanpa `password_hash` tidak bisa
  login; tidak ada jalur "development" yang melewati verifikasi.
- **MFA tidak diklaim aktif sebelum benar-benar lolos.** `mfa_enabled` baru
  menjadi True setelah kode dari authenticator diverifikasi. Sesi yang belum
  melewati MFA punya capability kosong dan ditolak oleh `require_capability`.
- **Rotasi sesi saat tingkat kepercayaan berubah** (verifikasi MFA, ganti
  password). Sesi lama dicabut, bukan dibiarkan hidup.
- **Rate limit di database**, bukan di memori proses.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ...core import totp
from ...core import mfa_crypto
from ...core.config import get_settings
from ...core.passwords import (
    hash_password,
    needs_rehash,
    password_policy_error,
    verify_password,
)
from ...core.security import CallerContext, get_caller
from ...database.session import get_db
from ...database.base import utcnow
from ...models.identity import Session as SessionRow
from ...models.identity import User
from ...models.tenant import Tenant
from ...repositories import audit as audit_repo
from ...repositories import security as security_repo
from ...repositories import sessions as session_repo
from ...repositories import tenants as tenant_repo

router = APIRouter(tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Hash tiruan untuk menyamakan waktu respons ketika email tidak dikenal.
#: Tanpa ini, "email tidak ada" selesai jauh lebih cepat daripada "password
#: salah", dan selisih itu cukup untuk enumerasi.
_DUMMY_HASH = hash_password("dummy-password-untuk-penyamaan-waktu")


# --- Model permintaan -------------------------------------------------------


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)
    #: Slug tenant yang dipilih. Kosong = tenant default pengguna.
    tenant: str | None = Field(default=None, max_length=64)


class CodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class DisableMfaRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    code: str = Field(min_length=6, max_length=10)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


# --- Pembantu ---------------------------------------------------------------


def _client_ip(request: Request) -> str:
    return (request.client.host if request.client else "") or ""


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")[:255]


def _normalise_email(raw: str) -> str:
    return raw.strip().lower()


def _tenant_slug(db: DbSession, tenant_id: str | None) -> str | None:
    if not tenant_id:
        return None
    tenant = db.get(Tenant, tenant_id)
    return tenant.slug if tenant else None


def _set_cookies(response: Response, issued: session_repo.IssuedSession) -> None:
    settings = get_settings()
    max_age = int((issued.expires_at - utcnow()).total_seconds())
    response.set_cookie(
        settings.session_cookie_name,
        issued.token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    # Cookie CSRF harus bisa dibaca JavaScript untuk double-submit; ia bukan
    # rahasia, dan tidak memberi akses apa pun tanpa cookie sesi.
    response.set_cookie(
        settings.csrf_cookie_name,
        issued.csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def _clear_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(name, path="/")


def _principal_payload(
    db: DbSession,
    *,
    user: User,
    tenant_id: str,
    role_name: str,
    capabilities: tuple[str, ...],
    pending_mfa: bool,
) -> dict:
    return {
        "principal_id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "tenant_id": tenant_id,
        "tenant_slug": _tenant_slug(db, tenant_id),
        "role": role_name,
        "capabilities": list(capabilities),
        "mfa_enabled": user.mfa_enabled,
        "pending_mfa": pending_mfa,
    }


def _current_session_row(request: Request, db: DbSession) -> tuple[SessionRow, User]:
    """Sesi dari cookie. 401 bila tidak ada/tidak sah."""
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    row = session_repo.find_session(db, token)
    if row is None:
        raise HTTPException(status_code=401, detail="Sesi tidak ditemukan atau sudah berakhir.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Sesi tidak ditemukan atau sudah berakhir.")
    return row, user


def _throttle_subjects(email: str, ip: str) -> list[tuple[str, str]]:
    subjects: list[tuple[str, str]] = [("email", email)]
    if ip:
        subjects.append(("ip", ip))
    return subjects


def _check_throttle(db: DbSession, email: str, ip: str, now: datetime) -> datetime | None:
    """Kunci aktif paling lama di antara subjek, atau None."""
    settings = get_settings()
    blocked: datetime | None = None
    for kind, identifier in _throttle_subjects(email, ip):
        until = security_repo.locked_until(db, kind, identifier, now=now)
        if until is not None and (blocked is None or until > blocked):
            blocked = until
    return blocked


def _record_failure(db: DbSession, email: str, ip: str, now: datetime) -> datetime | None:
    settings = get_settings()
    locked: datetime | None = None
    for kind, identifier in _throttle_subjects(email, ip):
        _, until = security_repo.register_failure(
            db,
            kind,
            identifier,
            now=now,
            max_failures=settings.login_max_failures,
            window_minutes=settings.login_window_minutes,
            lock_minutes=settings.login_lock_minutes,
        )
        if until is not None:
            locked = until
    return locked


def _clear_failures(db: DbSession, email: str, ip: str) -> None:
    for kind, identifier in _throttle_subjects(email, ip):
        security_repo.clear_failures(db, kind, identifier)


def _audit_login(
    db: DbSession,
    *,
    event_type: str,
    severity: str,
    outcome: str,
    email: str,
    ip: str,
    user_agent: str,
    tenant_id: str | None = None,
    user_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """Tulis security event dan audit chain dalam satu transaksi.

    Dua catatan, dua tujuan: security event untuk Security Center (peristiwa
    identitas), audit chain untuk tata kelola (siapa melakukan apa).
    """
    security_repo.record_event(
        db,
        event_type=event_type,
        tenant_id=tenant_id,
        severity=severity,
        outcome=outcome,
        actor_user_id=user_id,
        actor_label=email,
        ip_address=ip,
        user_agent=user_agent,
        detail=detail or {},
    )
    # A16: kegagalan login juga masuk audit_chain (decision=deny), bukan hanya
    # security_events. Risiko pertumbuhan rantai oleh lalu lintas penyerang
    # diterima secara eksplisit: tanpa jejak audit, brute-force tidak tercatat
    # sebagai keputusan tata kelola. append_event kini terkunci+retry.
    _is_success = outcome == "success"
    audit_repo.append_event(
        db,
        event_type=event_type,
        actor="user" if user_id else "anonymous",
        scope="user" if user_id else "none",
        action=event_type,
        resource=user_id or email,
        decision="allow" if _is_success else "deny",
        tenant_id=tenant_id,
        detail={"ip": ip, **(detail or {})},
    )


# --- Login / logout ---------------------------------------------------------


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    now = utcnow()
    email = _normalise_email(payload.email)
    ip = _client_ip(request)
    user_agent = _user_agent(request)

    if not _EMAIL_RE.match(email):
        # Bentuk salah diperlakukan sama seperti kredensial salah.
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    blocked = _check_throttle(db, email, ip, now)
    if blocked is not None:
        retry = max(1, int((blocked - now).total_seconds()))
        security_repo.record_event(
            db,
            event_type="login_throttled",
            severity="warning",
            outcome="denied",
            actor_label=email,
            ip_address=ip,
            user_agent=user_agent,
            detail={"retry_after": retry},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Terlalu banyak percobaan login. Coba lagi nanti.",
            headers={"Retry-After": str(retry)},
        )

    user = db.scalar(select(User).where(User.email == email))
    # Email tidak dikenal tetap melewati verifikasi scrypt terhadap hash tiruan,
    # supaya waktu respons tidak membocorkan keberadaan akun.
    password_ok = verify_password(payload.password, user.password_hash if user else _DUMMY_HASH)

    if user is None or not password_ok or not user.is_active:
        locked = _record_failure(db, email, ip, now)
        if user is not None:
            user.failed_login_count = int(user.failed_login_count or 0) + 1
        # Kegagalan diatribusikan ke tenant pengguna bila penggunanya dikenal,
        # supaya admin tenant melihat percobaan terhadap anggotanya. Email tak
        # dikenal tetap tanpa tenant — tidak ada yang bisa ditebak.
        failure_tenant = (
            tenant_repo.default_tenant_for_user(db, user.id) if user is not None else None
        )
        _audit_login(
            db,
            event_type="login_failed",
            severity="warning",
            outcome="failure",
            email=email,
            ip=ip,
            user_agent=user_agent,
            user_id=user.id if user else None,
            tenant_id=failure_tenant,
            detail={"reason": "invalid_credentials", "locked": bool(locked)},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    # --- Kredensial benar ---
    tenant_id = _resolve_tenant(db, user, payload.tenant)
    if tenant_id is None:
        # Terautentikasi tetapi tidak punya tenant aktif: tidak ada wewenang yang
        # bisa dihitung. Pesan tetap umum.
        _record_failure(db, email, ip, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    principal = tenant_repo.principal_for(db, tenant_id=tenant_id, user_id=user.id)
    if principal is None:
        _record_failure(db, email, ip, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    _clear_failures(db, email, ip)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if needs_rehash(user.password_hash):
        # Parameter hashing naik: perbarui diam-diam saat login berhasil.
        user.password_hash = hash_password(payload.password)

    pending_mfa = bool(user.mfa_enabled)
    issued = session_repo.create_session(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        ip_address=ip,
        user_agent=user_agent,
        mfa_verified=not pending_mfa,
        now=now,
    )
    _audit_login(
        db,
        event_type="login_succeeded",
        severity="info",
        outcome="success",
        email=email,
        ip=ip,
        user_agent=user_agent,
        tenant_id=tenant_id,
        user_id=user.id,
        detail={"mfa_required": pending_mfa, "session_id": issued.session_id},
    )
    db.commit()

    _set_cookies(response, issued)
    return {
        "authenticated": True,
        "mfa_required": pending_mfa,
        "principal": _principal_payload(
            db,
            user=user,
            tenant_id=tenant_id,
            role_name=principal.role_name,
            capabilities=() if pending_mfa else principal.capabilities,
            pending_mfa=pending_mfa,
        ),
        "session": {
            "id": issued.session_id,
            "expires_at": issued.expires_at.isoformat(),
            "idle_expires_at": issued.idle_expires_at.isoformat(),
        },
        "csrf_token": issued.csrf_token,
    }


def _resolve_tenant(db: DbSession, user: User, requested_slug: str | None) -> str | None:
    memberships = [
        m
        for m in tenant_repo.list_memberships_for_user(db, user.id)
        if m.status == "active" and m.accepted_at is not None
    ]
    if not memberships:
        return None
    allowed = []
    for membership in memberships:
        tenant = db.get(Tenant, membership.tenant_id)
        if tenant is not None and tenant.is_active():
            allowed.append((membership, tenant))
    if not allowed:
        return None

    if requested_slug:
        for membership, tenant in allowed:
            if tenant.slug == requested_slug:
                return tenant.id
        # Tenant yang diminta bukan milik pengguna: jangan jatuh ke default,
        # karena itu menyembunyikan kesalahan konfigurasi.
        return None

    for membership, tenant in allowed:
        if membership.is_default:
            return tenant.id
    return allowed[0][1].id


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)) -> Response:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    row = session_repo.find_session(db, token)
    if row is not None:
        user = db.get(User, row.user_id)
        session_repo.revoke_session(db, row, "logout")
        security_repo.record_event(
            db,
            event_type="logout",
            tenant_id=row.tenant_id,
            actor_user_id=row.user_id,
            actor_label=user.email if user else "",
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            detail={"session_id": row.id},
        )
        audit_repo.append_event(
            db,
            event_type="logout",
            actor="user",
            scope="user",
            action="logout",
            resource=row.user_id,
            decision="allow",
            tenant_id=row.tenant_id,
            detail={"session_id": row.id},
        )
        db.commit()

    _clear_cookies(response)
    response.status_code = 204
    return response


# --- Konteks sesi -----------------------------------------------------------


@router.get("/auth/session")
def session_info(
    db: DbSession = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    payload = {
        "authenticated": True,
        "auth_kind": caller.auth_kind,
        "pending_mfa": caller.pending_mfa,
        "scope": caller.scope,
        "capabilities": list(caller.capabilities),
        "principal": caller.principal,
    }
    if caller.auth_kind == "session" and caller.tenant_id and caller.principal_id:
        principal = tenant_repo.principal_for(
            db, tenant_id=caller.tenant_id, user_id=caller.principal_id
        )
        if principal is not None:
            payload["tenant"] = {
                "id": principal.tenant_id,
                "slug": _tenant_slug(db, principal.tenant_id),
            }
            payload["role"] = principal.role_name
            payload["mfa_enabled"] = principal.mfa_enabled
    return payload


# --- MFA --------------------------------------------------------------------


@router.post("/auth/mfa/enroll")
def mfa_enroll(
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    if caller.auth_kind != "session" or not caller.principal_id:
        raise HTTPException(status_code=400, detail="Hanya sesi pengguna yang bisa mendaftarkan MFA.")
    if caller.pending_mfa:
        raise HTTPException(status_code=403, detail="Verifikasi MFA diperlukan lebih dulu.")
    user = db.get(User, caller.principal_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sesi tidak sah.")
    if user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA sudah aktif untuk akun ini.")

    settings = get_settings()
    secret = totp.generate_secret()
    user.mfa_secret = mfa_crypto.encrypt_secret(secret)
    user.mfa_enrolled_at = None  # baru diisi setelah kode pertama benar
    security_repo.record_event(
        db,
        event_type="mfa_enrolled",
        tenant_id=caller.tenant_id,
        actor_user_id=user.id,
        actor_label=user.email,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        detail={"stage": "secret_issued", "active": False},
    )
    db.commit()
    return {
        "secret": secret,
        "otpauth_uri": totp.provisioning_uri(
            secret, account=user.email, issuer=settings.mfa_issuer
        ),
        "active": False,
        "note": "MFA belum aktif. Aktifkan dengan kode 6 digit dari authenticator.",
    }


MFA_MAX_FAILURES = 5
MFA_WINDOW_MINUTES = 15
MFA_LOCK_MINUTES = 15


def _mfa_throttle_subjects(user_id: str, ip: str) -> list[tuple[str, str]]:
    subjects: list[tuple[str, str]] = [("mfa_user", user_id)]
    if ip:
        subjects.append(("mfa_ip", ip))
    return subjects


def _check_mfa_throttle(db: DbSession, user_id: str, ip: str, now: datetime) -> datetime | None:
    blocked: datetime | None = None
    for kind, identifier in _mfa_throttle_subjects(user_id, ip):
        until = security_repo.locked_until(db, kind, identifier, now=now)
        if until is not None and (blocked is None or until > blocked):
            blocked = until
    return blocked


def _record_mfa_failure(db: DbSession, user_id: str, ip: str, now: datetime) -> datetime | None:
    locked: datetime | None = None
    for kind, identifier in _mfa_throttle_subjects(user_id, ip):
        _, until = security_repo.register_failure(
            db, kind, identifier, now=now,
            max_failures=MFA_MAX_FAILURES, window_minutes=MFA_WINDOW_MINUTES,
            lock_minutes=MFA_LOCK_MINUTES,
        )
        if until is not None:
            locked = until
    return locked


def _mfa_throttled_response(blocked: datetime, now: datetime) -> HTTPException:
    retry = max(1, int((blocked - now).total_seconds()))
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Terlalu banyak percobaan kode MFA. Coba lagi nanti.",
        headers={"Retry-After": str(retry)},
    )


def _consume_totp(db: DbSession, user: User, code: str, now: datetime) -> bool:
    """Verifikasi kode dan tandai langkahnya supaya tidak bisa dipakai ulang."""
    if not user.mfa_secret:
        return False
    ok, step = totp.verify_code(
        mfa_crypto.decrypt_secret(user.mfa_secret),
        code,
        timestamp=now.timestamp(),
        last_used_step=user.mfa_last_step,
    )
    if not ok:
        return False
    user.mfa_last_step = step
    db.flush()
    return True


@router.post("/auth/mfa/activate")
def mfa_activate(
    payload: CodeRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    if caller.auth_kind != "session" or not caller.principal_id:
        raise HTTPException(status_code=400, detail="Hanya sesi pengguna yang bisa mengaktifkan MFA.")
    user = db.get(User, caller.principal_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sesi tidak sah.")
    if user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA sudah aktif untuk akun ini.")
    if not user.mfa_secret:
        raise HTTPException(status_code=409, detail="Belum ada secret MFA. Mulai dari pendaftaran.")

    now = utcnow()
    _ip = _client_ip(request)
    _blocked = _check_mfa_throttle(db, user.id, _ip, now)
    if _blocked is not None:
        db.commit()
        raise _mfa_throttled_response(_blocked, now)
    if not _consume_totp(db, user, payload.code, now):
        _record_mfa_failure(db, user.id, _ip, now)
        security_repo.record_event(
            db,
            event_type="mfa_failed",
            tenant_id=caller.tenant_id,
            severity="warning",
            outcome="failure",
            actor_user_id=user.id,
            actor_label=user.email,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            detail={"stage": "activate"},
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Kode MFA tidak sah.")

    user.mfa_enabled = True
    user.mfa_enrolled_at = now
    security_repo.record_event(
        db,
        event_type="mfa_enrolled",
        tenant_id=caller.tenant_id,
        actor_user_id=user.id,
        actor_label=user.email,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        detail={"stage": "activated", "active": True},
    )
    row = db.get(SessionRow, caller.session_id) if caller.session_id else None
    issued = session_repo.rotate_session(db, row, mfa_verified=True, now=now) if row else None
    db.commit()
    if issued:
        _set_cookies(response, issued)
    return {"active": True, "mfa_enabled": True}


@router.post("/auth/mfa/verify")
def mfa_verify(
    payload: CodeRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
) -> dict:
    """Langkah kedua login. Sesi yang belum terverifikasi ditukar dengan yang baru."""
    row, user = _current_session_row(request, db)
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=409, detail="MFA tidak aktif untuk akun ini.")
    if row.mfa_verified:
        raise HTTPException(status_code=409, detail="Sesi ini sudah melewati verifikasi MFA.")

    now = utcnow()
    _ip = _client_ip(request)
    _blocked = _check_mfa_throttle(db, user.id, _ip, now)
    if _blocked is not None:
        db.commit()
        raise _mfa_throttled_response(_blocked, now)
    if not _consume_totp(db, user, payload.code, now):
        _record_mfa_failure(db, user.id, _ip, now)
        security_repo.record_event(
            db,
            event_type="mfa_failed",
            tenant_id=row.tenant_id,
            severity="warning",
            outcome="failure",
            actor_user_id=user.id,
            actor_label=user.email,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            detail={"stage": "login"},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Kode MFA tidak sah.")

    issued = session_repo.rotate_session(db, row, mfa_verified=True, now=now)
    principal = tenant_repo.principal_for(db, tenant_id=row.tenant_id, user_id=user.id)
    security_repo.record_event(
        db,
        event_type="login_succeeded",
        tenant_id=row.tenant_id,
        actor_user_id=user.id,
        actor_label=user.email,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        detail={"stage": "mfa_verified", "session_id": issued.session_id},
    )
    db.commit()
    _set_cookies(response, issued)
    return {
        "authenticated": True,
        "mfa_required": False,
        "principal": _principal_payload(
            db,
            user=user,
            tenant_id=row.tenant_id or "",
            role_name=principal.role_name if principal else "",
            capabilities=principal.capabilities if principal else (),
            pending_mfa=False,
        ),
        "session": {
            "id": issued.session_id,
            "expires_at": issued.expires_at.isoformat(),
            "idle_expires_at": issued.idle_expires_at.isoformat(),
        },
        "csrf_token": issued.csrf_token,
    }


@router.post("/auth/mfa/disable")
def mfa_disable(
    payload: DisableMfaRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
) -> dict:
    """Menonaktifkan MFA menuntut password DAN kode: satu faktor tidak cukup."""
    row, user = _current_session_row(request, db)
    if not user.mfa_enabled:
        raise HTTPException(status_code=409, detail="MFA tidak aktif untuk akun ini.")
    if not row.mfa_verified:
        raise HTTPException(status_code=403, detail="Verifikasi MFA diperlukan lebih dulu.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Password salah.")
    now = utcnow()
    _ip = _client_ip(request)
    _blocked = _check_mfa_throttle(db, user.id, _ip, now)
    if _blocked is not None:
        db.commit()
        raise _mfa_throttled_response(_blocked, now)
    if not _consume_totp(db, user, payload.code, now):
        _record_mfa_failure(db, user.id, _ip, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Kode MFA tidak sah.")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_enrolled_at = None
    user.mfa_last_step = None
    security_repo.record_event(
        db,
        event_type="mfa_disabled",
        tenant_id=row.tenant_id,
        severity="warning",
        actor_user_id=user.id,
        actor_label=user.email,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    issued = session_repo.rotate_session(db, row, mfa_verified=True, now=now)
    db.commit()
    _set_cookies(response, issued)
    return {"active": False, "mfa_enabled": False}


# --- Password ---------------------------------------------------------------


@router.post("/auth/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
) -> dict:
    row, user = _current_session_row(request, db)
    if not row.mfa_verified and user.mfa_enabled:
        raise HTTPException(status_code=403, detail="Verifikasi MFA diperlukan lebih dulu.")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Password saat ini salah.")

    error = password_policy_error(payload.new_password)
    if error:
        raise HTTPException(status_code=422, detail=error)
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="Password baru harus berbeda dari yang lama.")

    now = utcnow()
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = now
    revoked = session_repo.revoke_all_for_user(
        db, user.id, except_session_id=row.id, reason="password_changed"
    )
    security_repo.record_event(
        db,
        event_type="password_changed",
        tenant_id=row.tenant_id,
        severity="warning",
        actor_user_id=user.id,
        actor_label=user.email,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        detail={"sessions_revoked": revoked},
    )
    audit_repo.append_event(
        db,
        event_type="password_changed",
        actor="user",
        scope="user",
        action="change_password",
        resource=user.id,
        decision="allow",
        tenant_id=row.tenant_id,
        detail={"sessions_revoked": revoked},
    )
    # Sesi saat ini dirotasi: password berubah berarti token lama tidak berlaku.
    issued = session_repo.rotate_session(db, row, now=now)
    db.commit()
    _set_cookies(response, issued)
    return {"changed": True, "sessions_revoked": revoked}


# --- Inventaris sesi --------------------------------------------------------


@router.get("/auth/sessions")
def list_sessions(
    db: DbSession = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    if caller.auth_kind != "session" or not caller.tenant_id or not caller.principal_id:
        raise HTTPException(status_code=400, detail="Hanya sesi pengguna yang punya daftar sesi.")
    rows = session_repo.list_active_sessions(
        db, tenant_id=caller.tenant_id, user_id=caller.principal_id
    )
    return {
        "items": [
            {
                "id": row.id,
                "issued_at": row.issued_at.isoformat(),
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "expires_at": row.expires_at.isoformat(),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "mfa_verified": row.mfa_verified,
                "current": row.id == caller.session_id,
            }
            for row in rows
        ]
    }


@router.post("/auth/sessions/{session_id}/revoke")
def revoke_session_endpoint(
    session_id: str,
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    if caller.auth_kind != "session" or not caller.principal_id:
        raise HTTPException(status_code=400, detail="Hanya sesi pengguna yang bisa mencabut sesi.")
    row = db.get(SessionRow, session_id)
    if row is None or row.user_id != caller.principal_id:
        # Sesi milik orang lain tidak dibedakan dari sesi yang tidak ada.
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    session_repo.revoke_session(db, row, "revoked_by_user")
    security_repo.record_event(
        db,
        event_type="session_revoked",
        tenant_id=row.tenant_id,
        actor_user_id=caller.principal_id,
        actor_label=caller.email or "",
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        detail={"session_id": row.id},
    )
    db.commit()
    return {"revoked": True, "id": row.id}
