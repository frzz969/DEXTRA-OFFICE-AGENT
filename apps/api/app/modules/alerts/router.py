"""Feed plans untuk alerts scan (DetectInput.plans dari DB nyata).

GET /alerts/plans: work request dari conversation milik tenant
pemanggil, bentuk persis ConversationPlanFact detect.ts. Scan produksi
(packages/alerts) bisa mengisi `plans` dari sini sehingga
`conversation_work_request` fire tanpa `ScanOptions.detect` manual.
Tenant-scoped, capability view_own.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.authz import require_tenant
from ...core.security import CallerContext, require_capability
from ...database.session import get_db
from ...repositories.plans import list_conversation_work_requests

router = APIRouter(tags=["alerts"])


@router.get("/alerts/plans")
def alerts_plans(
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    return {"items": list_conversation_work_requests(db, tenant_id), "tenant_id": tenant_id}
