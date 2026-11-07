"""Mesin orkestrasi workflow.

Kenapa tidak memakai LangGraph: paketnya tidak terpasang di lingkungan ini, dan
menambah dependency yang tidak bisa dijalankan berarti menulis kode yang tidak
bisa dibuktikan. Yang dibutuhkan dari orkestrasi di sini justru sempit dan sudah
punya pemilik di sistem ini:

- state dan checkpoint → tabel `workflow_runs` (state + checkpoint_json);
- gerbang persetujuan manusia → Approval/Mandate Engine yang sudah ada;
- eksekusi bertools → Execution Gateway yang sudah ada, bukan adapter baru;
- audit dan idempotensi → `audit_events` dan `idempotency_key` unik.

Mesin ini karena itu tipis: ia mengurutkan langkah, menyimpan titik pemulihan,
dan menyerahkan efek samping ke gateway. Kalau kelak LangGraph dipakai, ia harus
menggantikan lapisan pengurutan ini — bukan menambah lapisan kedua di atasnya.

Yang ditegakkan:

- definisi harus DAG: dependensi ada, tidak ada siklus, ada langkah akar;
- langkah `execute` wajib punya `mandate_id` dan lewat Execution Gateway;
- gerbang persetujuan menghentikan run sampai manusia menyetujui;
- kegagalan diulang sampai `max_attempts`, lalu run berstatus `failed`;
- setiap langkah menulis checkpoint, sehingga run bisa dilanjutkan setelah
  proses mati.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.registry import WorkflowDefinition, WorkflowRun, WorkflowStepRun
from ..repositories import audit as audit_repo

STEP_TYPES = ("noop", "approval_gate", "execute")


class WorkflowError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Step:
    id: str
    type: str
    depends_on: tuple[str, ...]
    max_attempts: int = 1
    params: dict | None = None


def parse_steps(raw: list[dict]) -> list[Step]:
    steps: list[Step] = []
    for item in raw:
        if not isinstance(item, dict):
            raise WorkflowError("INVALID_STEP", "Setiap langkah harus berupa objek.")
        step_id = item.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise WorkflowError("INVALID_STEP", "Langkah wajib punya id.")
        step_type = item.get("type", "noop")
        if step_type not in STEP_TYPES:
            raise WorkflowError("INVALID_STEP", f"Jenis langkah tidak dikenal: {step_type}")
        depends = item.get("depends_on", [])
        if not isinstance(depends, list) or not all(isinstance(d, str) for d in depends):
            raise WorkflowError("INVALID_STEP", f"depends_on langkah {step_id} harus daftar id.")
        attempts = item.get("max_attempts", 1)
        if not isinstance(attempts, int) or attempts < 1 or attempts > 10:
            raise WorkflowError("INVALID_STEP", "max_attempts harus 1..10.")
        steps.append(
            Step(
                id=step_id,
                type=step_type,
                depends_on=tuple(depends),
                max_attempts=attempts,
                params=item.get("params") or {},
            )
        )
    return steps


def validate_steps(steps: list[Step]) -> list[str]:
    errors: list[str] = []
    ids = {step.id for step in steps}
    if len(ids) != len(steps):
        errors.append("id langkah harus unik")
    for step in steps:
        for dependency in step.depends_on:
            if dependency not in ids:
                errors.append(f"{step.id}: dependensi tidak dikenal {dependency}")
            if dependency == step.id:
                errors.append(f"{step.id}: tidak boleh bergantung pada dirinya sendiri")
    if steps and not any(not step.depends_on for step in steps):
        errors.append("workflow tidak punya langkah akar")

    # Deteksi siklus dengan DFS tiga warna.
    graph = {step.id: list(step.depends_on) for step in steps}
    state: dict[str, int] = {}

    def visit(node: str) -> bool:
        state[node] = 1
        for neighbour in graph.get(node, []):
            if state.get(neighbour) == 1:
                return True
            if state.get(neighbour, 0) == 0 and visit(neighbour):
                return True
        state[node] = 2
        return False

    for node in graph:
        if state.get(node, 0) == 0 and visit(node):
            errors.append("workflow mengandung siklus")
            break
    return errors


def _load_steps(definition: WorkflowDefinition) -> list[Step]:
    return parse_steps(json.loads(definition.steps_json or "[]"))


def start_run(
    db: Session,
    *,
    tenant_id: str,
    definition: WorkflowDefinition,
    idempotency_key: str,
    created_by_user_id: str | None = None,
    now: datetime | None = None,
) -> WorkflowRun:
    existing = db.scalar(
        select(WorkflowRun).where(WorkflowRun.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.tenant_id != tenant_id:
            raise WorkflowError("RUN_NOT_FOUND", "Workflow run tidak ditemukan.")
        return existing

    if definition.status != "active":
        raise WorkflowError("WORKFLOW_NOT_ACTIVE", "Workflow belum aktif.")

    steps = _load_steps(definition)
    errors = validate_steps(steps)
    if errors:
        raise WorkflowError("INVALID_DEFINITION", "; ".join(errors))

    moment = now or datetime.now(timezone.utc)
    run = WorkflowRun(
        id=f"wfr_{__import__('secrets').token_hex(8)}",
        tenant_id=tenant_id,
        workflow_id=definition.id,
        status="running",
        idempotency_key=idempotency_key,
        state_json="{}",
        checkpoint_json="{}",
        started_at=moment,
        created_by_user_id=created_by_user_id,
    )
    db.add(run)
    db.flush()

    for step in steps:
        db.add(
            WorkflowStepRun(
                id=f"wsr_{run.id}_{step.id}"[:64],
                run_id=run.id,
                step_id=step.id,
                status="pending",
                attempts=0,
            )
        )
    db.flush()
    return run


def _step_rows(db: Session, run: WorkflowRun) -> dict[str, WorkflowStepRun]:
    rows = db.scalars(select(WorkflowStepRun).where(WorkflowStepRun.run_id == run.id)).all()
    return {row.step_id: row for row in rows}


def _checkpoint(db: Session, run: WorkflowRun, state: dict) -> None:
    run.state_json = json.dumps(state, sort_keys=True, default=str)
    run.checkpoint_json = run.state_json
    run.checkpoint_at = datetime.now(timezone.utc)
    db.flush()


def advance(
    db: Session,
    run: WorkflowRun,
    *,
    capabilities: tuple[str, ...],
    actor: str = "workflow",
) -> WorkflowRun:
    """Jalankan langkah yang siap sampai berhenti, gagal, atau selesai."""
    definition = db.get(WorkflowDefinition, run.workflow_id)
    if definition is None:
        raise WorkflowError("WORKFLOW_NOT_FOUND", "Definisi workflow hilang.")
    steps = _load_steps(definition)
    rows = _step_rows(db, run)
    state = json.loads(run.state_json or "{}")

    if run.status in ("succeeded", "failed", "cancelled"):
        return run

    for _ in range(len(steps) + 1):
        done = {sid for sid, row in rows.items() if row.status in ("succeeded", "skipped")}
        ready = [
            step
            for step in steps
            if step.id not in done and step.id in rows and rows[step.id].status == "pending"
            and all(dependency in done for dependency in step.depends_on)
        ]
        if not ready:
            break

        step = ready[0]
        row = rows[step.id]

        if step.type == "approval_gate":
            if row.status == "waiting_approval":
                run.status = "waiting_approval"
                db.flush()
                return run
            row.status = "waiting_approval"
            row.started_at = datetime.now(timezone.utc)
            run.status = "waiting_approval"
            _checkpoint(db, run, state)
            audit_repo.append_event(
                db,
                event_type="workflow_gate_waiting",
                actor=actor,
                scope="workflow",
                action="await_approval",
                resource=run.id,
                decision="review",
                tenant_id=run.tenant_id,
                detail={"step_id": step.id, "workflow": definition.name},
            )
            return run

        if step.type == "execute" and "execute" not in capabilities:
            row.status = "failed"
            row.error = "CAPABILITY_MISSING"
            run.status = "failed"
            run.error = f"Langkah {step.id} menuntut capability execute."
            run.finished_at = datetime.now(timezone.utc)
            db.flush()
            return run

        row.status = "running"
        row.attempts = int(row.attempts or 0) + 1
        row.started_at = datetime.now(timezone.utc)
        db.flush()

        try:
            output = _run_step(db, run, step, actor=actor)
        except Exception as exc:  # noqa: BLE001 - kegagalan langkah harus tercatat
            message = str(exc)
            if row.attempts >= step.max_attempts:
                row.status = "failed"
                row.error = message[:500]
                row.finished_at = datetime.now(timezone.utc)
                run.status = "failed"
                run.error = f"Langkah {step.id} gagal: {message}"[:500]
                run.finished_at = datetime.now(timezone.utc)
                _checkpoint(db, run, state)
                audit_repo.append_event(
                    db,
                    event_type="workflow_failed",
                    actor=actor,
                    scope="workflow",
                    action="step_failed",
                    resource=run.id,
                    decision="deny",
                    tenant_id=run.tenant_id,
                    detail={"step_id": step.id, "attempts": row.attempts, "error": message[:200]},
                )
                db.flush()
                return run
            # Sisa percobaan: kembalikan ke pending, putaran berikutnya mencoba lagi.
            row.status = "pending"
            row.error = message[:500]
            db.flush()
            continue

        row.status = "succeeded"
        row.output_json = json.dumps(output, sort_keys=True, default=str)
        row.finished_at = datetime.now(timezone.utc)
        state[step.id] = output
        _checkpoint(db, run, state)
        db.flush()

    pending = [row for row in rows.values() if row.status in ("pending", "running")]
    waiting = [row for row in rows.values() if row.status == "waiting_approval"]
    if waiting:
        run.status = "waiting_approval"
    elif not pending:
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        audit_repo.append_event(
            db,
            event_type="workflow_succeeded",
            actor=actor,
            scope="workflow",
            action="workflow_complete",
            resource=run.id,
            decision="allow",
            tenant_id=run.tenant_id,
            detail={"steps": len(steps)},
        )
    db.flush()
    return run


def _run_step(db: Session, run: WorkflowRun, step: Step, *, actor: str) -> dict:
    if step.type == "noop":
        return {"ok": True, "step": step.id}

    if step.type == "execute":
        from ..modules.execution.service import ExecutionError, execute as run_execution

        params = step.params or {}
        mandate_id = params.get("mandate_id")
        if not mandate_id:
            raise WorkflowError("MISSING_MANDATE", "Langkah execute wajib menyebut mandate_id.")
        try:
            execution = run_execution(
                db,
                mandate_id=mandate_id,
                action_id=params.get("action_id", step.id),
                action_type=params.get("action_type", "send_email"),
                params=params.get("payload", {}),
                actor=actor,
                correlation_id=run.id,
                tenant_id=run.tenant_id,
            )
        except ExecutionError as exc:
            raise WorkflowError(exc.code, exc.message) from exc
        return {"ok": execution.status == "succeeded", "execution_id": execution.id}

    raise WorkflowError("INVALID_STEP", f"Jenis langkah tidak bisa dijalankan: {step.type}")


def approve_gate(
    db: Session,
    run: WorkflowRun,
    *,
    step_id: str,
    user_id: str,
    capabilities: tuple[str, ...],
    actor: str = "workflow",
) -> WorkflowRun:
    """Setujui gerbang. Menuntut capability `approve` milik manusia, bukan mesin."""
    if "approve" not in capabilities:
        raise WorkflowError("FORBIDDEN", "Menyetujui gerbang menuntut capability approve.")
    rows = _step_rows(db, run)
    row = rows.get(step_id)
    if row is None:
        raise WorkflowError("STEP_NOT_FOUND", "Langkah tidak ditemukan pada run ini.")
    if row.status != "waiting_approval":
        raise WorkflowError("GATE_NOT_WAITING", "Langkah ini tidak sedang menunggu persetujuan.")

    row.status = "succeeded"
    row.approved_by_user_id = user_id
    row.approved_at = datetime.now(timezone.utc)
    row.finished_at = datetime.now(timezone.utc)
    row.output_json = json.dumps({"approved_by": user_id}, sort_keys=True)
    run.status = "running"
    db.flush()
    audit_repo.append_event(
        db,
        event_type="workflow_gate_approved",
        actor=actor,
        scope="workflow",
        action="approve_gate",
        resource=run.id,
        decision="allow",
        tenant_id=run.tenant_id,
        detail={"step_id": step_id, "approved_by": user_id},
    )
    db.flush()
    return run
