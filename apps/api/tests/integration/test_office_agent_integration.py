"""Integrasi Office Agent ujung ke ujung.

Rantai yang dibuktikan di sini adalah rantai yang diklaim produk:

    worker (service account) -> rencana tersimpan
    manusia (approver)       -> approval + mandate
    manusia (approver)       -> eksekusi lewat gateway
    audit chain              -> utuh

Yang juga dibuktikan: worker tidak bisa menyetujui pekerjaannya sendiri, dan
tenant lain tidak bisa melihat rencana ini.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.identity import User
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"

PLAN = {
    "request_id": "req-notulen-001",
    "plan_id": "pln-notulen-001",
    "source": {"kind": "markdown", "title": "Notulen rapat operasional"},
    "document": {"sha256": "a" * 64, "blocks": 12},
    "actions": [
        {
            "action_id": "act-email-budi",
            "action_type": "send_email",
            "params": {"to": "budi@example.test", "subject": "Notulen rapat"},
            "source_ref": {"block": 4},
        },
        {
            "action_id": "act-jadwal-tim",
            "action_type": "create_calendar_event",
            "params": {"title": "Rapat tindak lanjut", "start": "2026-11-06T09:00:00+07:00"},
            "source_ref": {"block": 7},
        },
    ],
    "findings": [{"code": "CALENDAR_CONFLICT", "severity": "warning"}],
    "validation": {"checks_passed": 10, "checks_total": 10},
}


@pytest.fixture(autouse=True)
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_user(role_name: str, *, tenant_slug: str | None = None) -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        if tenant_slug:
            tenant = tenant_repo.get_tenant_by_slug(db, tenant_slug)
        else:
            tenant = tenant_repo.create_tenant(db, slug=f"office-{suffix}", name="Office Test")
        role = tenant_repo.ensure_system_role(db, role_name)
        user = User(
            id=new_id("usr"),
            email=f"{role_name}-{suffix}@example.test",
            display_name=f"Pengguna {role_name}",
            is_active=True,
            password_hash=hash_password(PASSWORD),
        )
        db.add(user)
        db.flush()
        tenant_repo.add_membership(
            db, tenant_id=tenant.id, user_id=user.id, role_id=role.id, is_default=True
        )
        return {"email": user.email, "user_id": user.id, "tenant_id": tenant.id, "tenant_slug": tenant.slug}


def _login(client, account) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": PASSWORD}
    )
    assert response.status_code == 200, response.text


def _post(client, url: str, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["X-CSRF-Token"] = client.cookies.get("dextra_csrf") or ""
    return client.post(url, headers=headers, **kwargs)


@pytest.fixture()
def worker_token(client):
    """Admin menerbitkan identitas mesin untuk worker Office Agent."""
    admin = _make_user("admin")
    approver = _make_user("approver", tenant_slug=admin["tenant_slug"])
    _login(client, admin)
    account = _post(
        client,
        "/api/v1/service-accounts",
        json={
            "name": "office-agent-worker",
            "kind": "worker",
            "description": "Worker Office Agent",
            "scopes": ["view_own", "view_all", "create_request"],
        },
    ).json()
    token = _post(
        client,
        "/api/v1/tokens",
        json={
            "name": "worker-token",
            "scopes": ["view_own", "view_all", "create_request"],
            "service_account_id": account["id"],
        },
    ).json()["token"]
    return {"token": token, "account": account, "admin": admin, "approver": approver}


def test_worker_submits_plan_and_human_approves_it(client, worker_token):
    worker = client.__class__(client.app)
    headers = {"Authorization": f"Bearer {worker_token['token']}"}

    submitted = worker.post("/api/v1/office-agent/plans", json=PLAN, headers=headers)
    assert submitted.status_code == 201, submitted.text
    body = submitted.json()
    assert body["status"] == "received"
    assert body["plan_hash"]
    assert len(body["actions"]) == 2

    # Rencana tercatat atas nama identitas mesin, bukan akun manusia, dan
    # terikat ke tenant pemilik token. Ini pemisahan principal P11 yang bisa
    # diperiksa, bukan hanya diklaim.
    from app.models.office import OfficePlanRequest

    with session_scope() as db:
        row = db.scalar(
            select(OfficePlanRequest).where(OfficePlanRequest.plan_id == "pln-notulen-001")
        )
        assert row is not None
        assert row.created_by_service_account_id == worker_token["account"]["id"]
        assert row.created_by_user_id is None
        assert row.tenant_id == worker_token["admin"]["tenant_id"]

    # Worker tidak bisa menyetujui pekerjaannya sendiri.
    self_approve = worker.post(
        "/api/v1/office-agent/plans/pln-notulen-001/actions/act-email-budi/approve",
        json={},
        headers=headers,
    )
    assert self_approve.status_code == 403

    _login(client, worker_token["approver"])
    approved = _post(
        client,
        "/api/v1/office-agent/plans/pln-notulen-001/actions/act-email-budi/approve",
        json={"reason": "sesuai notulen"},
    )
    assert approved.status_code == 201, approved.text
    decision = approved.json()
    assert decision["mandate_id"]

    executed = _post(
        client,
        "/api/v1/executions",
        json={
            "mandate_id": decision["mandate_id"],
            "action_id": "act-email-budi",
            "action_type": "send_email",
            "params": PLAN["actions"][0]["params"],
        },
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["status"] == "succeeded"

    # Audit chain tetap utuh setelah seluruh rantai.
    verify = client.get("/api/v1/audit-events/verify").json()
    assert verify["ok"] is True
    assert verify["checked"] >= 3


def test_plan_submission_is_idempotent(client, worker_token):
    worker = client.__class__(client.app)
    headers = {"Authorization": f"Bearer {worker_token['token']}"}
    first = worker.post("/api/v1/office-agent/plans", json=PLAN, headers=headers).json()
    second = worker.post("/api/v1/office-agent/plans", json=PLAN, headers=headers).json()
    assert first["id"] == second["id"]


def test_plan_rejects_duplicate_action_ids(client, worker_token):
    worker = client.__class__(client.app)
    payload = {**PLAN, "request_id": "req-duplikat", "plan_id": "pln-duplikat"}
    payload["actions"] = [PLAN["actions"][0], PLAN["actions"][0]]
    response = worker.post(
        "/api/v1/office-agent/plans",
        json=payload,
        headers={"Authorization": f"Bearer {worker_token['token']}"},
    )
    assert response.status_code == 422


def test_plan_is_invisible_to_other_tenant(client, worker_token):
    worker = client.__class__(client.app)
    worker.post(
        "/api/v1/office-agent/plans",
        json=PLAN,
        headers={"Authorization": f"Bearer {worker_token['token']}"},
    )

    other = _make_user("approver")
    _login(client, other)
    assert client.get("/api/v1/office-agent/plans/pln-notulen-001").status_code == 404
    assert client.get("/api/v1/office-agent/plans").json()["items"] == []


def test_other_tenant_cannot_approve_plan(client, worker_token):
    worker = client.__class__(client.app)
    worker.post(
        "/api/v1/office-agent/plans",
        json=PLAN,
        headers={"Authorization": f"Bearer {worker_token['token']}"},
    )
    other = _make_user("approver")
    _login(client, other)
    response = _post(
        client,
        "/api/v1/office-agent/plans/pln-notulen-001/actions/act-email-budi/approve",
        json={},
    )
    assert response.status_code == 404


def test_rejection_issues_no_mandate(client, worker_token):
    worker = client.__class__(client.app)
    worker.post(
        "/api/v1/office-agent/plans",
        json=PLAN,
        headers={"Authorization": f"Bearer {worker_token['token']}"},
    )
    _login(client, worker_token["approver"])
    response = _post(
        client,
        "/api/v1/office-agent/plans/pln-notulen-001/actions/act-email-budi/approve",
        json={"decision": "rejected", "reason": "penerima salah"},
    )
    assert response.status_code == 201
    assert response.json()["mandate_id"] is None
    plan = client.get("/api/v1/office-agent/plans/pln-notulen-001").json()
    assert plan["status"] == "rejected"


def test_service_worker_cannot_read_plans_without_capability(client):
    """Identitas mesin dengan scope sempit tidak mendapat akses baca."""
    admin = _make_user("admin")
    _login(client, admin)
    account = _post(
        client,
        "/api/v1/service-accounts",
        json={"name": "buta", "kind": "worker", "scopes": ["create_request"]},
    ).json()
    token = _post(
        client,
        "/api/v1/tokens",
        json={"name": "buta", "scopes": ["create_request"], "service_account_id": account["id"]},
    ).json()["token"]

    worker = client.__class__(client.app)
    response = worker.get(
        "/api/v1/office-agent/plans", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
