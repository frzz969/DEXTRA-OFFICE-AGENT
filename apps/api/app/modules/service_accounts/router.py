"""Identitas mesin: service account untuk worker, MCP server, agent, integrasi.

Service account adalah identitas, bukan kredensial. Kredensialnya diterbitkan
lewat `/tokens` dengan `service_account_id` — satu jalur token, bukan dua.
Rotasi berarti mencabut token lama dan menerbitkan yang baru; identitasnya tetap.

Yang dijaga:

- Identitas mesin tidak pernah memakai akun manusia. Tidak ada kolom `email`
  di sini, dan tidak ada cara login sebagai service account.
- Scope service account adalah batas atas. Token miliknya tidak bisa lebih luas.
- Pencabutan identitas mencabut seluruh tokennya sekaligus.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.session import get_db
from ...models.credentials import SERVICE_ACCOUNT_KINDS
from ...repositories import audit as audit_repo
from ...repositories import credentials as cred
from ...repositories import security as security_repo

router = APIRouter(tags=["service-accounts"])


class CreateServiceAccountRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str
    description: str = Field(default="", max_length=500)
    scopes: list[str] = Field(min_length=1, max_length=20)


class RevokeServiceAccountRequest(BaseModel):
    reason: str = Field(default="", max_length=200)


def _serialize(account) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "kind": account.kind,
        "description": account.description,
        "status": account.status,
        "scopes": json.loads(account.scopes_json or "[]"),
        "created_at": account.created_at.isoformat(),
        "revoked_at": account.revoked_at.isoformat() if account.revoked_at else None,
        "revoke_reason": account.revoke_reason,
    }


@router.get("/service-accounts")
def list_service_accounts(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    accounts = cred.list_service_accounts(db, tenant_id)
    token_counts: dict[str, int] = {}
    for token in cred.list_tokens(db, tenant_id):
        if token.service_account_id:
            token_counts[token.service_account_id] = token_counts.get(token.service_account_id, 0) + 1
    return {
        "items": [
            {**_serialize(account), "token_count": token_counts.get(account.id, 0)}
            for account in accounts
        ],
        "kinds": list(SERVICE_ACCOUNT_KINDS),
    }


@router.post("/service-accounts", status_code=201)
def create_service_account(
    payload: CreateServiceAccountRequest,
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    if caller.auth_kind != "session":
        # Membuat identitas mesin adalah tindakan administratif manusia.
        raise HTTPException(status_code=403, detail="Pembuatan service account menuntut sesi pengguna.")
    try:
        account = cred.create_service_account(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            kind=payload.kind,
            scopes=payload.scopes,
            description=payload.description,
            created_by_user_id=caller.principal_id,
        )
    except cred.CredentialError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    security_repo.record_event(
        db,
        event_type="service_account_created",
        tenant_id=tenant_id,
        actor_user_id=caller.principal_id,
        actor_label=caller.email or "",
        ip_address=(request.client.host if request.client else "") or "",
        user_agent=request.headers.get("user-agent", "")[:255],
        detail={"service_account_id": account.id, "kind": account.kind},
    )
    audit_repo.append_event(
        db,
        event_type="service_account_created",
        actor="user",
        scope=caller.scope,
        action="create_service_account",
        resource=account.id,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={"kind": account.kind, "name": account.name},
    )
    db.commit()
    return _serialize(account)


@router.get("/service-accounts/{service_account_id}")
def get_service_account(
    service_account_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    account = cred.get_service_account(
        db, tenant_id=tenant_id, service_account_id=service_account_id
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Service account tidak ditemukan.")
    tokens = [
        {
            "id": token.id,
            "name": token.name,
            "prefix": token.token_prefix,
            "status": token.status,
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        }
        for token in cred.list_tokens(db, tenant_id)
        if token.service_account_id == account.id
    ]
    return {**_serialize(account), "tokens": tokens}


@router.post("/service-accounts/{service_account_id}/revoke")
def revoke_service_account(
    service_account_id: str,
    payload: RevokeServiceAccountRequest,
    request: Request,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    account = cred.get_service_account(
        db, tenant_id=tenant_id, service_account_id=service_account_id
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Service account tidak ditemukan.")

    revoked = cred.revoke_service_account(db, account, payload.reason or "revoked_by_user")
    security_repo.record_event(
        db,
        event_type="service_account_revoked",
        tenant_id=tenant_id,
        severity="warning",
        actor_user_id=caller.principal_id,
        actor_label=caller.email or "",
        ip_address=(request.client.host if request.client else "") or "",
        user_agent=request.headers.get("user-agent", "")[:255],
        detail={"service_account_id": account.id, "tokens_revoked": revoked},
    )
    audit_repo.append_event(
        db,
        event_type="service_account_revoked",
        actor="user",
        scope=caller.scope,
        action="revoke_service_account",
        resource=account.id,
        decision="deny",
        tenant_id=caller.tenant_id,
        detail={"tokens_revoked": revoked, "reason": payload.reason},
    )
    db.commit()
    return {**_serialize(account), "tokens_revoked": revoked}
