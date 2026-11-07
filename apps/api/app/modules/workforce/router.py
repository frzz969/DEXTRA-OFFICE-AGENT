"""Workforce: registri agen. Hanya empat spesialis yang benar-benar ditetapkan.

Setiap operasi tulis memakai `tenant_id` dari identitas pemanggil — tidak pernah
dari body. Agen tenant lain tidak bisa disentuh: pencarian selalu melewati
`scope_to_tenant`, sehingga hasilnya `None` dan berakhir 404 (bukan 403, yang
akan mengonfirmasi keberadaan agen itu).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...models.tasks import Task
from ...models.workforce import Agent, AgentAssignment

router = APIRouter(tags=["workforce"])

#: §8.4 — menambah slug di sini berarti menambah agen yang harus ada implementasinya.
SPECIALISTS = (
    "workforce-dispatcher",
    "executive-assistant",
    "administrative-officer",
    "adversarial-reviewer",
)

#: Status yang dikenal model. Nilai lain ditolak, bukan disimpan apa adanya:
#: status asing membuat filter UI diam-diam kosong.
AGENT_STATUSES = ("active", "idle", "busy", "disabled", "error")


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    status: str = "idle"

class AgentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = None
    is_enabled: bool | None = None
    model_provider: str | None = Field(default=None, min_length=1, max_length=64)


def _serialize(agent: Agent) -> dict:
    return {
        "id": agent.id,
        "slug": agent.slug,
        "display_name": agent.display_name,
        "agent_type": agent.agent_type,
        "description": agent.description,
        "model_provider": agent.model_provider,
        "status": agent.status,
        "is_enabled": agent.is_enabled,
        "capabilities": sorted(c.capability for c in agent.capabilities),
        "versions": len(agent.versions),
    }


def _resolve(db: Session, slug: str, caller: CallerContext) -> Agent:
    """Ambil agen milik tenant pemanggil.

    Pemanggil tanpa tenant mendapat `false()` dari `scope_to_tenant`, jadi hasilnya
    selalu `None` — bukan agen pertama yang kebetulan cocok.
    """
    agent = db.scalar(scope_to_tenant(select(Agent).where(Agent.slug == slug), Agent, caller))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agen tidak ditemukan.")
    return agent


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)) -> dict:
    #: Tenantless caller mendapat query false() dari scope_to_tenant — kosong,
    #: bukan semua agent. Slug yang sama boleh ada di dua tenant (komposit).
    statement = scope_to_tenant(select(Agent), Agent, caller)
    agents = db.scalars(statement.order_by(Agent.slug)).all()
    return {
        "items": [_serialize(a) for a in agents],
        "expected_specialists": list(SPECIALISTS),
        #: Agen di luar empat spesialis dilaporkan, bukan disembunyikan.
        "unexpected": [a.slug for a in agents if a.slug not in SPECIALISTS],
    }


@router.get("/agents/{slug}")
def get_agent(
    slug: str, db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    return _serialize(_resolve(db, slug, caller))


@router.patch("/agents/{slug}")
def update_agent(
    slug: str,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    #: Tenant eksplisit: endpoint tulis tidak masuk akal tanpa identitas ber-tenant.
    require_tenant(caller)
    agent = _resolve(db, slug, caller)

    if payload.status is not None and payload.status not in AGENT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status agen tidak dikenal. Pilihan: {', '.join(AGENT_STATUSES)}.",
        )

    for name in ("display_name", "description", "status", "is_enabled", "model_provider"):
        value = getattr(payload, name)
        if value is not None:
            setattr(agent, name, value)

    db.commit()
    db.refresh(agent)
    return _serialize(agent)


@router.delete("/agents/{slug}")
def delete_agent(
    slug: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    require_tenant(caller)
    agent = _resolve(db, slug, caller)
    agent_id = agent.id

    #: Bersihkan rujukan sebelum agen dihapus. Di PostgreSQL FK menangani ini,
    #: tetapi SQLite tidak menegakkan FK secara default — tanpa langkah ini
    #: penugasan dan `assigned_agent_id` menjadi yatim di salah satu dialek.
    for assignment in db.scalars(
        select(AgentAssignment).where(AgentAssignment.agent_id == agent_id)
    ).all():
        db.delete(assignment)
    for task in db.scalars(select(Task).where(Task.assigned_agent_id == agent_id)).all():
        task.assigned_agent_id = None

    db.delete(agent)
    db.commit()
    return {"deleted": True, "slug": slug, "id": agent_id}


def _resolve_by_id(db, agent_id, caller):
    agent = db.scalar(scope_to_tenant(select(Agent).where(Agent.id == agent_id), Agent, caller))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agen tidak ditemukan.")
    return agent


@router.post("/agents", status_code=201)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    tenant_id = require_tenant(caller)
    if payload.status not in AGENT_STATUSES:
        raise HTTPException(status_code=422, detail="Status agen tidak dikenal.")
    slug = payload.name.lower().replace(" ", "-")
    agent = Agent(
        id=new_id("agt"),
        tenant_id=tenant_id,
        slug=slug,
        display_name=payload.name,
        agent_type=payload.role,
        status=payload.status,
    )
    db.add(agent)
    db.flush()
    for cap in payload.capabilities:
        db.add(AgentCapability(id=new_id("cap"), agent_id=agent.id, capability=cap))
    db.commit()
    db.refresh(agent)
    return _serialize(agent)


@router.patch("/agents/{agent_id}")
def update_agent_by_id(
    agent_id: str,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    agent = _resolve_by_id(db, agent_id, caller)
    if payload.status is not None and payload.status not in AGENT_STATUSES:
        raise HTTPException(status_code=422, detail="Status agen tidak dikenal.")
    for name in ("display_name", "description", "status", "is_enabled", "model_provider"):
        value = getattr(payload, name)
        if value is not None:
            setattr(agent, name, value)
    db.commit()
    db.refresh(agent)
    return _serialize(agent)
