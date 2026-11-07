"""Agregasi harian eksekusi untuk chart (7 hari terakhir, UTC).

Dihitung dari started_at nyata yang tersimpan, tenant pemanggil saja.
Baris tanpa started_at tidak dihitung ke hari mana pun.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, get_caller
from ...database.session import get_db
from ...models.execution import Execution

router = APIRouter(tags=["analytics"])

_STATUSES = ("succeeded", "failed", "blocked", "pending", "running", "skipped")


@router.get("/analytics/daily")
def analytics_daily(db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)) -> dict:
    tenant_id = require_tenant(caller)
    now = datetime.now(timezone.utc)
    today = now.date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    buckets = {d.isoformat(): {"date": d.isoformat(), "total": 0, **{s: 0 for s in _STATUSES}} for d in days}
    start = datetime(days[0].year, days[0].month, days[0].day, tzinfo=timezone.utc)
    rows = db.scalars(
        scope_to_tenant(
            select(Execution).where(Execution.started_at >= start, Execution.started_at.is_not(None)),
            Execution,
            caller,
        )
    ).all()
    for row in rows:
        moment = row.started_at
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        key = moment.date().isoformat()
        bucket = buckets.get(key)
        if bucket is None:
            continue
        bucket["total"] += 1
        if row.status in _STATUSES:
            bucket[row.status] += 1
    return {"tenant_id": tenant_id, "items": [buckets[d.isoformat()] for d in days]}
