"""Otorisasi: identitas -> capability.

Tiga jalur masuk yang sah, semuanya berakhir di satu `CallerContext`:

1. **Sesi manusia** (cookie) — pengguna yang login, diverifikasi password dan
   (bila aktif) TOTP. Capability berasal dari role keanggotaannya di tenant.
2. **API token** (`dx_...`) — dimiliki pengguna atau service account. Capability
   adalah irisan scope token dengan capability pemiliknya.
3. **Token gateway lama** (`DEXTRA_AGENT_TOKEN`/`DEXTRA_OPS_TOKEN`) — jalur
   kompatibilitas untuk MCP. Tidak membawa identitas dan tidak punya tenant.
   Dipertahankan supaya integrasi yang sudah ada tidak putus, bukan karena ini
   model yang benar.

Daftar capability adalah cermin `packages/contracts/src/authorization.ts`.
`tests/security/test_authorization_parity.py` membandingkan keduanya.

Default-deny: tanpa jalur yang valid, `get_caller` menolak dengan 401. Tidak ada
fallback, tidak ada scope default, tidak ada "development mode" yang melewati
pemeriksaan.
"""
from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

#: Metrik in-process: kegagalan pencatatan keamanan tidak lagi diam.
SECURITY_RECORD_FAILURES: dict[str, int] = {}


def _record_security_failure(site: str, exc: Exception) -> None:
    SECURITY_RECORD_FAILURES[site] = SECURITY_RECORD_FAILURES.get(site, 0) + 1
    logger.error("security record failed at %s: %s", site, exc)


from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings

Scope = Literal["agent", "ops"]

#: Semua capability yang dikenal sistem.
CAPABILITIES: tuple[str, ...] = (
    "view_own",
    "view_all",
    "create_request",
    "approve",
    "issue_mandate",
    "revoke_mandate",
    "execute",
    "view_audit",
    "edit_policy",
    "manage_users",
    "manage_integrations",
)

#: Capability yang **benar-benar** dipasang pada endpoint. Diisi oleh
#: `require_capability` saat router diimpor, jadi daftar ini tidak bisa
#: menyimpang dari kenyataan seperti daftar yang ditulis tangan.
_ENFORCED_CAPABILITIES: set[str] = set()


def enforced_capabilities() -> tuple[str, ...]:
    """Capability yang punya penegak nyata: dependency HTTP atau tool MCP.

    Dihitung, bukan dihafal. Sebelum ini `/permissions` dan `/meta` memakai
    daftar tulis-tangan yang menyebut `manage_users` dan `manage_integrations`
    "belum tersedia" padahal P10/P11 sudah menegakkannya — klaim yang salah
    pada endpoint yang justru dibaca frontend.
    """
    from ..mcp.registry import TOOL_CAPABILITY

    return tuple(sorted(_ENFORCED_CAPABILITIES | set(TOOL_CAPABILITY.values())))


def unbacked_capabilities() -> tuple[str, ...]:
    """Capability yang dikenal tetapi tidak dijaga endpoint mana pun."""
    return tuple(sorted(set(CAPABILITIES) - set(enforced_capabilities())))

SCOPE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "agent": ("view_own", "view_all", "create_request"),
    "ops": (
        "view_own",
        "view_all",
        "create_request",
        "approve",
        "issue_mandate",
        "revoke_mandate",
        "execute",
        "view_audit",
    ),
}

#: Role sistem dan capability-nya. Ini sumber tunggal untuk seed dan untuk
#: perhitungan capability seorang anggota tenant.
#:
#: Sengaja hanya memuat capability yang SUDAH punya endpoint penegak. Memberi
#: `manage_users` ke `admin` sebelum `/users` benar-benar menyaring tenant akan
#: membuka kebocoran lintas tenant pada perubahan pertama — jadi capability itu
#: ditambahkan di fase yang membangun endpoint-nya, bukan di sini.
ROLE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "viewer": ("view_own",),
    "operator": ("view_own", "view_all", "create_request"),
    "operations_manager": ("view_own", "view_all", "create_request"),
    "approver": (
        "view_own",
        "view_all",
        "create_request",
        "approve",
        "issue_mandate",
        "revoke_mandate",
        "execute",
        "view_audit",
    ),
    "auditor": ("view_own", "view_all", "view_audit"),
    #: Satu-satunya role yang memegang capability administratif. `manage_users`
    #: dipakai oleh inventaris anggota tenant, `manage_integrations` oleh
    #: pengelolaan service account, token, dan registri agen, `edit_policy` oleh
    #: perubahan policy ber-versi. Ketiganya baru masuk sini setelah endpoint
    #: penegaknya benar-benar ada dan menyaring tenant.
    "admin": (
        "view_own",
        "view_all",
        "create_request",
        "approve",
        "issue_mandate",
        "revoke_mandate",
        "execute",
        "view_audit",
        "edit_policy",
        "manage_users",
        "manage_integrations",
    ),
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "viewer": "Hanya melihat pekerjaan miliknya sendiri.",
    "operator": "Melihat seluruh pekerjaan tenant dan mengajukan permintaan.",
    "approver": "Menyetujui rencana, menerbitkan mandate, dan mengeksekusi tindakan.",
    "auditor": "Melihat seluruh pekerjaan dan seluruh audit, tanpa wewenang eksekusi.",
    "admin": "Mengelola anggota, kredensial, dan identitas mesin di dalam tenant-nya.",
}


