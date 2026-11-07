"""Isolasi tenant untuk Agent, Task, WorkPackage, Policy — diuji lewat HTTP."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.governance import Policy, PolicyEvaluation
from app.models.identity import User
from app.models.tasks import Task, WorkPackage
from app.models.workforce import Agent
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"


@pytest.fixture()
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_tenant_user(role_name: str, *, slug_prefix: str = "rbac") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="RBAC Test")
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
        return {
            "email": user.email,
            "user_id": user.id,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "role": role_name,
        }


def _login(client, account) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return client.cookies.get("dextra_csrf") or ""


def _seed_operational(tenant_id: str, *, slug: str = "shared-slug") -> dict:
    tag = uuid.uuid4().hex[:6]
    with session_scope() as db:
        agent = Agent(
            id=new_id("agt"),
            tenant_id=tenant_id,
            slug=slug,
            display_name=f"Agen {tag}",
            agent_type="assistant",
            status="idle",
        )
        db.add(agent)
        db.flush()
        policy = Policy(
            id=new_id("pol"),
            tenant_id=tenant_id,
            slug=slug,
            title=f"Policy {tag}",
            scope="organization",
        )
        db.add(policy)
        db.flush()
        package = WorkPackage(
            id=new_id("wpg"), tenant_id=tenant_id, title=f"Paket {tag}", status="draft"
        )
        db.add(package)
        db.flush()
        task = Task(
            id=new_id("tsk"),
            tenant_id=tenant_id,
            work_package_id=package.id,
            title=f"Tugas {tag}",
            status="todo",
        )
        db.add(task)
        db.flush()
        return {
            "agent_id": agent.id,
            "agent_slug": slug,
            "policy_id": policy.id,
            "policy_slug": slug,
            "work_package_id": package.id,
            "task_id": task.id,
        }


def _logout(client) -> None:
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""})


def test_same_slug_allowed_in_two_tenants_and_lists_are_isolated(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    # Slug sama di dua tenant harus sah (composite unique tenant_id+slug).
    a = _seed_operational(alpha["tenant_id"])
    b = _seed_operational(beta["tenant_id"])
    assert a["agent_slug"] == b["agent_slug"]

    _login(client, alpha)
    agents = client.get("/api/v1/agents").json()["items"]
    assert {item["id"] for item in agents} == {a["agent_id"]}
    assert agents[0]["slug"] == "shared-slug"
    # Detail slug resolving ke milik tenant pemanggil, bukan tenant lain.
    assert client.get(f"/api/v1/agents/{a['agent_slug']}").json()["id"] == a["agent_id"]
    assert client.get("/api/v1/work-packages").json()["items"][0]["id"] == a["work_package_id"]
    assert client.get("/api/v1/tasks").json()["items"][0]["id"] == a["task_id"]
    assert client.get("/api/v1/policies").json()["items"][0]["id"] == a["policy_id"]
    _logout(client)

    _login(client, beta)
    agents = client.get("/api/v1/agents").json()["items"]
    assert {item["id"] for item in agents} == {b["agent_id"]}
    assert client.get(f"/api/v1/agents/{b['agent_slug']}").json()["id"] == b["agent_id"]
    assert client.get("/api/v1/tasks").json()["items"][0]["id"] == b["task_id"]
    assert client.get("/api/v1/policies").json()["items"][0]["id"] == b["policy_id"]
    assert client.get("/api/v1/overview").json()["kpi"]["active_agents"] == 1


def test_cross_tenant_detail_is_404(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed_operational(alpha["tenant_id"], slug="alpha-only")
    _seed_operational(beta["tenant_id"], slug="beta-only")

    _login(client, beta)
    assert client.get(f"/api/v1/agents/{a['agent_slug']}").status_code == 404


def test_create_task_on_foreign_work_package_is_rejected(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed_operational(alpha["tenant_id"])

    _login(client, beta)
    response = client.post(
        "/api/v1/tasks",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={"work_package_id": a["work_package_id"], "title": "Coba lintas tenant"},
    )
    assert response.status_code == 404
    with session_scope() as db:
        assert db.scalar(select(Task).where(Task.title == "Coba lintas tenant")) is None


def test_create_task_stamps_caller_tenant(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed_operational(alpha["tenant_id"])

    _login(client, alpha)
    response = client.post(
        "/api/v1/tasks",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={"work_package_id": a["work_package_id"], "title": "Tugas sah"},
    )
    assert response.status_code == 201, response.text
    with session_scope() as db:
        row = db.scalar(select(Task).where(Task.title == "Tugas sah"))
        assert row is not None and row.tenant_id == alpha["tenant_id"]


def test_evaluate_cannot_reference_foreign_policy(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed_operational(alpha["tenant_id"], slug="alpha-policy")

    _login(client, beta)
    response = client.post(
        "/api/v1/policies/evaluate",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={"action_type": "send_email", "policy_slug": a["policy_slug"]},
    )
    assert response.status_code == 404
    with session_scope() as db:
        assert db.scalar(select(PolicyEvaluation).where(PolicyEvaluation.policy_slug == a["policy_slug"])) is None


def test_evaluate_records_caller_tenant(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    _seed_operational(alpha["tenant_id"])

    _login(client, alpha)
    response = client.post(
        "/api/v1/policies/evaluate",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={"action_type": "send_email", "policy_slug": "shared-slug", "plan_id": "pln_eval"},
    )
    assert response.status_code == 200, response.text
    with session_scope() as db:
        row = db.scalar(select(PolicyEvaluation).where(PolicyEvaluation.plan_id == "pln_eval"))
        assert row is not None and row.tenant_id == alpha["tenant_id"]


def test_tenantless_caller_gets_empty_lists(client, ops_headers, _clean_throttle, monkeypatch):
    """Tenantless (legacy tanpa pengikatan) fail-closed: kosong, bukan semua data."""
    monkeypatch.delenv("DEXTRA_LEGACY_TENANT", raising=False)
    account = _make_tenant_user("operator")
    _seed_operational(account["tenant_id"])

    for path in ("/api/v1/agents", "/api/v1/work-packages", "/api/v1/tasks", "/api/v1/policies"):
        response = client.get(path, headers=ops_headers)
        if response.status_code == 200:
            assert response.json()["items"] == [], path
        else:
            assert response.status_code in (400, 401, 403, 404), path
