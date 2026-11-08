"""Eksekusi terkontrol.

Urutan yang tidak boleh dibalik:
1. validasi mandate (ulang, tepat sebelum aksi),
2. cek idempotensi di database,
3. jalankan aksi,
4. catat hasil + audit.
"""
from __future__ import annotations

import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.config import data_dir
from ...governance import mandate as mandate_service
from ...governance.mandate import MandateError
from ...models.execution import ActionRecord, Execution, ExecutionStep
from ...models.governance import Mandate
from ...repositories import audit as audit_repo


class ExecutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ADAPTER_NAME = "outbox"

def _outbox_dir() -> Path:
    return data_dir() / "outbox"


def _ensure_outbox() -> Path:
    path = _outbox_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _adapter_email(params: dict) -> tuple[str, Path]:
    msg = EmailMessage()
    msg["From"] = params.get("from", "noreply@dextra.local")
    msg["To"] = params.get("to", "")
    msg["Subject"] = params.get("subject", "")
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    msg.set_content(params.get("body", ""))
    rid = uuid.uuid4().hex
    path = _ensure_outbox() / f"{rid}.eml"
    path.write_bytes(msg.as_bytes())
    return rid, path


def _adapter_calendar(params: dict) -> tuple[str, Path]:
    rid = uuid.uuid4().hex
    start = params.get("start", "")
    end = params.get("end", "")
    title = params.get("title", "")
    content = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//dextra//outbox//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{rid}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DTSTART:{start}\r\n"
        f"DTEND:{end}\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    path = _ensure_outbox() / f"{rid}.ics"
    path.write_text(content, encoding="utf-8")
    return rid, path


def _adapter_task(params: dict) -> tuple[str, Path]:
    rid = uuid.uuid4().hex
    payload = {"id": rid, **{k: v for k, v in params.items()}}
    path = _ensure_outbox() / f"{rid}.task.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return rid, path


#: Peta tipe aksi ke adapter. Tipe lama (email/calendar/task) tetap didukung
#: agar mandate lama tidak rusak; tipe nyata dari Office Agent dipetakan.
_ACTION_ADAPTERS = {
    "send_email": "email",
    "email": "email",
    "create_calendar_event": "calendar",
    "calendar": "calendar",
    "create_task": "task",
    "task": "task",
}


def _dispatch(action_type: str, params: dict) -> tuple[str, Path]:
    adapter = _ACTION_ADAPTERS.get((action_type or "").lower())
    if adapter == "email":
        return _adapter_email(params)
    if adapter == "calendar":
        return _adapter_calendar(params)
    if adapter == "task":
        return _adapter_task(params)
    raise ExecutionError(
        "UNSUPPORTED_ACTION_TYPE",
        f"Tipe aksi tidak didukung: {action_type!r}.",
    )