@dataclass(frozen=True)
class CallerContext:
    scope: str
    principal: dict | None = None
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    unbacked_capabilities: tuple[str, ...] = field(default_factory=tuple)

    # --- identitas (P8+) ---
    #: Jenis jalur autentikasi: legacy_token | user_token | service_token | session
    auth_kind: str = "legacy_token"
    tenant_id: str | None = None
    principal_id: str | None = None
    display_name: str | None = None
    email: str | None = None
    session_id: str | None = None
    token_id: str | None = None
    role_name: str | None = None
    #: True bila pengguna punya MFA aktif tetapi sesi ini belum melewatinya.
    pending_mfa: bool = False

    def can(self, capability: str) -> bool:
        if self.pending_mfa:
            return False
        return capability in self.capabilities


def resolve_scope(token: str | None) -> Scope | None:
    """Petakan bearer token gateway ke scope. Tanpa fallback, tanpa default."""
    if not token:
        return None
    settings = get_settings()
    candidates: tuple[tuple[Scope, str], ...] = (
        ("agent", settings.agent_token),
        ("ops", settings.ops_token),
    )
    for scope, expected in candidates:
        # compare_digest menuntut tipe dan panjang sama; perbandingan panjang
        # eksplisit menghindari menjadi oracle waktu.
        if len(token) == len(expected) and hmac.compare_digest(token, expected):
            return scope
    return None


def caller_context(scope: Scope) -> CallerContext:
    return CallerContext(
        scope=scope,
        capabilities=SCOPE_CAPABILITIES[scope],
        auth_kind="legacy_token",
    )


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization[7:].strip()


def _context_from_bearer(db: Session, token: str) -> CallerContext | None:
    from ..repositories import credentials as credential_repo
    from .tokens import looks_like_token

    if looks_like_token(token):
        principal = credential_repo.authenticate_token(db, token)
        if principal is None:
            return None
        # Catat pemakaian di transaksi terpisah: jalur baca tidak boleh menahan
        # lock tulis sampai permintaan selesai.
        from ..database.session import session_scope

        try:
            with session_scope() as audit_db:
                credential_repo.record_token_use(audit_db, principal.token_id)
        except Exception as exc:  # pragma: no cover - kegagalan pencatatan tidak memblokir
            _record_security_failure('token_use', exc)
        return CallerContext(
            scope="service" if principal.kind == "service" else "user",
            principal={
                "principal_id": principal.principal_id,
                "display_name": principal.display_name,
                "kind": principal.kind,
            },
            capabilities=principal.capabilities,
            auth_kind="service_token" if principal.kind == "service" else "user_token",
            tenant_id=principal.tenant_id,
            principal_id=principal.principal_id,
            display_name=principal.display_name,
            token_id=principal.token_id,
        )

    scope = resolve_scope(token)
    if scope is None:
        return None
    return _bind_legacy_tenant(db, caller_context(scope))


def _bind_legacy_tenant(db: Session, context: CallerContext) -> CallerContext:
    """Ikat token gateway lama ke satu tenant, bila konfigurasi menyebutkannya.

    Tanpa `DEXTRA_LEGACY_TENANT`, token tetap berjalan seperti sebelumnya:
    `tenant_id` kosong dan setiap endpoint ber-tenant menolaknya lewat
    `require_tenant`. Itu gagal-tertutup, bukan akses lintas tenant.

    Dengan konfigurasi, token hanya melihat satu tenant. Slug yang tidak ada
    **menolak** permintaan: salah konfigurasi tidak boleh berubah menjadi akses
    global yang diam-diam.
    """
    from dataclasses import replace

    from ..repositories import tenants as tenant_repo

    slug = get_settings().legacy_tenant_slug
    if not slug:
        return context
    tenant = tenant_repo.get_tenant_by_slug(db, slug)
    if tenant is None or not tenant.is_active():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token gateway terikat ke tenant yang tidak ada atau tidak aktif.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return replace(
        context,
        tenant_id=tenant.id,
        principal_id=f"legacy:{context.scope}",
        display_name=f"Gateway {context.scope}",
    )


