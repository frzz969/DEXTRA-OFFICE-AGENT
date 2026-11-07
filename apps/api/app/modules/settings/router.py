"""Settings tenant: baca/tulis settings_json lewat endpoint resmi.

GET: pemanggil terautentikasi yang terikat tenant.
PATCH: butuh capability manage_integrations (admin). Merge top-level keys
(kunci lain tidak hilang). Setiap perubahan di-audit (append-only).
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.authz import require_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.session import get_db
from ...models.tenant import Tenant
from ...repositories import audit as audit_repo

router = APIRouter(tags=["settings"])

_MAX_KEYS = 50
_MAX_BYTES = 20000


class SettingsPatch(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


def _parse(tenant: Tenant) -> dict:
    try:
        data = json.loads(tenant.settings_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _serialize(tenant: Tenant) -> dict:
    return {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.name,
        "settings": _parse(tenant),
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)) -> dict:
    tenant_id = require_tenant(caller)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")
    return _serialize(tenant)


@router.patch("/settings")
def update_settings(
    payload: SettingsPatch,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")
    if len(payload.settings) > _MAX_KEYS:
        raise HTTPException(status_code=422, detail=f"Terlalu banyak kunci (maks {_MAX_KEYS}).")
    merged = {**_parse(tenant), **payload.settings}
    try:
        encoded = json.dumps(merged, sort_keys=True)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Settings harus JSON-serializable.") from None
    if len(encoded) > _MAX_BYTES:
        raise HTTPException(status_code=422, detail=f"Settings terlalu besar (maks {_MAX_BYTES} byte JSON).")
    tenant.settings_json = encoded
    audit_repo.append_event(
        db,
        event_type="settings_updated",
        actor=caller.email or caller.display_name or caller.scope,
        scope=caller.scope,
        action="update_settings",
        resource=tenant_id,
        decision="allow",
        tenant_id=tenant_id,
        detail={"keys": sorted(payload.settings.keys())},
    )
    db.commit()
    db.refresh(tenant)
    return _serialize(tenant)
