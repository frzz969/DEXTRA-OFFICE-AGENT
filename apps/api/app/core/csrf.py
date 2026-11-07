"""CSRF: double-submit cookie yang diverifikasi ke sesi.

Token CSRF dikirim ke klien di cookie yang bisa dibaca JavaScript
(`dextra_csrf`), dan harus dikembalikan di header `X-CSRF-Token` pada setiap
permintaan yang mengubah keadaan. Server membandingkan hash-nya dengan yang
tersimpan di baris sesi — jadi menyalin cookie saja tidak cukup: penyerang juga
harus membaca cookie, dan itu terhalang same-origin policy.

Yang **tidak** dilakukan: mengandalkan `SameSite` saja. `SameSite=Lax` membantu,
tetapi tidak semua klien mematuhinya dan tidak melindungi dari serangan pada
subdomain. Dua lapis lebih baik daripada satu.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..database.session import session_scope
from ..repositories import security as security_repo
from ..repositories import sessions as session_repo
from .config import get_settings

STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Endpoint yang membuat sesi pertama. Token CSRF baru ada SETELAH login, jadi
#: mewajibkannya di sini adalah lingkaran. Penggantinya: bila header `Origin`
#: ada, ia harus termasuk origin yang diizinkan. Itu menutup login CSRF tanpa
#: memerlukan token yang belum bisa dimiliki klien.
CSRF_EXEMPT_PATHS = frozenset({"/api/v1/auth/login"})


def _origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    return origin in get_settings().allowed_origins


def check_csrf(request: Request) -> tuple[bool, str]:
    """Kembalikan (boleh, alasan). Dipisah dari middleware supaya bisa diuji."""
    settings = get_settings()
    session_cookie = request.cookies.get(settings.session_cookie_name)
    if not session_cookie:
        # Tidak ada sesi cookie: permintaan memakai bearer token atau anonim.
        # CSRF tidak relevan, dan otentikasi tetap ditentukan route.
        return True, "no_session"

    header = request.headers.get("x-csrf-token")
    with session_scope() as db:
        row = session_repo.find_session(db, session_cookie)
        if row is None:
            # Sesi tidak sah: biarkan route yang menjawab 401. Menolak di sini
            # akan menyamarkan sesi kedaluwarsa sebagai masalah CSRF.
            return True, "invalid_session"
        if session_repo.verify_csrf(row, header):
            return True, "ok"
        security_repo.record_event(
            db,
            event_type="csrf_rejected",
            tenant_id=row.tenant_id,
            severity="warning",
            outcome="denied",
            actor_user_id=row.user_id,
            actor_label=row.user_id,
            ip_address=(request.client.host if request.client else "") or "",
            user_agent=request.headers.get("user-agent", "")[:255],
            detail={"path": request.url.path, "method": request.method},
        )
        return False, "csrf_mismatch"


class CsrfMiddleware(BaseHTTPMiddleware):
    """Menolak permintaan pengubah keadaan tanpa token CSRF yang cocok."""

    async def dispatch(self, request: Request, call_next):
        if request.method in STATE_CHANGING:
            if request.url.path in CSRF_EXEMPT_PATHS:
                if not _origin_allowed(request):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": "Origin tidak diizinkan.",
                            "code": "origin_rejected",
                        },
                    )
                return await call_next(request)
            allowed, reason = check_csrf(request)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Token CSRF tidak sah atau tidak ada.",
                        "code": "csrf_failed",
                    },
                )
        return await call_next(request)


def require_csrf(request: Request) -> None:
    """Versi dependency, untuk route yang ingin memeriksa ulang secara eksplisit."""
    allowed, reason = check_csrf(request)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF tidak sah atau tidak ada.",
        )
