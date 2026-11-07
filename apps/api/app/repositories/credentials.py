"""Repository kredensial: service account dan API token.

Dua aturan yang menentukan keamanan di sini:

1. **Token tidak pernah memberi lebih dari identitasnya.** Capability efektif
   adalah irisan scope token dengan capability pemiliknya (role pengguna di
   tenant itu, atau scope service account). Token yang scope-nya lebih luas dari
   pemiliknya tetap tidak bisa melewati batas pemilik.
2. **Pencabutan dan kedaluwarsa diperiksa setiap kali token dipakai**, bukan
   hanya saat diterbitkan. Tidak ada cache yang membuat token tercabut tetap
   hidup sampai proses restart.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import CAPABILITIES
from ..core.tokens import generate_token, hash_token, looks_like_token
from ..database.base import new_id, utcnow
from ..models.credentials import ApiToken, ServiceAccount
from ..models.tenant import Tenant
from . import tenants as tenant_repo


class CredentialError(ValueError):
    """Kesalahan yang aman ditampilkan ke pemanggil."""


@dataclass(frozen=True)
class TokenPrincipal:
    token_id: str
    tenant_id: str
    tenant_slug: str
    token_name: str
    kind: str  # "user" | "service"
    principal_id: str  # user_id atau service_account_id
    display_name: str
    capabilities: tuple[str, ...]
    expires_at: datetime | None
    last_used_at: datetime | None


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite mengembalikan datetime naif; samakan sebelum dibandingkan."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalise_scopes(scopes: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    unknown = [s for s in scopes if s not in CAPABILITIES]
    if unknown:
        raise CredentialError("Capability tidak dikenal: " + ", ".join(sorted(unknown)))
    # Urutan mengikuti katalog supaya respons stabil dan mudah dibandingkan.
    return tuple(c for c in CAPABILITIES if c in set(scopes))


def create_service_account(
    db: Session,
    *,
    tenant_id: str,
    name: str,
    kind: str,
    scopes: list[str] | tuple[str, ...],
    description: str = "",
    created_by_user_id: str | None = None,
) -> ServiceAccount:
    from ..models.credentials import SERVICE_ACCOUNT_KINDS

    if kind not in SERVICE_ACCOUNT_KINDS:
        raise CredentialError("Jenis service account tidak dikenal.")
    if not name.strip():
        raise CredentialError("Nama service account wajib diisi.")
    if tenant_repo.get_tenant(db, tenant_id) is None:
        raise CredentialError("Tenant tidak ditemukan.")
    if db.scalar(
        select(ServiceAccount).where(
            ServiceAccount.tenant_id == tenant_id, ServiceAccount.name == name.strip()
        )
    ):
        raise CredentialError("Nama service account sudah dipakai di tenant ini.")

    account = ServiceAccount(
        id=new_id("svc"),
        tenant_id=tenant_id,
        name=name.strip(),
        kind=kind,
        description=description,
        status="active",
        scopes_json=json.dumps(list(_normalise_scopes(scopes))),
        created_by_user_id=created_by_user_id,
    )
    db.add(account)
    db.flush()
    return account


def get_service_account(db: Session, *, tenant_id: str, service_account_id: str) -> ServiceAccount | None:
    account = db.get(ServiceAccount, service_account_id)
    if account is None or account.tenant_id != tenant_id:
        return None
    return account


def list_service_accounts(db: Session, tenant_id: str) -> list[ServiceAccount]:
    return list(
        db.scalars(
            select(ServiceAccount)
            .where(ServiceAccount.tenant_id == tenant_id)
            .order_by(ServiceAccount.name)
        ).all()
    )


def revoke_service_account(db: Session, account: ServiceAccount, reason: str = "") -> int:
    """Nonaktifkan identitas dan cabut seluruh token miliknya. Kembalikan jumlah token."""
    account.status = "revoked"
    account.revoked_at = utcnow()
    account.revoke_reason = reason
    revoked = 0
    for token in db.scalars(
        select(ApiToken).where(ApiToken.service_account_id == account.id, ApiToken.status == "active")
    ).all():
        revoke_token(db, token, reason or "service_account_revoked")
        revoked += 1
    db.flush()
    return revoked


def issue_token(
    db: Session,
    *,
    tenant_id: str,
    name: str,
    scopes: list[str] | tuple[str, ...],
    owner_user_id: str | None = None,
    service_account_id: str | None = None,
    expires_at: datetime | None = None,
    created_by_user_id: str | None = None,
    rotated_from_id: str | None = None,
) -> tuple[ApiToken, str]:
    """Terbitkan token. Plaintext dikembalikan sekali dan tidak disimpan."""
    if (owner_user_id is None) == (service_account_id is None):
        raise CredentialError("Token harus dimiliki tepat satu: pengguna atau service account.")

    tenant = tenant_repo.get_tenant(db, tenant_id)
    if tenant is None:
        raise CredentialError("Tenant tidak ditemukan.")
    if not tenant.is_active():
        raise CredentialError("Tenant tidak aktif.")

    requested = _normalise_scopes(scopes)

    if owner_user_id is not None:
        principal = tenant_repo.principal_for(db, tenant_id=tenant_id, user_id=owner_user_id)
        if principal is None:
            raise CredentialError("Pengguna bukan anggota aktif tenant ini.")
        allowed = set(principal.capabilities)
    else:
        account = get_service_account(
            db, tenant_id=tenant_id, service_account_id=service_account_id or ""
        )
        if account is None or not account.is_active():
            raise CredentialError("Service account tidak aktif.")
        allowed = set(json.loads(account.scopes_json or "[]"))

    # Scope token tidak boleh melebihi wewenang pemiliknya.
    if not set(requested).issubset(allowed):
        raise CredentialError("Scope token melebihi wewenang pemiliknya.")
    if not requested:
        raise CredentialError("Token tanpa scope tidak berguna dan tidak diterbitkan.")

    plaintext, prefix, digest = generate_token()
    token = ApiToken(
        id=new_id("tok"),
        tenant_id=tenant_id,
        name=name.strip() or "token",
        token_prefix=prefix,
        token_hash=digest,
        owner_user_id=owner_user_id,
        service_account_id=service_account_id,
        scopes_json=json.dumps(list(requested)),
        status="active",
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
        rotated_from_id=rotated_from_id,
    )
    db.add(token)
    db.flush()
    return token, plaintext


def revoke_token(db: Session, token: ApiToken, reason: str = "") -> None:
    if token.status == "revoked":
        return
    token.status = "revoked"
    token.revoked_at = utcnow()
    token.revoked_reason = reason
    db.flush()


def rotate_token(
    db: Session,
    token: ApiToken,
    *,
    name: str | None = None,
    expires_at: datetime | None = None,
    created_by_user_id: str | None = None,
) -> tuple[ApiToken, str]:
    """Cabut token lama lalu terbitkan pengganti dengan scope yang sama.

    Scope pengganti diambil dari token lama, bukan dari permintaan klien, supaya
    rotasi tidak bisa dipakai untuk menaikkan wewenang.
    """
    if token.status != "active":
        raise CredentialError("Hanya token aktif yang bisa dirotasi.")
    scopes = json.loads(token.scopes_json or "[]")
    revoke_token(db, token, "rotated")
    return issue_token(
        db,
        tenant_id=token.tenant_id,
        name=name or token.name,
        scopes=scopes,
        owner_user_id=token.owner_user_id,
        service_account_id=token.service_account_id,
        expires_at=expires_at if expires_at is not None else token.expires_at,
        created_by_user_id=created_by_user_id,
        rotated_from_id=token.id,
    )


def list_tokens(db: Session, tenant_id: str) -> list[ApiToken]:
    return list(
        db.scalars(
            select(ApiToken).where(ApiToken.tenant_id == tenant_id).order_by(ApiToken.created_at)
        ).all()
    )


def get_token(db: Session, *, tenant_id: str, token_id: str) -> ApiToken | None:
    token = db.get(ApiToken, token_id)
    if token is None or token.tenant_id != tenant_id:
        return None
    return token


def authenticate_token(
    db: Session, plaintext: str, *, now: datetime | None = None
) -> TokenPrincipal | None:
    """Validasi token. None berarti tidak sah — tanpa membedakan alasannya.

    Semua kondisi berikut menghasilkan None: bentuk salah, hash tidak cocok,
    dicabut, kedaluwarsa, tenant nonaktif, pemilik nonaktif, service account
    dicabut, atau pengguna kehilangan keanggotaan. Membedakan alasannya di
    respons akan memberi penyerang oracle tentang keadaan akun.
    """
    if not looks_like_token(plaintext):
        return None
    moment = now or utcnow()
    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(plaintext)))
    if token is None:
        return None
    if token.status != "active" or token.revoked_at is not None:
        return None

    expires = _as_utc(token.expires_at)
    if expires is not None and expires <= moment:
        return None

    tenant = db.get(Tenant, token.tenant_id)
    if tenant is None or not tenant.is_active():
        return None

    scopes = set(json.loads(token.scopes_json or "[]"))

    if token.owner_user_id is not None:
        principal = tenant_repo.principal_for(
            db, tenant_id=token.tenant_id, user_id=token.owner_user_id
        )
        if principal is None:
            return None
        effective = tuple(c for c in CAPABILITIES if c in scopes and c in set(principal.capabilities))
        return TokenPrincipal(
            token_id=token.id,
            tenant_id=token.tenant_id,
            tenant_slug=tenant.slug,
            token_name=token.name,
            kind="user",
            principal_id=principal.user_id,
            display_name=principal.display_name,
            capabilities=effective,
            expires_at=expires,
            last_used_at=_as_utc(token.last_used_at),
        )

    account = db.get(ServiceAccount, token.service_account_id)
    if account is None or not account.is_active() or account.tenant_id != token.tenant_id:
        return None
    account_scopes = set(json.loads(account.scopes_json or "[]"))
    effective = tuple(c for c in CAPABILITIES if c in scopes and c in account_scopes)
    return TokenPrincipal(
        token_id=token.id,
        tenant_id=token.tenant_id,
        tenant_slug=tenant.slug,
        token_name=token.name,
        kind="service",
        principal_id=account.id,
        display_name=account.name,
        capabilities=effective,
        expires_at=expires,
        last_used_at=_as_utc(token.last_used_at),
    )


def record_token_use(
    db: Session, token_id: str, *, now: datetime | None = None, min_interval: int = 60
) -> bool:
    """Catat `last_used_at`, tapi tidak lebih sering dari `min_interval` detik.

    Tanpa pembatasan ini setiap permintaan menjadi satu UPDATE. Dengan
    pembatasan, kolomnya tetap berguna untuk inventaris dan deteksi token
    menganggur tanpa membebani jalur baca.
    """
    token = db.get(ApiToken, token_id)
    if token is None:
        return False
    moment = now or utcnow()
    previous = _as_utc(token.last_used_at)
    if previous is not None and (moment - previous) < timedelta(seconds=min_interval):
        return False
    token.last_used_at = moment
    db.flush()
    return True
