"""Data Management: export tenant (JSON) + seed/reset berguard.

Pola existing: tenant-scoped (tenant_id dari pemanggil, bukan body),
capability lewat require_capability, setiap aksi di-audit append-only.

- GET /data/export  (view_audit): seluruh data tenant sebagai JSON.
  Secret (password_hash, mfa_secret, hash token) TIDAK pernah ikut.
- POST /data/seed   (manage_integrations = admin): seed demo idempotent
  satu conversation work-request (metadata intent) agar feed
  /alerts/plans dan rule conversation_work_request bisa fire.
- POST /data/reset  (manage_integrations + confirm==slug tenant):
  HANYA scope "conversations" yang didukung — menghapus conversation
  dan pesannya. Governance, audit, identitas, dan tenant TIDAK pernah
  disentuh, jadi reset tidak bisa menghancurkan data demo inti.
  Tidak ada capability `manage_settings` di katalog (lihat
  core.security.CAPABILITIES); guard admin yang dipakai adalah
  `manage_integrations`, capability administratif yang sudah ada.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...models.audit import AuditEvent
from ...models.conversation import Conversation, ConversationMessage
from ...models.execution import Execution
from ...models.governance import Approval, Mandate, Policy
from ...models.identity import Role, User
from ...models.office import OfficePlanRequest
from ...models.tenant import Membership, Tenant
from ...repositories import audit as audit_repo

router = APIRouter(tags=["data-management"])

SEED_INTENT = "Menyiapkan laporan demo mingguan untuk finance"
SEED_PLAN_ID = "pln_demo_seed"


class ResetRequest(BaseModel):
    confirm: str = Field(default="", max_length=128)
    scope: str = Field(default="conversations", max_length=32)


def _actor(caller: CallerContext) -> str:
    return caller.email or caller.display_name or caller.scope


def _j(value: str) -> object:
    try:
        data = json.loads(value or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, (dict, list)) else {}


@router.get("/data/export")
def export_tenant(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_audit")),
) -> dict:
    tenant_id = require_tenant(caller)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")

    members = db.execute(
        select(Membership, User, Role)
        .join(User, User.id == Membership.user_id)
        .join(Role, Role.id == Membership.role_id)
        .where(Membership.tenant_id == tenant_id)
        .order_by(User.email)
    ).all()
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
        .order_by(Conversation.created_at.asc())
    ).all()
    messages = db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.tenant_id == tenant_id)
        .order_by(ConversationMessage.created_at.asc())
        .limit(5000)
    ).all()
    plans = db.scalars(
        select(OfficePlanRequest)
        .where(OfficePlanRequest.tenant_id == tenant_id)
        .order_by(OfficePlanRequest.created_at.asc())
    ).all()
    approvals = db.scalars(
        select(Approval).where(Approval.tenant_id == tenant_id).order_by(Approval.created_at.asc())
    ).all()
    mandates = db.scalars(
        select(Mandate).where(Mandate.tenant_id == tenant_id).order_by(Mandate.created_at.asc())
    ).all()
    executions = db.scalars(
        select(Execution).where(Execution.tenant_id == tenant_id).order_by(Execution.created_at.asc())
    ).all()
    policies = db.scalars(
        select(Policy).where(Policy.tenant_id == tenant_id).order_by(Policy.slug.asc())
    ).all()
    audit_events = db.scalars(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.seq.asc()).limit(5000)
    ).all()

    body = {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.name,
        "tenant_status": tenant.status,
        "settings": _j(tenant.settings_json),
        "members": [
            {
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": role.name,
                "status": membership.status,
                "is_default": membership.is_default,
            }
            for membership, user, role in members
        ],
        "conversations": [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "agent_id": row.agent_id,
                "metadata": _j(row.metadata_json),
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
            for row in conversations
        ],
        "messages": [
            {
                "id": row.id,
                "conversation_id": row.conversation_id,
                "role": row.role,
                "content": row.content,
                "metadata": _j(row.metadata_json),
                "created_at": row.created_at.isoformat(),
            }
            for row in messages
        ],
        "office_plans": [
            {
                "id": row.id,
                "request_id": row.request_id,
                "plan_id": row.plan_id,
                "plan_hash": row.plan_hash,
                "status": row.status,
                "actions": _j(row.actions_json),
                "findings": _j(row.findings_json),
                "created_at": row.created_at.isoformat(),
            }
            for row in plans
        ],
        "approvals": [
            {
                "id": row.id,
                "plan_id": row.plan_id,
                "approver_id": row.approver_id,
                "decision": row.decision,
                "reason": row.reason,
                "mandate_id": row.mandate_id,
                "decided_at": row.decided_at.isoformat(),
            }
            for row in approvals
        ],
        "mandates": [
            {
                "id": row.id,
                "plan_id": row.plan_id,
                "action_id": row.action_id,
                "action_type": row.action_type,
                "status": row.status,
                "approver_id": row.approver_id,
                "issued_at": row.issued_at.isoformat(),
                "expires_at": row.expires_at.isoformat(),
            }
            for row in mandates
        ],
        "executions": [
            {
                "id": row.id,
                "plan_id": row.plan_id,
                "mandate_id": row.mandate_id,
                "action_id": row.action_id,
                "status": row.status,
                "adapter": row.adapter,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in executions
        ],
        "policies": [
            {"id": row.id, "slug": row.slug, "title": row.title, "scope": row.scope, "is_active": row.is_active}
            for row in policies
        ],
        "audit_events": [
            {
                "seq": row.seq,
                "event_type": row.event_type,
                "actor": row.actor,
                "action": row.action,
                "resource": row.resource,
                "decision": row.decision,
                "plan_id": row.plan_id,
                "at": row.at.isoformat(),
            }
            for row in audit_events
        ],
    }
    audit_repo.append_event(
        db,
        event_type="data_exported",
        actor=_actor(caller),
        scope=caller.scope,
        action="export_tenant_data",
        resource=tenant_id,
        decision="allow",
        tenant_id=tenant_id,
        detail={
            "conversations": len(conversations),
            "messages": len(messages),
            "office_plans": len(plans),
            "approvals": len(approvals),
            "mandates": len(mandates),
            "executions": len(executions),
            "audit_events": len(audit_events),
        },
    )
    db.commit()
    return body


@router.post("/data/seed")
def seed_demo(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    """Seed demo idempotent: satu conversation work-request per tenant."""
    tenant_id = require_tenant(caller)
    existing = db.scalar(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.metadata_json.like(f"%{SEED_PLAN_ID}%"),
        )
    )
    if existing is not None:
        return {
            "conversation_id": existing.id,
            "plan_id": SEED_PLAN_ID,
            "intent": SEED_INTENT,
            "created": False,
        }
    row = Conversation(
        id=new_id("cnv"),
        tenant_id=tenant_id,
        title="Demo: laporan mingguan",
        status="active",
        created_by_user_id=caller.principal_id if caller.auth_kind == "session" else None,
        metadata_json=json.dumps(
            {"intent": SEED_INTENT, "plan_id": SEED_PLAN_ID, "seed": "demo"}, sort_keys=True
        ),
    )
    db.add(row)
    db.flush()
    db.add(
        ConversationMessage(
            id=new_id("msg"),
            tenant_id=tenant_id,
            conversation_id=row.id,
            role="user",
            content="Tolong siapkan laporan mingguan untuk finance.",
        )
    )
    audit_repo.append_event(
        db,
        event_type="demo_seeded",
        actor=_actor(caller),
        scope=caller.scope,
        action="seed_demo_data",
        resource=row.id,
        decision="allow",
        tenant_id=tenant_id,
        detail={"conversation_id": row.id, "plan_id": SEED_PLAN_ID},
    )
    db.commit()
    return {
        "conversation_id": row.id,
        "plan_id": SEED_PLAN_ID,
        "intent": SEED_INTENT,
        "created": True,
    }


@router.post("/data/reset")
def reset_demo(
    payload: ResetRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    """Reset berguard: hanya conversation demo, konfirmasi = slug tenant.

    Scope lain (all/tenant/governance) ditolak 422 — endpoint ini tidak
    pernah menghapus audit, approval, mandate, execution, membership,
    atau tenant.
    """
    tenant_id = require_tenant(caller)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan.")
    if payload.scope != "conversations":
        raise HTTPException(
            status_code=422,
            detail="Scope reset tidak didukung. Hanya 'conversations' yang boleh di-reset.",
        )
    if payload.confirm != tenant.slug:
        raise HTTPException(
            status_code=422,
            detail="Konfirmasi reset harus sama dengan slug tenant.",
        )
    conv_ids = list(
        db.scalars(select(Conversation.id).where(Conversation.tenant_id == tenant_id)).all()
    )
    deleted_messages = db.execute(
        delete(ConversationMessage).where(ConversationMessage.tenant_id == tenant_id)
    ).rowcount
    deleted_conversations = db.execute(
        delete(Conversation).where(Conversation.tenant_id == tenant_id)
    ).rowcount
    audit_repo.append_event(
        db,
        event_type="data_reset",
        actor=_actor(caller),
        scope=caller.scope,
        action="reset_conversations",
        resource=tenant_id,
        decision="allow",
        tenant_id=tenant_id,
        detail={
            "scope": "conversations",
            "deleted_conversations": deleted_conversations,
            "deleted_messages": deleted_messages,
            "conversation_ids": conv_ids,
        },
    )
    db.commit()
    return {
        "tenant_id": tenant_id,
        "scope": "conversations",
        "deleted_conversations": deleted_conversations or 0,
        "deleted_messages": deleted_messages or 0,
    }
