"""Sumber plan nyata untuk alerts scan (DetectInput.plans).

`packages/alerts/src/detect.ts` mengharapkan `ConversationPlanFact[]`:
`{plan_id, intent, created_at}` untuk work request yang lahir dari
conversation. Backend tidak punya tabel Plan terpisah — rencana kerja
dari conversation dicatat di `conversations.metadata_json` sebagai
`{"intent": "...", "plan_id": "..."}`. Repository ini membaca fakta
tersebut dari DB nyata, tenant-scoped, supaya scan produksi bisa
memakai feed ini (bukan hanya `ScanOptions.detect` manual).

Conversation tanpa `intent` bukan work request dan tidak ikut.
`plan_id` dari metadata bila ada, jatuh ke id conversation.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.conversation import Conversation


def list_conversation_work_requests(db: Session, tenant_id: str) -> list[dict]:
    """Daftar work request dari conversation milik satu tenant.

    Mengembalikan dict persis berbentuk ConversationPlanFact detect.ts:
    hanya plan_id/intent/created_at. Urutan stabil: created_at naik, id naik.
    """
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
        .order_by(Conversation.created_at.asc(), Conversation.id.asc())
    ).all()
    facts: list[dict] = []
    for row in rows:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(metadata, dict):
            continue
        intent = metadata.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            continue
        plan_id = metadata.get("plan_id")
        facts.append(
            {
                "plan_id": plan_id if isinstance(plan_id, str) and plan_id else row.id,
                "intent": intent.strip(),
                "created_at": row.created_at.isoformat(),
            }
        )
    return facts
