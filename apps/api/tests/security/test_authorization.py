"""Batas otorisasi: default-deny, pemisahan scope, dan capability tanpa backend."""
from __future__ import annotations

import pytest

PROTECTED_READS = [
    "/api/v1/overview",
    "/api/v1/agents",
    "/api/v1/work-packages",
    "/api/v1/tasks",
    "/api/v1/executions",
    "/api/v1/approvals",
    "/api/v1/mandates",
    "/api/v1/policies",
]


@pytest.mark.parametrize("path", PROTECTED_READS)
def test_no_token_is_401(client, path):
    assert client.get(path).status_code == 401


def test_unknown_token_is_401(client):
    response = client.get("/api/v1/overview", headers={"Authorization": "Bearer salah"})
    assert response.status_code == 401


def test_malformed_header_is_401(client):
    assert client.get("/api/v1/overview", headers={"Authorization": "ops-dev-token"}).status_code == 401


def test_agent_cannot_read_audit(client, agent_headers):
    assert client.get("/api/v1/audit-events", headers=agent_headers).status_code == 403


def test_agent_cannot_approve(client, agent_headers):
    response = client.post(
        "/api/v1/approvals",
        headers=agent_headers,
        json={
            "plan_id": "pln_x",
            "action_id": "act_x",
            "action_type": "send_email",
            "params": {},
            "approver_id": "user_001",
            "decision": "approved",
        },
    )
    assert response.status_code == 403


def test_agent_cannot_execute(client, agent_headers):
    response = client.post(
        "/api/v1/executions",
        headers=agent_headers,
        json={"mandate_id": "mnd_x", "action_id": "act_x", "action_type": "send_email", "params": {}},
    )
    assert response.status_code == 403


def test_agent_can_read_own_context(client, agent_headers):
    payload = client.get("/api/v1/permissions", headers=agent_headers).json()
    assert payload["scope"] == "agent"
    assert payload["principal"] is None
    assert "execute" not in payload["capabilities"]


def test_unbacked_capability_is_locked_for_ops(client, ops_headers):
    """manage_users tidak pernah diberikan ke scope gateway, termasuk ops."""
    assert client.get("/api/v1/users", headers=ops_headers).status_code == 403
    assert client.get("/api/v1/roles", headers=ops_headers).status_code == 403


def test_capability_report_distinguishes_enforced_from_granted(client, ops_headers):
    """Tiga hal berbeda: dimiliki pemanggil, punya penegak, dan belum ada penegak.

    `manage_users` sekarang punya penegak (endpoint admin P9/P11), tetapi tetap
    tidak dimiliki scope `ops`. Dulu laporan menyebutnya "belum tersedia" —
    klaim yang salah pada endpoint yang dibaca frontend.
    """
    payload = client.get("/api/v1/permissions", headers=ops_headers).json()
    assert "manage_users" not in payload["capabilities"]
    assert "manage_users" in payload["enforced_capabilities"]
    assert payload["unbacked_capabilities"] == []
