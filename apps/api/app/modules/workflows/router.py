"""API orkestrasi workflow.

Definisi disimpan per tenant. Run memakai `idempotency_key` unik: permintaan
ulang dengan kunci yang sama mengembalikan run yang sudah ada, bukan memulai
yang kedua.

Gerbang persetujuan tidak memakai mekanisme sendiri: yang menyetujui adalah
manusia dengan capability `approve`, dan jejaknya masuk ke audit chain.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ...core.authz import require_tenant, scope_to_tenant
from ...core.security import CallerContext, require_capability
from ...database.session import get_db
from ...models.registry import WorkflowDefinition, WorkflowRun, WorkflowStepRun
from ...workflow import engine

router = APIRouter(tags=["workflows"])


class StepModel(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: str = Field(default="noop")
    depends_on: list[str] = Field(default_factory=list)
    max_attempts: int = Field(default=1, ge=1, le=10)
    params: dict = Field(default_factory=dict)


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=2, max_length=96)
    description: str = Field(default="", max_length=2000)
    steps: list[StepModel] = Field(min_length=1, max_length=50)


class StartRunRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=160)
    inputs: dict = Field(default_factory=dict)


class ApproveGateRequest(BaseModel):
    note: str = Field(default="", max_length=500)


def _serialize_definition(row: WorkflowDefinition) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "description": row.description,
        "status": row.status,
        "steps": json.loads(row.steps_json or "[]"),
        "created_at": row.created_at.isoformat(),
    }


def _serialize_run(db: DbSession, run: WorkflowRun) -> dict:
    rows = db.scalars(
        select(WorkflowStepRun)
        .where(WorkflowStepRun.run_id == run.id)
        .order_by(WorkflowStepRun.created_at)
    ).all()
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "idempotency_key": run.idempotency_key,
        "state": json.loads(run.state_json or "{}"),
        "checkpoint_at": run.checkpoint_at.isoformat() if run.checkpoint_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
        "steps": [
            {
                "step_id": row.step_id,
                "status": row.status,
                "attempts": row.attempts,
                "error": row.error,
                "output": json.loads(row.output_json or "null"),
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "approved_by": row.approved_by_user_id,
            }
            for row in rows
        ],
    }


@router.get("/workflows")
def list_workflows(
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    statement = scope_to_tenant(select(WorkflowDefinition), WorkflowDefinition, caller)
    rows = db.scalars(statement.order_by(WorkflowDefinition.name)).all()
    return {"items": [_serialize_definition(row) for row in rows], "tenant_id": tenant_id}


@router.post("/workflows", status_code=201)
def create_workflow(
    payload: CreateWorkflowRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    steps = [step.model_dump() for step in payload.steps]
    try:
        parsed = engine.parse_steps(steps)
    except engine.WorkflowError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc
    errors = engine.validate_steps(parsed)
    if errors:
        raise HTTPException(
            status_code=422, detail={"code": "INVALID_DEFINITION", "message": "; ".join(errors)}
        )

    existing = db.scalar(
        select(WorkflowDefinition).where(
            WorkflowDefinition.tenant_id == tenant_id, WorkflowDefinition.name == payload.name
        )
    )
    version = 1 if existing is None else existing.version + 1
    row = WorkflowDefinition(
        id=f"wfd_{__import__('secrets').token_hex(8)}",
        tenant_id=tenant_id,
        name=payload.name,
        version=version,
        description=payload.description,
        steps_json=json.dumps(steps, sort_keys=True),
        status="draft",
        created_by_user_id=caller.principal_id,
    )
    db.add(row)
    db.commit()
    return _serialize_definition(row)


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(
    workflow_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_integrations")),
) -> dict:
    tenant_id = require_tenant(caller)
    row = db.get(WorkflowDefinition, workflow_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
    row.status = "active"
    db.commit()
    return _serialize_definition(row)


@router.post("/workflows/{workflow_id}/runs", status_code=201)
def start_run(
    workflow_id: str,
    payload: StartRunRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    tenant_id = require_tenant(caller)
    definition = db.get(WorkflowDefinition, workflow_id)
    if definition is None or definition.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
    try:
        run = engine.start_run(
            db,
            tenant_id=tenant_id,
            definition=definition,
            idempotency_key=payload.idempotency_key,
            created_by_user_id=caller.principal_id,
        )
        engine.advance(db, run, capabilities=caller.capabilities, actor=caller.email or "workflow")
    except engine.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc
    db.commit()
    return _serialize_run(db, run)


@router.get("/workflows/runs")
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    rows = db.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.tenant_id == tenant_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
    ).all()
    return {"items": [_serialize_run(db, row) for row in rows]}


@router.get("/workflows/runs/{run_id}")
def get_run(
    run_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("view_own")),
) -> dict:
    tenant_id = require_tenant(caller)
    run = db.get(WorkflowRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow run tidak ditemukan.")
    return _serialize_run(db, run)


@router.post("/workflows/runs/{run_id}/gates/{step_id}/approve")
def approve_gate(
    run_id: str,
    step_id: str,
    payload: ApproveGateRequest,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("approve")),
) -> dict:
    tenant_id = require_tenant(caller)
    run = db.get(WorkflowRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow run tidak ditemukan.")
    try:
        engine.approve_gate(
            db,
            run,
            step_id=step_id,
            user_id=caller.principal_id or "",
            capabilities=caller.capabilities,
            actor=caller.email or "workflow",
        )
        engine.advance(db, run, capabilities=caller.capabilities, actor=caller.email or "workflow")
    except engine.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc
    db.commit()
    return _serialize_run(db, run)


@router.post("/workflows/runs/{run_id}/resume")
def resume_run(
    run_id: str,
    db: DbSession = Depends(get_db),
    caller: CallerContext = Depends(require_capability("create_request")),
) -> dict:
    """Lanjutkan run dari checkpoint. Langkah yang sudah berhasil tidak diulang."""
    tenant_id = require_tenant(caller)
    run = db.get(WorkflowRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow run tidak ditemukan.")
    try:
        engine.advance(db, run, capabilities=caller.capabilities, actor=caller.email or "workflow")
    except engine.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc
    db.commit()
    return _serialize_run(db, run)
