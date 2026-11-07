"""Repository audit — append-only dengan hash chaining.

Satu-satunya tempat penulisan `audit_events`. Tidak ada fungsi update atau delete
di sini, dan itu disengaja: audit yang bisa disunting dari kode aplikasi bukan
audit.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.audit import AuditEvent


def _canonical_at(moment: datetime) -> str:
    """Representasi waktu yang stabil lintas database.

    SQLite mengembalikan datetime tanpa timezone, sementara penulisan memakai
    datetime ber-timezone. Tanpa penyeragaman ini, hash yang dihitung saat
    menulis tidak akan cocok saat verifikasi — dan audit akan tampak rusak
    padahal utuh.
    """
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment.isoformat(timespec="microseconds")


import logging as _logging
import threading as _threading
import time as _time

logger = _logging.getLogger(__name__)
_append_lock = _threading.Lock()


def _next_seq(db: Session) -> int:
    # PostgreSQL: SELECT ... FOR UPDATE pada baris terakhir/aggregate advisory lock.
    # SQLite: tidak ada FOR UPDATE, jadi pakai lock in-process + retry di append_event.
    try:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(select(func.pg_try_advisory_xact_lock(727272)))
    except Exception as exc:
        logger.warning("advisory lock unavailable: %s", exc)
    current = db.scalar(select(func.max(AuditEvent.seq)))
    return 1 if current is None else int(current) + 1


def _payload(event: AuditEvent) -> dict:
    """Bentuk payload sesuai versi rantai baris itu.

    Rantai versi 1 ditulis sebelum atribusi tenant ada. Hash-nya tidak boleh
    dihitung ulang dengan bentuk baru: itu akan mengubah bukti historis dan
    membuat rantai lama tampak rusak. Jadi verifikasi mengikuti versi yang
    tercatat di baris, bukan versi kode saat ini.
    """
    base = {
        "seq": event.seq,
        "at": _canonical_at(event.at),
        "event_type": event.event_type,
        "actor": event.actor,
        "scope": event.scope,
        "action": event.action,
        "resource": event.resource,
        "decision": event.decision,
        "plan_id": event.plan_id,
        "mandate_id": event.mandate_id,
        "execution_id": event.execution_id,
        "correlation_id": event.correlation_id,
        "detail": json.loads(event.detail_json or "{}"),
    }
    if event.chain_version >= 2:
        base["tenant_id"] = event.tenant_id or ""
    return base


def append_event(
    db: Session,
    *,
    event_type: str,
    actor: str,
    scope: str = "none",
    action: str = "",
    resource: str = "",
    decision: str = "",
    plan_id: str = "",
    mandate_id: str = "",
    execution_id: str = "",
    correlation_id: str = "",
    detail: dict | None = None,
    at: datetime | None = None,
    tenant_id: str | None = None,
) -> AuditEvent:
    with _append_lock:
        return _append_event_locked(
            db, event_type=event_type, actor=actor, scope=scope, action=action,
            resource=resource, decision=decision, plan_id=plan_id,
            mandate_id=mandate_id, execution_id=execution_id,
            correlation_id=correlation_id, detail=detail, at=at, tenant_id=tenant_id,
        )


def _append_event_locked(
    db: Session,
    *,
    event_type: str,
    actor: str,
    scope: str = "none",
    action: str = "",
    resource: str = "",
    decision: str = "",
    plan_id: str = "",
    mandate_id: str = "",
    execution_id: str = "",
    correlation_id: str = "",
    detail: dict | None = None,
    at: datetime | None = None,
    tenant_id: str | None = None,
) -> AuditEvent:
    for attempt in range(3):
        try:
            return _append_event_once(
                db, event_type=event_type, actor=actor, scope=scope, action=action,
                resource=resource, decision=decision, plan_id=plan_id,
                mandate_id=mandate_id, execution_id=execution_id,
                correlation_id=correlation_id, detail=detail, at=at, tenant_id=tenant_id,
            )
        except Exception:
            if attempt == 2:
                raise
            db.rollback()
            _time.sleep(0.05 * (attempt + 1))


def _append_event_once(
    db: Session,
    *,
    event_type: str,
    actor: str,
    scope: str = "none",
    action: str = "",
    resource: str = "",
    decision: str = "",
    plan_id: str = "",
    mandate_id: str = "",
    execution_id: str = "",
    correlation_id: str = "",
    detail: dict | None = None,
    at: datetime | None = None,
    tenant_id: str | None = None,
) -> AuditEvent:
    seq = _next_seq(db)
    previous = db.scalar(select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1))
    prev_hash = previous.entry_hash if previous is not None else ""
    moment = at or datetime.now(timezone.utc)
    payload = {
        "seq": seq,
        "at": _canonical_at(moment),
        "event_type": event_type,
        "actor": actor,
        "scope": scope,
        "action": action,
        "resource": resource,
        "decision": decision,
        "plan_id": plan_id,
        "mandate_id": mandate_id,
        "execution_id": execution_id,
        "correlation_id": correlation_id,
        "detail": detail or {},
    }
    # Baris baru selalu versi 2 (atribusi tenant ikut di-hash). Tanpa tenant,
    # nilai yang di-hash adalah string kosong — bukan "tidak ada kunci" —
    # supaya bentuk payload tidak berubah-ubah menurut isi.
    payload["tenant_id"] = tenant_id or ""
    chain_version = 2
    event = AuditEvent(
        id=f"evt_{seq:08d}",
        seq=seq,
        at=moment,
        event_type=event_type,
        actor=actor,
        scope=scope,
        action=action,
        resource=resource,
        decision=decision,
        plan_id=plan_id,
        mandate_id=mandate_id,
        execution_id=execution_id,
        correlation_id=correlation_id,
        detail_json=json.dumps(detail or {}, sort_keys=True),
        tenant_id=tenant_id,
        chain_version=chain_version,
        prev_hash=prev_hash,
        entry_hash=AuditEvent.compute_hash(prev_hash, payload),
    )
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session) -> dict:
    """Rekonstruksi rantai dari awal dan laporkan baris pertama yang rusak."""
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.seq.asc())).all()
    prev_hash = ""
    for event in events:
        expected = AuditEvent.compute_hash(prev_hash, _payload(event))
        if event.prev_hash != prev_hash or event.entry_hash != expected:
            return {"ok": False, "broken_at_seq": event.seq, "checked": len(events)}
        prev_hash = event.entry_hash
    versions = sorted({event.chain_version for event in events})
    return {"ok": True, "checked": len(events), "chain_versions": versions}


def list_events(
    db: Session, limit: int = 100, offset: int = 0, tenant_id: str | None = None
) -> list[AuditEvent]:
    """Daftar event audit milik satu tenant.

    `tenant_id=None` berarti pemanggil tanpa tenant (token gateway lama tanpa
    pengikatan): hasilnya kosong, bukan "semua tenant" — ketiadaan tenant
    adalah fail-closed, bukan akses global.
    """
    if tenant_id is None:
        return []
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.seq.desc())
            .limit(min(limit, 500))
            .offset(offset)
        ).all()
    )