def _context_from_session(db: Session, token: str) -> CallerContext | None:
    from ..models.identity import User
    from ..repositories import sessions as session_repo
    from ..repositories import tenants as tenant_repo
    from ..database.session import session_scope

    row = session_repo.find_session(db, token)
    if row is None:
        return None

    # Sesi tanpa tenant aktif tidak bisa dipakai: capability tidak bisa dihitung
    # di luar tenant, dan menebaknya berarti mengarang wewenang.
    if not row.tenant_id:
        return None

    principal = tenant_repo.principal_for(db, tenant_id=row.tenant_id, user_id=row.user_id)
    if principal is None:
        return None

    try:
        with session_scope() as touch_db:
            fresh = session_repo.find_session(touch_db, token)
            if fresh is not None:
                session_repo.touch_session(touch_db, fresh)
    except Exception as exc:  # pragma: no cover
        _record_security_failure('session_touch', exc)

    user = db.get(User, row.user_id)
    pending_mfa = bool(user and user.mfa_enabled and not row.mfa_verified)

    return CallerContext(
        scope="user",
        principal={
            "principal_id": principal.user_id,
            "display_name": principal.display_name,
            "email": principal.email,
            "role": principal.role_name,
            "tenant_id": principal.tenant_id,
        },
        capabilities=() if pending_mfa else principal.capabilities,
        auth_kind="session",
        tenant_id=principal.tenant_id,
        principal_id=principal.user_id,
        display_name=principal.display_name,
        email=principal.email,
        session_id=row.id,
        role_name=principal.role_name,
        pending_mfa=pending_mfa,
    )


async def get_caller(request: Request) -> CallerContext:
    """Dependency FastAPI: default-deny untuk ketiga jalur autentikasi."""
    from ..database.session import get_session_factory

    db = get_session_factory()()
    try:
        token = _bearer_token(request)
        if request.headers.get("authorization") is not None and token is None:
            # Header ada tetapi bukan bearer: bentuk salah, bukan anonim.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Header Authorization harus memakai skema Bearer.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token:
            context = _context_from_bearer(db, token)
            if context is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token tidak dikenali atau sudah tidak berlaku.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return context

        settings = get_settings()
        cookie = request.cookies.get(settings.session_cookie_name)
        if cookie:
            context = _context_from_session(db, cookie)
            if context is not None:
                return context

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()


def _record_denial(caller: CallerContext, request: Request, capability: str) -> None:
    """Catat penolakan akses ke security_events.

    Kegagalan pencatatan tidak boleh mengubah keputusan: akses tetap ditolak
    meski penulisan event gagal. Yang tidak boleh terjadi adalah sebaliknya —
    akses diloloskan karena pencatatan gagal.
    """
    try:
        from ..database.session import session_scope
        from ..repositories import security as security_repo

        with session_scope() as db:
            security_repo.record_event(
                db,
                event_type="access_denied",
                tenant_id=caller.tenant_id,
                severity="warning",
                outcome="denied",
                actor_user_id=caller.principal_id if caller.auth_kind == "session" else None,
                actor_service_account_id=caller.principal_id
                if caller.auth_kind == "service_token"
                else None,
                actor_label=caller.email or caller.display_name or caller.scope,
                ip_address=(request.client.host if request.client else "") or "",
                user_agent=request.headers.get("user-agent", "")[:255],
                detail={
                    "capability": capability,
                    "path": request.url.path,
                    "method": request.method,
                    "role": caller.role_name,
                },
            )
    except Exception as exc:  # pragma: no cover - jalur kegagalan basis data
        _record_security_failure('access_denied', exc)


def require_capability(capability: str):
    """Dependency factory: menolak 403 jika pemanggil tidak punya capability."""
    if capability not in CAPABILITIES:
        raise ValueError(f"Capability tidak dikenal: {capability}")
    _ENFORCED_CAPABILITIES.add(capability)

    async def dependency(
        request: Request, caller: CallerContext = Depends(get_caller)
    ) -> CallerContext:
        if caller.pending_mfa:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verifikasi MFA diperlukan sebelum melanjutkan.",
            )
        if not caller.can(capability):
            _record_denial(caller, request, capability)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Pemanggil tidak memiliki capability {capability}.",
            )
        return caller

    return dependency
