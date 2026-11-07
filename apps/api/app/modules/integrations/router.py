"""Status konektor integrasi, dari config nyata — bukan badge palsu.

Sumber kebenaran per kanal (bukan klaim UI):
- telegram: env TELEGRAM_BOT_TOKEN ada/tidak. Tidak ada adapter di backend
  :8000 (bot terpisah apps/telegram-adapter), jadi adapter=None.
- whatsapp: tidak ada adapter & tidak ada endpoint -> configured False.
- email / calendar: adapter lokal "outbox" terdaftar di execution/service.py
  (_adapter_email / _adapter_calendar menulis .eml/.ics ke data/outbox).
- documents: tidak ada konektor/adapter -> configured False.

Nilai secret TIDAK pernah dikembalikan; hanya boolean keberadaan env.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from ...core.security import CallerContext, get_caller

router = APIRouter(tags=["integrations"])

# Adapter yang benar-benar terdaftar di backend (execution/service.py).
_REGISTERED_ADAPTERS = {"email": "outbox", "calendar": "outbox"}


def _item(name: str, *, configured: bool, adapter: str | None, detail: str, evidence: str) -> dict:
    return {
        "name": name,
        "configured": configured,
        "status": "configured" if configured else "not_configured",
        "adapter": adapter,
        "detail": detail,
        "evidence": evidence,
    }


@router.get("/integrations/status")
def integrations_status(caller: CallerContext = Depends(get_caller)) -> dict:
    """Status konektor tanpa data tenant. Butuh autentikasi seperti endpoint lain."""
    telegram_configured = bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())
    items = [
        _item(
            "telegram",
            configured=telegram_configured,
            adapter=None,
            detail="Bot terpisah lewat TELEGRAM_BOT_TOKEN (apps/telegram-adapter); bukan adapter di :8000.",
            evidence="env TELEGRAM_BOT_TOKEN ada/tidak",
        ),
        _item(
            "whatsapp",
            configured=False,
            adapter=None,
            detail="Belum diimplementasikan: tidak ada adapter dan tidak ada endpoint.",
            evidence="tidak ada adapter terdaftar",
        ),
        _item(
            "email",
            configured=True,
            adapter=_REGISTERED_ADAPTERS["email"],
            detail="Adapter lokal menulis file .eml ke data/outbox lewat execution service. Tidak ada server email eksternal.",
            evidence="adapter outbox terdaftar (execution/service.py)",
        ),
        _item(
            "calendar",
            configured=True,
            adapter=_REGISTERED_ADAPTERS["calendar"],
            detail="Adapter lokal menulis file .ics ke data/outbox lewat execution service.",
            evidence="adapter outbox terdaftar (execution/service.py)",
        ),
        _item(
            "documents",
            configured=False,
            adapter=None,
            detail="Tidak ada konektor dokumen: tidak ada endpoint upload/sinkronisasi dokumen.",
            evidence="tidak ada adapter terdaftar",
        ),
    ]
    return {"items": items, "tenant_id": caller.tenant_id}
