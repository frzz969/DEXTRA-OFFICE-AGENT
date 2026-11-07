"""Work package, task, dan penugasan agen.

Aturan yang berlaku untuk seluruh operasi tulis di modul ini:

- `tenant_id` selalu berasal dari identitas pemanggil (`require_tenant`), tidak
  pernah dari body permintaan.
- Setiap resource dicari lewat `scope_to_tenant`, jadi resource tenant lain
  berakhir 404 — bukan 403, yang akan mengonfirmasi keberadaannya.
- Relasi yang menyeberang tenant (work package induk, agen yang ditugaskan)
  ditolak dengan 404 sebelum baris apa pun ditulis.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.base import new_id
from ...database.session import get_db
from ...models.tasks import WORK_STATUSES, Task, WorkPackage
from ...models.workforce import Agent, AgentAssignment

router = APIRouter(tags=["tasks"])

PRIORITIES = ("low", "normal", "high", "urgent")


class TaskCreate(BaseModel):
    work_package_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = ""


class WorkPackageUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    status: str | None = None
    sort_order: int | None = Field(default=None, ge=0)


class TransitionRequest(BaseModel):
    to_status: str

class AssignmentCreate(BaseModel):
    agent_slug: str = Field(min_length=1, max_length=64)
    role: str = Field(default="executor", min_length=1, max_length=64)


def _resolve_package(db: Session, package_id: str, caller: CallerContext) -> WorkPackage:
    package = db.scalar(
        scope_to_tenant(select(WorkPackage).where(WorkPackage.id == package_id), WorkPackage, caller)
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Work package tidak ditemukan.")
    return package


def _resolve_task(db: Session, task_id: str, caller: CallerContext) -> Task:
    task = db.scalar(scope_to_tenant(select(Task).where(Task.id == task_id), Task, caller))
    if task is None:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan.")
    return task


def _serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "work_package_id": task.work_package_id,
        "title": task.title,
        "status": task.status,
        "assigned_agent_id": task.assigned_agent_id,
    }


def _drop_assignments(db: Session, task_ids: list[str]) -> None:
    """Hapus penugasan milik task yang akan ikut terhapus.

    Foreign key `ON DELETE CASCADE` menanganinya di PostgreSQL, tetapi SQLite
    tidak menegakkan FK secara default. Menghapusnya eksplisit membuat kedua
    dialek berperilaku sama, bukan bergantung pada pengaturan server.
    """
    if not task_ids:
        return
    rows = db.scalars(
        select(AgentAssignment).where(AgentAssignment.task_id.in_(task_ids))
    ).all()
    for row in rows:
        db.delete(row)


def _task_id(db: Session, package: WorkPackage) -> str:
    """ID deterministik, tetapi tidak menabrak baris yang sudah ada.

    Penghapusan task membuat `len(tasks) + 1` bisa menunjuk ID yang masih hidup,
    jadi kandidat diperiksa dulu.
    """
    candidate = f"tsk_{len(package.tasks) + 1:04d}_{package.id[-6:]}"
    if db.get(Task, candidate) is None:
        return candidate
    return new_id("tsk")


@router.get("/work-packages")
def list_work_packages(
    db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    rows = db.scalars(
        scope_to_tenant(select(WorkPackage), WorkPackage, caller).order_by(WorkPackage.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": wp.id,
                "title": wp.title,
                "status": wp.status,
                "priority": wp.priority,
                "task_count": len(wp.tasks),
                "due_at": wp.due_at.isoformat() if wp.due_at else None,
            }
            for wp in rows
        ]
    }


@router.get("/work-packages/{package_id}")
def get_work_package(
    package_id: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    package = _resolve_package(db, package_id, caller)
    return {
        "id": package.id,
        "title": package.title,
        "status": package.status,
        "priority": package.priority,
        "org_id": package.org_id,
        "tenant_id": package.tenant_id,
        "due_at": package.due_at.isoformat() if package.due_at else None,
        "created_at": package.created_at.isoformat() if package.created_at else None,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "assigned_agent_id": task.assigned_agent_id,
                "sort_order": task.sort_order,
            }
            for task in package.tasks
        ],
    }


@router.patch("/work-packages/{package_id}")
def update_work_package(
    package_id: str,
    payload: WorkPackageUpdate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    package = _resolve_package(db, package_id, caller)

    if payload.status is not None and payload.status not in WORK_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status work package tidak dikenal. Pilihan: {', '.join(WORK_STATUSES)}.",
        )
    if payload.priority is not None and payload.priority not in PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Prioritas tidak dikenal. Pilihan: {', '.join(PRIORITIES)}.",
        )

    for name in ("title", "status", "priority", "due_at"):
        value = getattr(payload, name)
        if value is not None:
            setattr(package, name, value)

    db.commit()
    return {
        "id": package.id,
        "title": package.title,
        "status": package.status,
        "priority": package.priority,
    }


@router.delete("/work-packages/{package_id}")
def delete_work_package(
    package_id: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    package = _resolve_package(db, package_id, caller)
    _drop_assignments(db, [task.id for task in package.tasks])
    db.delete(package)
    db.commit()
    return {"deleted": True, "id": package_id}


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)) -> dict:
    rows = db.scalars(
        scope_to_tenant(select(Task), Task, caller).order_by(Task.sort_order, Task.created_at)
    ).all()
    return {"items": [_serialize_task(t) for t in rows]}


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    tenant_id = require_tenant(caller)
    #: Relasi lintas tenant ditolak 404 (bukan 403) agar keberadaan package
    #: tenant lain tidak terkonfirmasi. tenant_id selalu dari caller.
    package = _resolve_package(db, payload.work_package_id, caller)
    task = Task(
        id=_task_id(db, package),
        work_package_id=package.id,
        title=payload.title,
        description=payload.description,
        tenant_id=tenant_id,
    )
    db.add(task)
    db.commit()
    return {"id": task.id, "status": task.status}


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    task = _resolve_task(db, task_id, caller)

    if payload.status is not None and payload.status not in WORK_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status task tidak dikenal. Pilihan: {', '.join(WORK_STATUSES)}.",
        )

    for name in ("title", "description", "status", "sort_order"):
        value = getattr(payload, name)
        if value is not None:
            setattr(task, name, value)

    db.commit()
    return _serialize_task(task)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    task = _resolve_task(db, task_id, caller)
    _drop_assignments(db, [task.id])
    db.delete(task)
    db.commit()
    return {"deleted": True, "id": task_id}


@router.get("/tasks/{task_id}/assignments")
def list_assignments(
    task_id: str, db: Session = Depends(get_db), caller: CallerContext = Depends(get_caller)
) -> dict:
    task = _resolve_task(db, task_id, caller)
    rows = db.scalars(
        select(AgentAssignment).where(AgentAssignment.task_id == task.id).order_by(AgentAssignment.id)
    ).all()
    return {
        "items": [
            {"id": row.id, "task_id": row.task_id, "agent_id": row.agent_id, "role": row.role}
            for row in rows
        ]
    }


@router.post("/tasks/{task_id}/assignments", status_code=201)
def assign_agent(
    task_id: str,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    """Tugaskan agen ke task. Keduanya harus milik tenant pemanggil.

    Idempoten: menugaskan agen yang sama dengan peran yang sama mengembalikan
    baris yang sudah ada, bukan menggandakannya.
    """
    tenant_id = require_tenant(caller)
    task = _resolve_task(db, task_id, caller)
    agent = db.scalar(
        scope_to_tenant(select(Agent).where(Agent.slug == payload.agent_slug), Agent, caller)
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agen tidak ditemukan.")

    existing = db.scalar(
        select(AgentAssignment).where(
            AgentAssignment.task_id == task.id,
            AgentAssignment.agent_id == agent.id,
            AgentAssignment.role == payload.role,
        )
    )
    if existing is not None:
        return {
            "id": existing.id,
            "task_id": existing.task_id,
            "agent_id": existing.agent_id,
            "role": existing.role,
            "created": False,
        }

    assignment = AgentAssignment(
        id=new_id("asg"),
        task_id=task.id,
        agent_id=agent.id,
        role=payload.role,
        #: Dari caller, bukan dari body — dan hanya setelah agen & task lolos
        #: pemeriksaan tenant di atas.
        tenant_id=tenant_id,
    )
    db.add(assignment)
    task.assigned_agent_id = agent.id
    try:
        db.commit()
    except IntegrityError:
        # Permintaan lain menang balapan dan sudah menulis baris yang sama.
        # Itu hasil yang diinginkan, bukan kegagalan: kembalikan baris itu.
        db.rollback()
        existing = db.scalar(
            select(AgentAssignment).where(
                AgentAssignment.task_id == task.id,
                AgentAssignment.agent_id == agent.id,
                AgentAssignment.role == payload.role,
            )
        )
        if existing is None:
            raise
        return {
            "id": existing.id,
            "task_id": existing.task_id,
            "agent_id": existing.agent_id,
            "role": existing.role,
            "created": False,
        }
    return {
        "id": assignment.id,
        "task_id": assignment.task_id,
        "agent_id": assignment.agent_id,
        "role": assignment.role,
        "created": True,
    }


@router.delete("/tasks/{task_id}/assignments/{assignment_id}")
def unassign_agent(
    task_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    task = _resolve_task(db, task_id, caller)
    assignment = db.scalar(
        scope_to_tenant(
            select(AgentAssignment).where(
                AgentAssignment.id == assignment_id, AgentAssignment.task_id == task.id
            ),
            AgentAssignment,
            caller,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Penugasan tidak ditemukan.")

    if task.assigned_agent_id == assignment.agent_id:
        task.assigned_agent_id = None
    db.delete(assignment)
    db.commit()
    return {"deleted": True, "id": assignment_id}


_ALLOWED_TRANSITIONS = {
    "draft": {"assigned", "cancelled", "rejected"},
    "assigned": {"in_progress", "cancelled", "rejected"},
    "in_progress": {"review", "cancelled", "rejected"},
    "review": {"completed", "cancelled", "rejected"},
}


@router.post("/tasks/{task_id}/transition")
def transition_task(
    task_id: str,
    payload: TransitionRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    require_tenant(caller)
    task = _resolve_task(db, task_id, caller)
    if payload.to_status not in WORK_STATUSES:
        raise HTTPException(status_code=422, detail="Status tidak dikenal.")
    allowed = _ALLOWED_TRANSITIONS.get(task.status, set()) | {"cancelled", "rejected"}
    if payload.to_status not in allowed:
        raise HTTPException(status_code=422, detail="Transisi tidak diizinkan.")
    task.status = payload.to_status
    db.commit()
    return _serialize_task(task)
