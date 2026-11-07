"""Modul percakapan: sistem pencatat percakapan dan pesan.

Percakapan adalah milik tenant, bukan milik klien. `tenant_id` selalu berasal
dari identitas pemanggil, tidak pernah dari body. Resource tenant lain menjawab
404 (bukan 403) supaya keberadaannya tidak terkonfirmasi.

Tidak ada kolom atau parameter yang menyamar sebagai sesi login: `sessions`
tetap berarti sesi autentikasi.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ...core.authz import assert_tenant_access, require_tenant, scope_to_tenant
from ...core.security import CallerContext, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...models.conversation import Conversation, ConversationMessage
from ...repositories import audit as audit_repo

router = APIRouter(tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    agent_id: str | None = Field(default=None, max_length=64)
    metadata: dict = Field(default_factory=dict)


class CreateMessageRequest(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|tool)$")
    content: str = Field(min_length=1, max_length=100_000)
    metadata: dict = Field(default_factory=dict)


def _serialize_conversation(row: Conversation) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "agent_id": row.agent_id,
        "created_by_user_id": row.created_by_user_id,
        "metadata": json.loads(row.metadata_json or "{}"),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _serialize_message(row: ConversationMessage) -> dict:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "role": row.role,
        "content": row.content,
        "metadata": json.loads(row.metadata_json or "{}"),
        "created_at": row.created_at.isoformat(),
    }


def _get_own_conversation(
    db: DbSession, conversation_id: str, caller: CallerContext
) -> Conversation:
    row = db.scalar(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    assert_tenant_access(caller, row.tenant_id, resource="Percakapan")
    return row


@router.post("/conversations", status_code=201)
def create_conversation(
    payload: CreateConversationRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    tenant_id = require_tenant(caller)
    row = Conversation(
        id=new_id("cnv"),
        tenant_id=tenant_id,
        title=payload.title,
        status="active",
        created_by_user_id=caller.principal_id if caller.auth_kind == "session" else None,
        agent_id=payload.agent_id,
        metadata_json=json.dumps(payload.metadata, sort_keys=True),
    )
    db.add(row)
    audit_repo.append_event(
        db,
        event_type="conversation_created",
        actor="conversations",
        scope=caller.scope,
        action="create_conversation",
        resource=row.id,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={
            "conversation_id": row.id,
            "title_length": str(len(row.title)),
        },
    )
    db.commit()
    return _serialize_conversation(row)


@router.get("/conversations")
def list_conversations(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    statement = scope_to_tenant(select(Conversation), Conversation, caller)
    rows = db.scalars(
        statement.order_by(Conversation.created_at.desc()).limit(100)
    ).all()
    return {"items": [_serialize_conversation(row) for row in rows]}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    row = _get_own_conversation(db, conversation_id, caller)
    return _serialize_conversation(row)


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def append_message(
    conversation_id: str,
    payload: CreateMessageRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    tenant_id = require_tenant(caller)
    conversation = _get_own_conversation(db, conversation_id, caller)
    row = ConversationMessage(
        id=new_id("msg"),
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        role=payload.role,
        content=payload.content,
        metadata_json=json.dumps(payload.metadata, sort_keys=True),
    )
    db.add(row)
    audit_repo.append_event(
        db,
        event_type="conversation_message_appended",
        actor="conversations",
        scope=caller.scope,
        action="append_conversation_message",
        resource=conversation.id,
        decision="allow",
        tenant_id=caller.tenant_id,
        detail={
            "conversation_id": conversation.id,
            "message_id": row.id,
            "content_length": str(len(row.content)),
        },
    )
    db.commit()
    return _serialize_message(row)


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    conversation = _get_own_conversation(db, conversation_id, caller)
    rows = db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
        .limit(200)
    ).all()
    return {"items": [_serialize_message(row) for row in rows]}
