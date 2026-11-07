"""Alur tata kelola end-to-end: approval -> mandate -> eksekusi -> cabut -> diblokir.

Sejak token gateway diikat ke tenant, alur ini berjalan sebagai gateway yang
terikat — bukan sebagai token tanpa tenant yang dulu bisa membaca mandate siapa
pun. Tanpa pengikatan, langkah baca akan 404 dan tes ini akan menguji kebalikan
dari yang dimaksud.
"""
from __future__ import annotations

import uuid

import pytest

from app.database.session import session_scope
from app.repositories import tenants as tenant_repo


@pytest.fixture(autouse=True)
def legacy_tenant(app, monkeypatch):
    """Tenant tempat token gateway bekerja selama tes alur tata kelola."""
    slug = f"gov-{uuid.uuid4().hex[:8]}"
    with session_scope() as db:
        tenant_repo.create_tenant(db, slug=slug, name="Governance Flow")
    monkeypatch.setenv("DEXTRA_LEGACY_TENANT", slug)
    return slug


def _approve(client, ops_headers, *, plan_id="pln_flow", action_id="act_1", params=None):
    response = client.post(
        "/api/v1/approvals",
        headers=ops_headers,
        json={
            "plan_id": plan_id,
            "action_id": action_id,
            "action_type": "send_email",
            "params": params or {"to": "a@example.com"},
            "plan_hash": "hash_plan",
            "approver_id": "user_001",
            "decision": "approved",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["mandate_id"]


def test_approval_issues_mandate(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_issue")
    assert mandate_id.startswith("mnd_")
    detail = client.get(f"/api/v1/mandates/{mandate_id}", headers=ops_headers).json()
    assert detail["status"] == "issued"
    assert detail["usable"] is True
    assert detail["action_id"] == "act_1"


def test_rejected_approval_issues_no_mandate(client, ops_headers):
    response = client.post(
        "/api/v1/approvals",
        headers=ops_headers,
        json={
            "plan_id": "pln_reject",
            "action_id": "act_1",
            "action_type": "send_email",
            "params": {"to": "a@example.com"},
            "approver_id": "user_001",
            "decision": "rejected",
            "reason": "tidak sesuai kebijakan",
        },
    )
    assert response.status_code == 201
    assert response.json()["mandate_id"] is None


def test_execution_under_valid_mandate_succeeds(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_exec")
    response = client.post(
        "/api/v1/executions",
        headers=ops_headers,
        json={
            "mandate_id": mandate_id,
            "action_id": "act_1",
            "action_type": "send_email",
            "params": {"to": "a@example.com"},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"


def test_same_action_twice_is_idempotent(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_idem")
    body = {
        "mandate_id": mandate_id,
        "action_id": "act_1",
        "action_type": "send_email",
        "params": {"to": "a@example.com"},
    }
    first = client.post("/api/v1/executions", headers=ops_headers, json=body).json()
    second = client.post("/api/v1/executions", headers=ops_headers, json=body).json()
    assert first["id"] == second["id"]
    listed = client.get("/api/v1/executions", headers=ops_headers).json()["items"]
    assert len([e for e in listed if e["mandate_id"] == mandate_id]) == 1


def test_changed_params_are_rejected(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_params")
    response = client.post(
        "/api/v1/executions",
        headers=ops_headers,
        json={
            "mandate_id": mandate_id,
            "action_id": "act_1",
            "action_type": "send_email",
            "params": {"to": "attacker@example.com"},
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PARAMS_CHANGED"


def test_action_outside_mandate_is_rejected(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_action")
    response = client.post(
        "/api/v1/executions",
        headers=ops_headers,
        json={
            "mandate_id": mandate_id,
            "action_id": "act_lain",
            "action_type": "send_email",
            "params": {"to": "a@example.com"},
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACTION_NOT_IN_MANDATE"


def test_revoked_mandate_blocks_execution(client, ops_headers):
    mandate_id = _approve(client, ops_headers, plan_id="pln_revoke")
    assert client.post(
        f"/api/v1/mandates/{mandate_id}/revoke", headers=ops_headers, json={"reason": "uji"}
    ).status_code == 200
    response = client.post(
        "/api/v1/executions",
        headers=ops_headers,
        json={
            "mandate_id": mandate_id,
            "action_id": "act_1",
            "action_type": "send_email",
            "params": {"to": "a@example.com"},
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "MANDATE_REVOKED"


def test_audit_chain_records_the_flow(client, ops_headers):
    _approve(client, ops_headers, plan_id="pln_audit")
    events = client.get("/api/v1/audit-events", headers=ops_headers).json()["items"]
    types = {e["event_type"] for e in events}
    assert "approval_recorded" in types
    assert "mandate_issued" in types
    assert client.get("/api/v1/audit-events/verify", headers=ops_headers).json()["ok"] is True


def test_overview_counts_come_from_database(client, ops_headers):
    payload = client.get("/api/v1/overview", headers=ops_headers).json()
    assert set(payload["kpi"]) >= {"active_agents", "pending_approvals", "active_mandates"}
    # Angka yang belum bisa dihitung dinyatakan tidak tersedia, bukan ditebak.
    assert "approval_response_time" in payload["unavailable"]
