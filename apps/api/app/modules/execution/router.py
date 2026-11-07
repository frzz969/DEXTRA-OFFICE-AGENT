"""Eksekusi: daftar jejak dan pemicu eksekusi terkontrol."""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.authz import scope_to_tenant
from ...core.security import CallerContext, get_caller, require_capability
from ...database.session import get_db
from ...models.execution import Execution
from .service import ExecutionError, execute as run_execution

router = APIRouter(tags=["execution"])


class ExecuteRequest(BaseModel):
    mandate_id: str
    action_id: str
    action_type: str = Field(min_length=1, max_length=64)
    params: dict = Field(default_factory=dict)
    correlation_id: str = ""


@router.get("/executions")
def list_executions(
    limit: int = 50,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(get_caller),
) -> dict:
    statement = scope_to_tenant(select(Execution), Execution, caller)
    rows = db.scalars(
        statement.order_by(Execution.created_at.desc()).limit(min(limit, 200))
    ).all()
    return {
        "items": [
            {
                "id": e.id,
                "plan_id": e.plan_id,
                "mandate_id": e.mandate_id,
                "action_id": e.action_id,
                "status": e.status,
                "adapter": e.adapter,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "duration_ms": e.duration_ms,
                "result": e.result_json,
            }
            for e in rows
        ]
    }


@router.post("/executions", status_code=201)
def create_execution(
    payload: ExecuteRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("execute")),
) -> dict:
    try:
        execution = run_execution(
            db,
            mandate_id=payload.mandate_id,
            action_id=payload.action_id,
            action_type=payload.action_type,
            params=payload.params,
            correlation_id=payload.correlation_id,
            tenant_id=caller.tenant_id,
        )
    except ExecutionError as exc:
        # 409: permintaan sah tetapi ditolak aturan, bukan kesalahan klien.
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message}) from exc
    return {
        "id": execution.id,
        "status": execution.status,
        "duration_ms": execution.duration_ms,
        "result": execution.result_json,
    }
