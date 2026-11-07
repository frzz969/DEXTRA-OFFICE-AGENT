"""Manajemen API token.

Aturan yang menentukan keamanan:

- Secret hanya dikembalikan **sekali**, pada respons pembuatan/rotasi. Tidak ada
  endpoint yang bisa menampilkannya lagi.
- Scope token tidak boleh melebihi capability pemiliknya. Ini ditegakkan di
  repository, bukan di handler, supaya jalur lain tidak bisa melewatinya.
- Pencabutan berlaku seketika: `authenticate_token` memeriksa status setiap
  permintaan, tanpa cache.
- Membuat token baru menuntut sesi manusia. Token yang bocor tidak bisa
  mencetak token pengganti — ia hanya bisa dipakai sampai dicabut.
"""
from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.base import utcnow
from ...database.session import get_db
from ...repositories import audit as audit_repo
from ...repositories import credentials as cred
from ...repositories import security as security_repo

router = APIRouter(tags=["tokens"])


class CreateTokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1, max_length=20)
    #: Bila diisi, token milik service account. Menuntut `manage_integrations`.
    service_account_id: str | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class RevokeTokenRequest(BaseModel):
    reason: str = Field(default="", max_length=200)


class RotateTokenRequest(BaseModel):
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


def _serialize(token) -> dict:
    return {
        "id": token.id,
        "name": token.name,
        "prefix": token.token_prefix,
        "scopes": json.loads(token.scopes_json or "[]"),
        "status": token.status,
        "owner": "service" if token.service_account_id else "user",
        "owner_id": token.service_account_id or token.owner_user_id,
        "created_at": token.created_at.isoformat(),
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
        "rotated_from_id": token.rotated_from_id,
    }


def _expiry(days: int | None):
    return utcnow() + timedelta(days=days) if days else None


def _record(db, *, event_type: str, caller: CallerContext, token_id: str, detail: dict | None = None):
    security_repo.record_event(
        db,
        event_type=event_type,
        tenant_id=caller.tenant_id,
        actor_user_id=caller.principal_id if caller.auth_kind == "session" else None,
        actor_service_account_id=caller.principal_id if caller.auth_kind == "service_token" else None,
        actor_label=caller.email or caller.display_name or "",
        detail={"token_id": token_id, **(detail or {})},
    )
    audit_repo.append_event(
        db,
        event_type=event_type,
        actor="user" if caller.auth_kind == "session" else caller.scope,
        scope=caller.scope,
        action=event_type,
        resource=token_id,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail=detail or {},
    )


@router.get("/tokens")
def list_tokens(
    db: DbSession = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    tenant_id = require_tenant(caller)
    can_manage = caller.can("manage_integrations")
    rows = cred.list_tokens(db, tenant_id)
    if not can_manage:
        # Tanpa capability pengelolaan, pemanggil hanya melihat tokennya sendiri.
        rows = [
            row
            for row in rows
            if row.owner_user_id == caller.principal_id
            or row.service_account_id == caller.principal_id
        ]
    return {"items": [_serialize(row) for row in rows], "tenant_id": tenant_id}


@router.post("/tokens", status_code=201)
def create_token(
    payload: CreateTokenRequest,
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    tenant_id = require_tenant(caller)
    if caller.auth_kind != "session":
        raise HTTPException(
            status_code=403,
            detail="Pembuatan token baru menuntut sesi pengguna, bukan token yang sudah ada.",
        )
    if caller.pending_mfa:
        raise HTTPException(status_code=403, detail="Verifikasi MFA diperlukan lebih dulu.")

    service_account_id = payload.service_account_id
    if service_account_id:
        if not caller.can("manage_integrations"):
            raise HTTPException(
                status_code=403, detail="Membuat token untuk service account menuntut manage_integrations."
            )
        account = cred.get_service_account(
            db, tenant_id=tenant_id, service_account_id=service_account_id
        )
        if account is None:
            raise HTTPException(status_code=404, detail="Service account tidak ditemukan.")
    try:
        token, plaintext = cred.issue_token(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            scopes=payload.scopes,
            owner_user_id=None if service_account_id else caller.principal_id,
            service_account_id=service_account_id,
            expires_at=_expiry(payload.expires_in_days),
            created_by_user_id=caller.principal_id,
        )
    except cred.CredentialError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _record(db, event_type="token_created", caller=caller, token_id=token.id, detail={"name": token.name})
    db.commit()
    return {
        **_serialize(token),
        # Satu-satunya kemunculan secret. Tidak disimpan, tidak bisa diambil lagi.
        "token": plaintext,
        "note": "Simpan token ini sekarang. Server hanya menyimpan hash-nya.",
    }


@router.post("/tokens/{token_id}/revoke")
def revoke_token(
    token_id: str,
    payload: RevokeTokenRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    tenant_id = require_tenant(caller)
    token = cred.get_token(db, tenant_id=tenant_id, token_id=token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token tidak ditemukan.")
    if not _may_manage(caller, token):
        raise HTTPException(status_code=404, detail="Token tidak ditemukan.")

    cred.revoke_token(db, token, payload.reason or "revoked_by_user")
    _record(
        db,
        event_type="token_revoked",
        caller=caller,
        token_id=token.id,
        detail={"reason": payload.reason},
    )
    db.commit()
    return _serialize(token)


@router.post("/tokens/{token_id}/rotate")
def rotate_token(
    token_id: str,
    payload: RotateTokenRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    tenant_id = require_tenant(caller)
    token = cred.get_token(db, tenant_id=tenant_id, token_id=token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token tidak ditemukan.")
    if not _may_manage(caller, token):
        raise HTTPException(status_code=404, detail="Token tidak ditemukan.")
    if caller.auth_kind != "session" and not caller.can("manage_integrations"):
        raise HTTPException(status_code=403, detail="Rotasi token menuntut sesi atau manage_integrations.")
    try:
        replacement, plaintext = cred.rotate_token(
            db,
            token,
            expires_at=_expiry(payload.expires_in_days),
            created_by_user_id=caller.principal_id if caller.auth_kind == "session" else None,
        )
    except cred.CredentialError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _record(
        db,
        event_type="token_created",
        caller=caller,
        token_id=replacement.id,
        detail={"rotated_from": token.id},
    )
    db.commit()
    return {
        **_serialize(replacement),
        "token": plaintext,
        "rotated_from": token.id,
        "note": "Token lama sudah dicabut. Simpan token baru sekarang.",
    }


def _may_manage(caller: CallerContext, token) -> bool:
    if caller.can("manage_integrations"):
        return True
    if token.owner_user_id is not None and token.owner_user_id == caller.principal_id:
        return True
    if token.service_account_id is not None and token.service_account_id == caller.principal_id:
        return True
    return False
