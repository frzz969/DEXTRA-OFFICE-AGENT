"""Skill Registry dan orkestrasi workflow.

Yang diuji: katalog menolak manifest yang tidak sah, siklus hidup tidak bisa
dilompati, dan workflow benar-benar berhenti di gerbang persetujuan manusia lalu
melanjutkan dari checkpoint.
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
            tenant = tenant_repo.create_tenant(db, slug=f"cat-{suffix}", name="Catalog Test")
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


SKILL_PAYLOAD = {
    "slug": "kirim-notulen",
    "display_name": "Kirim notulen rapat",
    "description": "Menyusun dan mengirim ringkasan rapat.",
    "version": "1.0.0",
    "input_schema": {"type": "object", "properties": {"meeting_id": {"type": "string"}}},
    "output_schema": {"type": "object"},
    "required_capabilities": ["create_request", "view_own"],
}


# --- Skill Registry ---------------------------------------------------------


def test_create_skill_starts_as_draft(client):
    account = _make_user("admin")
    _login(client, account)
    response = _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["versions"][0]["version"] == "1.0.0"
    assert body["versions"][0]["required_capabilities"] == ["create_request", "view_own"]


def test_duplicate_slug_is_rejected(client):
    account = _make_user("admin")
    _login(client, account)
    _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)
    response = _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DUPLICATE_SKILL_ID"


def test_skill_cannot_request_privileged_capability(client):
    account = _make_user("admin")
    _login(client, account)
    payload = {**SKILL_PAYLOAD, "slug": "naik-wewenang", "required_capabilities": ["execute"]}
    response = _post(client, "/api/v1/skills", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PRIVILEGED_CAPABILITY_FORBIDDEN"


def test_skill_cannot_request_unknown_capability(client):
    account = _make_user("admin")
    _login(client, account)
    payload = {**SKILL_PAYLOAD, "slug": "tidak-dikenal", "required_capabilities": ["terbang"]}
    response = _post(client, "/api/v1/skills", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_CAPABILITY"


def test_invalid_semver_is_rejected(client):
    account = _make_user("admin")
    _login(client, account)
    payload = {**SKILL_PAYLOAD, "slug": "versi-aneh", "version": "1.0"}
    response = _post(client, "/api/v1/skills", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_SEMVER"


def test_lifecycle_activate_and_deprecate(client):
    account = _make_user("admin")
    _login(client, account)
    _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)

    activated = _post(client, "/api/v1/skills/kirim-notulen/status", json={"status": "active"})
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    assert activated.json()["versions"][0]["status"] == "active"
    assert activated.json()["versions"][0]["published_at"]

    deprecated = _post(client, "/api/v1/skills/kirim-notulen/status", json={"status": "deprecated"})
    assert deprecated.status_code == 200

    # deprecated adalah status akhir: tidak bisa diaktifkan lagi.
    revived = _post(client, "/api/v1/skills/kirim-notulen/status", json={"status": "active"})
    assert revived.status_code == 409
    assert revived.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_new_version_is_added_and_becomes_latest(client):
    account = _make_user("admin")
    _login(client, account)
    _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)
    added = _post(
        client,
        "/api/v1/skills/kirim-notulen/versions",
        json={"version": "1.1.0", "required_capabilities": ["create_request"]},
    )
    assert added.status_code == 201
    detail = client.get("/api/v1/skills/kirim-notulen").json()
    assert detail["latest_version"] == "1.1.0"
    assert len(detail["versions"]) == 2
    # Urut dari versi tertinggi.
    assert detail["versions"][0]["version"] == "1.1.0"


def test_non_admin_cannot_register_skill(client):
    account = _make_user("approver")
    _login(client, account)
    assert _post(client, "/api/v1/skills", json=SKILL_PAYLOAD).status_code == 403
    # Tetap boleh membaca katalog.
    assert client.get("/api/v1/skills").status_code == 200


def test_skill_catalog_is_tenant_isolated(client):
    first = _make_user("admin")
    _login(client, first)
    _post(client, "/api/v1/skills", json=SKILL_PAYLOAD)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    second = _make_user("admin")
    _login(client, second)
    items = client.get("/api/v1/skills").json()["items"]
    assert all(item["slug"] != "kirim-notulen" for item in items)
    assert client.get("/api/v1/skills/kirim-notulen").status_code == 404


# --- Workflow ---------------------------------------------------------------

WORKFLOW_STEPS = [
    {"id": "siapkan", "type": "noop"},
    {"id": "persetujuan", "type": "approval_gate", "depends_on": ["siapkan"]},
    {"id": "selesai", "type": "noop", "depends_on": ["persetujuan"]},
]


def _tenant_with(roles: list[str]) -> tuple[dict, dict[str, dict]]:
    """Satu tenant, satu admin (pembuat workflow), dan anggota lain per role."""
    admin = _make_user("admin")
    accounts = {role: _make_user(role, tenant_slug=admin["tenant_slug"]) for role in roles}
    return admin, accounts


def _create_workflow(client, admin: dict, *, name: str = "alur-notulen", steps=None) -> dict:
    admin_client = client.__class__(client.app)
    _login(admin_client, admin)
    response = _post(
        admin_client,
        "/api/v1/workflows",
        json={"name": name, "steps": steps if steps is not None else WORKFLOW_STEPS},
    )
    assert response.status_code == 201, response.text
    workflow = response.json()
    activated = _post(admin_client, f"/api/v1/workflows/{workflow['id']}/activate")
    assert activated.status_code == 200
    return workflow


def test_workflow_rejects_unknown_dependency(client):
    account = _make_user("admin")
    _login(client, account)
    response = _post(
        client,
        "/api/v1/workflows",
        json={"name": "rusak", "steps": [{"id": "a", "type": "noop", "depends_on": ["hantu"]}]},
    )
    assert response.status_code == 422
    assert "dependensi tidak dikenal" in response.json()["detail"]["message"]


def test_workflow_rejects_cycle(client):
    account = _make_user("admin")
    _login(client, account)
    response = _post(
        client,
        "/api/v1/workflows",
        json={
            "name": "siklus",
            "steps": [
                {"id": "a", "type": "noop", "depends_on": ["b"]},
                {"id": "b", "type": "noop", "depends_on": ["a"]},
            ],
        },
    )
    assert response.status_code == 422
    assert "siklus" in response.json()["detail"]["message"]


def test_run_stops_at_human_gate(client):
    admin, accounts = _tenant_with(["approver"])
    approver = accounts["approver"]
    workflow = _create_workflow(client, admin)

    _login(client, approver)
    started = _post(
        client,
        f"/api/v1/workflows/{workflow['id']}/runs",
        json={"idempotency_key": f"run-{uuid.uuid4().hex}"},
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert body["status"] == "waiting_approval"
    steps = {step["step_id"]: step["status"] for step in body["steps"]}
    assert steps["siapkan"] == "succeeded"
    assert steps["persetujuan"] == "waiting_approval"
    assert steps["selesai"] == "pending"
    assert body["checkpoint_at"]


def test_gate_approval_resumes_and_completes(client):
    admin, accounts = _tenant_with(["approver"])
    approver = accounts["approver"]
    workflow = _create_workflow(client, admin)

    _login(client, approver)
    run = _post(
        client,
        f"/api/v1/workflows/{workflow['id']}/runs",
        json={"idempotency_key": f"run-{uuid.uuid4().hex}"},
    ).json()

    approved = _post(
        client, f"/api/v1/workflows/runs/{run['id']}/gates/persetujuan/approve", json={}
    )
    assert approved.status_code == 200, approved.text
    final = approved.json()
    assert final["status"] == "succeeded"
    steps = {step["step_id"]: step["status"] for step in final["steps"]}
    assert all(status == "succeeded" for status in steps.values())
    gate = next(step for step in final["steps"] if step["step_id"] == "persetujuan")
    assert gate["approved_by"] == approver["user_id"]


def test_non_approver_cannot_approve_gate(client):
    admin, accounts = _tenant_with(["operator"])
    operator = accounts["operator"]
    workflow = _create_workflow(client, admin)

    admin_client = client.__class__(client.app)
    _login(admin_client, admin)
    run = _post(
        admin_client,
        f"/api/v1/workflows/{workflow['id']}/runs",
        json={"idempotency_key": f"run-{uuid.uuid4().hex}"},
    ).json()

    _login(client, operator)
    response = _post(client, f"/api/v1/workflows/runs/{run['id']}/gates/persetujuan/approve", json={})
    assert response.status_code == 403


def test_run_is_idempotent(client):
    admin, accounts = _tenant_with(["approver"])
    approver = accounts["approver"]
    workflow = _create_workflow(client, admin)

    _login(client, approver)
    key = f"run-{uuid.uuid4().hex}"
    first = _post(
        client, f"/api/v1/workflows/{workflow['id']}/runs", json={"idempotency_key": key}
    ).json()
    second = _post(
        client, f"/api/v1/workflows/{workflow['id']}/runs", json={"idempotency_key": key}
    ).json()
    assert first["id"] == second["id"]


def test_execute_step_without_capability_fails_honestly(client):
    admin, accounts = _tenant_with(["operator"])
    operator = accounts["operator"]
    workflow = _create_workflow(
        client,
        admin,
        name="alur-eksekusi",
        steps=[{"id": "kirim", "type": "execute", "params": {"mandate_id": "mnd_tidak_ada"}}],
    )

    _login(client, operator)
    run = _post(
        client,
        f"/api/v1/workflows/{workflow['id']}/runs",
        json={"idempotency_key": f"run-{uuid.uuid4().hex}"},
    ).json()
    assert run["status"] == "failed"
    assert "execute" in run["error"]


def test_workflow_runs_are_tenant_isolated(client):
    admin, accounts = _tenant_with(["approver"])
    approver = accounts["approver"]
    workflow = _create_workflow(client, admin)

    _login(client, approver)
    run = _post(
        client,
        f"/api/v1/workflows/{workflow['id']}/runs",
        json={"idempotency_key": f"run-{uuid.uuid4().hex}"},
    ).json()
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    other = _make_user("approver")
    _login(client, other)
    assert client.get(f"/api/v1/workflows/runs/{run['id']}").status_code == 404
    assert client.get("/api/v1/workflows/runs").json()["items"] == []
