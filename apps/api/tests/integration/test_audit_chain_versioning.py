"""Rantai audit berversi: baris lama tetap sah, baris baru membawa tenant.

Masalah yang diuji: menambahkan atribusi tenant ke `audit_events` tidak boleh
mengubah hash baris historis. Kalau hash lama dihitung ulang dengan bentuk
payload baru, seluruh rantai produksi akan tampak rusak pada hari migrasi.

Jadi ada dua versi payload:
  v1 — 12 kunci, tanpa `tenant_id` (baris sebelum migrasi).
  v2 — 13 kunci, `tenant_id` ikut di-hash (baris baru).

Verifikasi memilih aturan menurut `chain_version` yang tersimpan, bukan menurut
versi kode saat ini.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.models.audit import AuditEvent
from app.database.session import session_scope
from app.repositories import audit as audit_repo


def _v1_payload(event: AuditEvent) -> dict:
    """Bentuk payload persis seperti kode sebelum P9 lanjutan."""
    return {
        "seq": event.seq,
        "at": audit_repo._canonical_at(event.at),
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


def _insert_v1(db, *, seq: int, prev_hash: str, event_type: str = "legacy_event") -> AuditEvent:
    """Tulis baris dengan tata cara lama: tanpa tenant, hash 12 kunci."""
    moment = datetime.now(timezone.utc)
    event = AuditEvent(
        id=f"evt_{seq:08d}",
        seq=seq,
        at=moment,
        event_type=event_type,
        actor="ops",
        scope="ops",
        action=event_type,
        resource="r",
        decision="allow",
        plan_id="",
        mandate_id="",
        execution_id="",
        correlation_id="",
        detail_json="{}",
        tenant_id=None,
        chain_version=1,
        prev_hash=prev_hash,
        entry_hash="",
    )
    event.entry_hash = AuditEvent.compute_hash(prev_hash, _v1_payload(event))
    db.add(event)
    db.flush()
    return event


@pytest.fixture()
def empty_chain(app):
    """Rantai kosong: `verify_chain` membaca seluruh tabel, jadi tes harus bersih."""
    from sqlalchemy import delete

    with session_scope() as db:
        db.execute(delete(AuditEvent))
    yield


def test_historical_v1_chain_still_verifies(empty_chain):
    """Baris pra-migrasi tidak boleh dianggap rusak hanya karena kode berubah."""
    with session_scope() as db:
        first = _insert_v1(db, seq=1, prev_hash="")
        _insert_v1(db, seq=2, prev_hash=first.entry_hash)

    with session_scope() as db:
        verdict = audit_repo.verify_chain(db)
    assert verdict["ok"] is True
    assert verdict["checked"] == 2
    assert verdict["chain_versions"] == [1]


def test_new_events_are_version_2_and_hash_the_tenant(empty_chain):
    with session_scope() as db:
        event = audit_repo.append_event(
            db, event_type="approval_recorded", actor="user", tenant_id="ten_abc"
        )
        assert event.chain_version == 2
        assert event.tenant_id == "ten_abc"

    with session_scope() as db:
        verdict = audit_repo.verify_chain(db)
    assert verdict == {"ok": True, "checked": 1, "chain_versions": [2]}


def test_mixed_chain_verifies_across_versions(empty_chain):
    """Rantai nyata setelah migrasi berisi v1 lalu v2, bersambung."""
    with session_scope() as db:
        legacy = _insert_v1(db, seq=1, prev_hash="")
        audit_repo.append_event(
            db, event_type="approval_recorded", actor="user", tenant_id="ten_abc"
        )

    with session_scope() as db:
        verdict = audit_repo.verify_chain(db)
    assert verdict["ok"] is True
    assert verdict["chain_versions"] == [1, 2]
    assert legacy.seq == 1


def test_changing_tenant_id_breaks_the_chain(empty_chain):
    """Atribusi tenant ikut di-hash, jadi tidak bisa diubah tanpa jejak."""
    with session_scope() as db:
        event = audit_repo.append_event(
            db, event_type="approval_recorded", actor="user", tenant_id="ten_a"
        )
        seq = event.seq

    with session_scope() as db:
        row = db.query(AuditEvent).filter(AuditEvent.seq == seq).one()
        row.tenant_id = "ten_b"

    with session_scope() as db:
        verdict = audit_repo.verify_chain(db)
    assert verdict["ok"] is False
    assert verdict["broken_at_seq"] == seq


def test_downgrading_chain_version_is_detected(empty_chain):
    """Menurunkan versi untuk menghindari pemeriksaan tenant justru memutus rantai."""
    with session_scope() as db:
        event = audit_repo.append_event(
            db, event_type="approval_recorded", actor="user", tenant_id="ten_a"
        )
        seq = event.seq

    with session_scope() as db:
        row = db.query(AuditEvent).filter(AuditEvent.seq == seq).one()
        row.chain_version = 1

    with session_scope() as db:
        verdict = audit_repo.verify_chain(db)
    assert verdict["ok"] is False
    assert verdict["broken_at_seq"] == seq


def test_verify_endpoint_reports_chain_versions(client, ops_headers, empty_chain, monkeypatch):
    """Kontrak HTTP: verifikasi menyebut versi rantai yang dilihatnya."""
    with session_scope() as db:
        audit_repo.append_event(
            db, event_type="approval_recorded", actor="user", tenant_id="ten_abc"
        )

    body = client.get("/api/v1/audit-events/verify", headers=ops_headers).json()
    assert body["ok"] is True
    assert body["chain_versions"] == [2]