def execute(
    db: Session,
    *,
    mandate_id: str,
    action_id: str,
    action_type: str,
    params: dict,
    actor: str = "executor",
    correlation_id: str = "",
    tenant_id: str | None = None,
) -> Execution:
    params_digest = mandate_service.params_digest(params)
    key = f"{mandate_id}:{action_id}:{params_digest}"
    existing = db.scalar(select(Execution).where(Execution.idempotency_key == key))
    if existing is not None:
        if tenant_id is not None and existing.tenant_id != tenant_id:
            raise ExecutionError("MANDATE_NOT_FOUND", "Mandate tidak ditemukan.")
        return existing

    if tenant_id is not None:
        owned = db.get(Mandate, mandate_id)
        if owned is None or owned.tenant_id != tenant_id:
            raise ExecutionError("MANDATE_NOT_FOUND", "Mandate tidak ditemukan.")

    # explicit mandate tenant mismatch check
    if tenant_id is not None:
        m = db.get(Mandate, mandate_id)
        if m is not None and m.tenant_id != tenant_id:
            audit_repo.append_event(
                db, event_type="action_blocked", actor=actor, scope="ops",
                action=action_type, resource=mandate_id, decision="deny",
                mandate_id=mandate_id, tenant_id=tenant_id, correlation_id=correlation_id,
                detail={"code": "MANDATE_TENANT_MISMATCH", "message": "tenant mismatch"},
            )
            db.commit()
            raise ExecutionError("MANDATE_TENANT_MISMATCH", "Mandate tenant mismatch.")

    try:
        mandate = mandate_service.validate_for_execution(
            db, mandate_id=mandate_id, action_id=action_id, params=params,
            action_type=action_type,
        )
    except MandateError as exc:
        audit_repo.append_event(
            db, event_type="action_blocked", actor=actor, scope="ops",
            action=action_type, resource=mandate_id, decision="deny",
            mandate_id=mandate_id, tenant_id=tenant_id, correlation_id=correlation_id,
            detail={"code": exc.code, "message": exc.message},
        )
        db.commit()
        raise ExecutionError(exc.code, exc.message) from exc

    started = datetime.now(timezone.utc)
    execution = Execution(
        id=f"exe_{int(time.time() * 1000)}_{secrets.token_hex(3)}",
        plan_id=mandate.plan_id,
        mandate_id=mandate.id,
        tenant_id=tenant_id if tenant_id is not None else mandate.tenant_id,
        action_id=action_id,
        agent_id=mandate.agent_id,
        adapter=ADAPTER_NAME,
        status="running",
        idempotency_key=key,
        params_digest=params_digest,
        started_at=started,
        correlation_id=correlation_id,
    )
    db.add(execution)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        again = db.scalar(select(Execution).where(Execution.idempotency_key == key))
        if again is None:
            raise
        return again

    mandate.consumed_by_execution_id = execution.id
    db.flush()

    db.add(ExecutionStep(
        id=f"stp_{execution.id}_1", execution_id=execution.id, seq=1,
        name="mandate_validated", status="succeeded", detail=f"nonce={mandate.nonce}",
    ))

    # retry dispatch
    delays = [0.05, 0.1, 0.2]
    result_id = None
    path = None
    last_exc = None
    for attempt in range(3):
        try:
            result_id, path = _dispatch(action_type, params)
            last_exc = None
            break
        except Exception as exc:  # noqa
            last_exc = exc
            if attempt < 2:
                time.sleep(delays[attempt])
    if last_exc is not None:
        finished = datetime.now(timezone.utc)
        execution.status = "failed"
        execution.finished_at = finished
        execution.duration_ms = int((finished - started).total_seconds() * 1000)
        db.add(ExecutionStep(
            id=f"stp_{execution.id}_2", execution_id=execution.id, seq=2,
            name="action_executed", status="failed", detail=str(last_exc),
        ))
        audit_repo.append_event(
            db, event_type="action_blocked", actor=actor, scope="ops",
            action=action_type, resource=mandate_id, decision="deny",
            plan_id=mandate.plan_id, mandate_id=mandate.id, execution_id=execution.id,
            tenant_id=tenant_id or mandate.tenant_id, correlation_id=correlation_id,
            detail={"code": "EXECUTOR_FAILURE", "message": str(last_exc)},
        )
        db.commit()
        raise ExecutionError("EXECUTOR_FAILURE", str(last_exc))

    result = {
        "adapter": ADAPTER_NAME,
        "provider": "outbox",
        "result_id": result_id,
        "path": str(path),
        "action_type": action_type,
    }
    finished = datetime.now(timezone.utc)
    execution.status = "succeeded"
    execution.finished_at = finished
    execution.duration_ms = int((finished - started).total_seconds() * 1000)
    execution.result_json = json.dumps(result, sort_keys=True)
    mandate.status = "executing"

    db.add(ActionRecord(
        id=f"act_{execution.id}", execution_id=execution.id,
        action_type=action_type, params_json=json.dumps(params, sort_keys=True),
        params_hash=mandate.params_hash,
    ))
    db.add(ExecutionStep(
        id=f"stp_{execution.id}_2", execution_id=execution.id, seq=2,
        name="action_executed", status="succeeded",
        detail=f"result_id={result_id}",
    ))

    audit_repo.append_event(
        db, event_type="action_executed", actor=actor, scope="ops",
        action=action_type, resource=mandate_id, decision="allow",
        plan_id=mandate.plan_id, mandate_id=mandate.id, execution_id=execution.id,
        tenant_id=tenant_id or mandate.tenant_id, correlation_id=correlation_id,
        detail={"adapter": ADAPTER_NAME, "provider": "outbox", "result_id": result_id,
                "duration_ms": execution.duration_ms},
    )
    db.commit()
    return execution