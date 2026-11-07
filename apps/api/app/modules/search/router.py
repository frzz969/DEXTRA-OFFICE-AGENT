"""Pencarian lintas entitas untuk Explorer.

Semua entitas difilter tenant pemanggil (scope_to_tenant). q kosong -> 422
(FastAPI min_length). Hasil dibatasi per entitas agar tidak meledak.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, get_caller
from ...database.session import get_db
from ...models.execution import Execution
from ...models.governance import Mandate, Policy
from ...models.office import OfficePlanRequest
from ...models.registry import Skill
from ...models.tasks import Task, WorkPackage
from ...models.workforce import Agent

router = APIRouter(tags=["search"])

_PER_ENTITY = 20


def _like(column, q: str):
    return func.lower(column).contains(q.lower())


def _query(db: Session, caller, model, predicate, limit: int = _PER_ENTITY):
    stmt = scope_to_tenant(select(model).where(predicate(model)), model, caller).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    require_tenant(caller)
    items: list[dict] = []

    for wp in _query(db, caller, WorkPackage, lambda m: _like(m.title, q) | _like(m.id, q)):
        items.append({"entity": "work_package", "id": wp.id, "title": wp.title, "status": wp.status,
                      "href": f"/work-packages/{wp.id}"})
    for t in _query(db, caller, Task, lambda m: _like(m.title, q) | _like(m.description, q) | _like(m.id, q)):
        items.append({"entity": "task", "id": t.id, "title": t.title, "status": t.status,
                      "href": f"/work-packages/{t.work_package_id}"})
    for a in _query(db, caller, Agent, lambda m: _like(m.slug, q) | _like(m.display_name, q) | _like(m.id, q)):
        items.append({"entity": "agent", "id": a.id, "title": a.display_name, "status": a.status,
                      "href": f"/agents/{a.slug}"})
    for mnd in _query(db, caller, Mandate, lambda m: _like(m.id, q) | _like(m.plan_id, q) | _like(m.action_type, q)):
        items.append({"entity": "mandate", "id": mnd.id, "title": mnd.id, "status": mnd.status,
                      "href": f"/mandates/{mnd.id}"})
    for ex in _query(db, caller, Execution, lambda m: _like(m.id, q) | _like(m.mandate_id, q) | _like(m.action_id, q) | _like(m.plan_id, q)):
        items.append({"entity": "execution", "id": ex.id, "title": ex.id, "status": ex.status,
                      "href": "/executions"})
    for p in _query(db, caller, Policy, lambda m: _like(m.slug, q) | _like(m.title, q)):
        items.append({"entity": "policy", "id": p.id, "title": p.title, "status": "active" if p.is_active else "inactive",
                      "href": "/policies"})
    for s in _query(db, caller, Skill, lambda m: _like(m.slug, q) | _like(m.display_name, q)):
        items.append({"entity": "skill", "id": s.id, "title": s.display_name, "status": s.status,
                      "href": f"/skills/{s.slug}"})
    for plan in _query(db, caller, OfficePlanRequest, lambda m: _like(m.plan_id, q) | _like(m.request_id, q)):
        items.append({"entity": "plan", "id": plan.id, "title": plan.plan_id, "status": plan.status,
                      "href": f"/office-agent/{plan.plan_id}"})
    return {"q": q, "items": items, "count": len(items)}
