"""Isolasi tenant untuk operasi tulis: Agent, WorkPackage, Task, Policy, penugasan.

Yang diuji di sini bukan "apakah 403 muncul", melainkan apakah data berubah.
Setiap penolakan diperiksa dengan membaca ulang baris di database: endpoint yang
mengembalikan 404 tetapi tetap menulis adalah kebocoran yang lebih buruk daripada
404 yang jujur.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.governance import Policy
from app.models.identity import User
from app.models.tasks import Task, WorkPackage
from app.models.workforce import Agent, AgentAssignment
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"
ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture()
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_tenant_user(role_name: str, *, slug_prefix: str = "iso") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="Iso Test")
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
        }


def _login(client, account) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}


def _logout(client) -> None:
    client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    )


def _seed(tenant_id: str, *, slug: str = "shared") -> dict:
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
            id=new_id("pol"), tenant_id=tenant_id, slug=slug, title=f"Policy {tag}"
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
            "package_id": package.id,
            "task_id": task.id,
        }


# ---------------------------------------------------------------- agent


def test_agent_update_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    own = client.patch(f"/api/v1/agents/{a['agent_slug']}", json={"status": "busy"}, headers=headers)
    assert own.status_code == 200, own.text
    assert own.json()["status"] == "busy"

    # Slug milik tenant lain: 404, dan barisnya tidak berubah.
    foreign = client.patch(
        f"/api/v1/agents/{b['agent_slug']}", json={"status": "disabled"}, headers=headers
    )
    assert foreign.status_code == 404

    with session_scope() as db:
        assert db.get(Agent, a["agent_id"]).status == "busy"
        assert db.get(Agent, b["agent_id"]).status == "idle"


def test_same_slug_updates_only_the_callers_row(client, _clean_throttle):
    """Slug identik di dua tenant: PATCH hanya menyentuh baris tenant pemanggil."""
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="shared")
    b = _seed(beta["tenant_id"], slug="shared")

    _login(client, alpha)
    response = client.patch(
        "/api/v1/agents/shared",
        json={"status": "busy", "display_name": "Milik Alpha"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == a["agent_id"]

    with session_scope() as db:
        assert db.get(Agent, a["agent_id"]).display_name == "Milik Alpha"
        other = db.get(Agent, b["agent_id"])
        assert other.display_name != "Milik Alpha"
        assert other.status == "idle"


def test_agent_delete_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    assert client.delete(f"/api/v1/agents/{b['agent_slug']}", headers=headers).status_code == 404
    with session_scope() as db:
        assert db.get(Agent, b["agent_id"]) is not None

    assert client.delete(f"/api/v1/agents/{a['agent_slug']}", headers=headers).status_code == 200
    with session_scope() as db:
        assert db.get(Agent, a["agent_id"]) is None
        assert db.get(Agent, b["agent_id"]) is not None


def test_agent_update_rejects_unknown_status(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"])
    _login(client, alpha)
    response = client.patch(
        f"/api/v1/agents/{a['agent_slug']}",
        json={"status": "teleported"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 422
    with session_scope() as db:
        assert db.get(Agent, a["agent_id"]).status == "idle"


# ---------------------------------------------------------------- work package


def test_work_package_update_and_delete_are_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"])
    b = _seed(beta["tenant_id"])

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}

    own = client.patch(
        f"/api/v1/work-packages/{a['package_id']}", json={"priority": "high"}, headers=headers
    )
    assert own.status_code == 200, own.text
    assert own.json()["priority"] == "high"

    assert (
        client.patch(
            f"/api/v1/work-packages/{b['package_id']}", json={"priority": "low"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/work-packages/{b['package_id']}", headers=headers).status_code
        == 404
    )

    with session_scope() as db:
        assert db.get(WorkPackage, a["package_id"]).priority == "high"
        assert db.get(WorkPackage, b["package_id"]).priority == "normal"

    assert (
        client.delete(f"/api/v1/work-packages/{a['package_id']}", headers=headers).status_code
        == 200
    )
    with session_scope() as db:
        assert db.get(WorkPackage, a["package_id"]) is None
        assert db.get(WorkPackage, b["package_id"]) is not None


# ---------------------------------------------------------------- task


def test_task_status_change_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"])
    b = _seed(beta["tenant_id"])

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}

    own = client.patch(
        f"/api/v1/tasks/{a['task_id']}", json={"status": "approved"}, headers=headers
    )
    assert own.status_code == 200, own.text
    assert own.json()["status"] == "approved"

    foreign = client.patch(
        f"/api/v1/tasks/{b['task_id']}", json={"status": "cancelled"}, headers=headers
    )
    assert foreign.status_code == 404

    with session_scope() as db:
        assert db.get(Task, a["task_id"]).status == "approved"
        assert db.get(Task, b["task_id"]).status == "todo"


def test_task_update_rejects_unknown_status(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"])
    _login(client, alpha)
    response = client.patch(
        f"/api/v1/tasks/{a['task_id']}",
        json={"status": "done-ish"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 422
    with session_scope() as db:
        assert db.get(Task, a["task_id"]).status == "todo"


def test_task_delete_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"])
    b = _seed(beta["tenant_id"])

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    assert client.delete(f"/api/v1/tasks/{b['task_id']}", headers=headers).status_code == 404
    with session_scope() as db:
        assert db.get(Task, b["task_id"]) is not None

    assert client.delete(f"/api/v1/tasks/{a['task_id']}", headers=headers).status_code == 200
    with session_scope() as db:
        assert db.get(Task, a["task_id"]) is None


# ---------------------------------------------------------------- assignment


def test_assignment_stamps_caller_tenant_and_rejects_foreign_agent(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}

    ok = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    assert ok.status_code == 201, ok.text
    assignment_id = ok.json()["id"]
    with session_scope() as db:
        row = db.get(AgentAssignment, assignment_id)
        assert row is not None and row.tenant_id == alpha["tenant_id"]
        assert db.get(Task, a["task_id"]).assigned_agent_id == a["agent_id"]

    # Agen tenant lain: 404, dan tidak ada baris penugasan yang dibuat.
    foreign = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "beta-agent"},
        headers=headers,
    )
    assert foreign.status_code == 404
    with session_scope() as db:
        assert (
            db.scalar(
                select(AgentAssignment).where(AgentAssignment.agent_id == b["agent_id"])
            )
            is None
        )


def test_assignment_to_foreign_task_is_rejected(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    response = client.post(
        f"/api/v1/tasks/{b['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 404
    with session_scope() as db:
        assert db.scalar(select(AgentAssignment).where(AgentAssignment.task_id == b["task_id"])) is None


def test_assignment_is_idempotent(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}

    first = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["id"] == second.json()["id"]
    with session_scope() as db:
        rows = db.scalars(
            select(AgentAssignment).where(AgentAssignment.task_id == a["task_id"])
        ).all()
        assert len(rows) == 1


def test_unassign_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    created = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    assignment_id = created.json()["id"]

    # Penugasan milik tenant lain tidak bisa dihapus lewat task sendiri.
    _logout(client)
    _login(client, beta)
    beta_headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    assert (
        client.delete(
            f"/api/v1/tasks/{b['task_id']}/assignments/{assignment_id}", headers=beta_headers
        ).status_code
        == 404
    )
    with session_scope() as db:
        assert db.get(AgentAssignment, assignment_id) is not None

    _logout(client)
    _login(client, alpha)
    alpha_headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    assert (
        client.delete(
            f"/api/v1/tasks/{a['task_id']}/assignments/{assignment_id}", headers=alpha_headers
        ).status_code
        == 200
    )
    with session_scope() as db:
        assert db.get(AgentAssignment, assignment_id) is None
        assert db.get(Task, a["task_id"]).assigned_agent_id is None


# ---------------------------------------------------------------- policy


def test_policy_update_and_delete_are_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-policy")
    b = _seed(beta["tenant_id"], slug="beta-policy")

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}

    own = client.patch(
        f"/api/v1/policies/{a['policy_slug']}",
        json={"title": "Judul baru", "rules_json": '{"deny_when":"x"}'},
        headers=headers,
    )
    assert own.status_code == 200, own.text
    assert own.json()["version"] == 1

    assert (
        client.patch(
            f"/api/v1/policies/{b['policy_slug']}", json={"title": "Diambil alih"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/policies/{b['policy_slug']}", headers=headers).status_code == 404
    )

    with session_scope() as db:
        assert db.get(Policy, b["policy_id"]).title != "Diambil alih"
        assert db.get(Policy, b["policy_id"]) is not None

    assert client.delete(f"/api/v1/policies/{a['policy_slug']}", headers=headers).status_code == 200
    with session_scope() as db:
        assert db.get(Policy, a["policy_id"]) is None


def test_policy_write_requires_edit_policy(client, _clean_throttle):
    """Operator punya create_request, bukan edit_policy."""
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"])
    _login(client, alpha)
    response = client.patch(
        f"/api/v1/policies/{a['policy_slug']}",
        json={"title": "Tidak boleh"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 403
    with session_scope() as db:
        assert db.get(Policy, a["policy_id"]).title != "Tidak boleh"


# ---------------------------------------------------------------- default deny


def test_tenantless_caller_cannot_write(client, ops_headers, _clean_throttle, monkeypatch):
    """Token gateway tanpa pengikatan tenant tidak boleh menulis apa pun."""
    monkeypatch.delenv("DEXTRA_LEGACY_TENANT", raising=False)
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"])

    for method, path, body in (
        ("patch", f"/api/v1/agents/{a['agent_slug']}", {"status": "busy"}),
        ("delete", f"/api/v1/agents/{a['agent_slug']}", None),
        ("patch", f"/api/v1/tasks/{a['task_id']}", {"status": "approved"}),
        ("delete", f"/api/v1/tasks/{a['task_id']}", None),
        ("patch", f"/api/v1/work-packages/{a['package_id']}", {"priority": "high"}),
        ("patch", f"/api/v1/policies/{a['policy_slug']}", {"title": "x"}),
        ("post", f"/api/v1/tasks/{a['task_id']}/assignments", {"agent_slug": a["agent_slug"]}),
    ):
        response = client.request(method.upper(), path, headers=ops_headers, json=body)
        assert response.status_code in (400, 401, 403, 404), (path, response.status_code)

    with session_scope() as db:
        assert db.get(Agent, a["agent_id"]).status == "idle"
        assert db.get(Task, a["task_id"]).status == "todo"
        assert db.get(WorkPackage, a["package_id"]).priority == "normal"
        assert db.scalar(select(AgentAssignment).where(AgentAssignment.task_id == a["task_id"])) is None


def test_tenant_id_in_body_is_ignored(client, _clean_throttle):
    """Tenant berasal dari caller; field asing di body tidak boleh membelokkannya."""
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    b = _seed(beta["tenant_id"], slug="beta-agent")

    _login(client, alpha)
    response = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent", "tenant_id": beta["tenant_id"]},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert response.status_code == 201
    with session_scope() as db:
        row = db.get(AgentAssignment, response.json()["id"])
        assert row.tenant_id == alpha["tenant_id"]
        assert row.tenant_id != beta["tenant_id"]


def test_legacy_null_rows_are_invisible_and_untouched(client, _clean_throttle):
    """Baris legacy tanpa tenant bukan milik siapa pun — termasuk tenant demo."""
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    _seed(alpha["tenant_id"], slug="alpha-agent")

    with session_scope() as db:
        legacy = Agent(
            id=new_id("agt"),
            tenant_id=None,
            slug="legacy-agent",
            display_name="Legacy",
            agent_type="assistant",
            status="idle",
        )
        db.add(legacy)
        db.flush()
        legacy_id = legacy.id

    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    slugs = [item["slug"] for item in client.get("/api/v1/agents").json()["items"]]
    assert "legacy-agent" not in slugs
    assert client.get("/api/v1/agents/legacy-agent").status_code == 404
    assert (
        client.patch(
            "/api/v1/agents/legacy-agent", json={"status": "busy"}, headers=headers
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/agents/legacy-agent", headers=headers).status_code == 404

    with session_scope() as db:
        row = db.get(Agent, legacy_id)
        assert row is not None
        assert row.tenant_id is None
        assert row.status == "idle"


# ---------------------------------------------------------------- seed


def _run_seed(database_url: str) -> str:
    env = {**os.environ, "DATABASE_URL": database_url, "DEXTRA_SEED_PASSWORD": PASSWORD}
    result = subprocess.run(
        [sys.executable, str(ROOT / "packages" / "database" / "seeds" / "seed.py")],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def test_seed_does_not_adopt_legacy_null_rows():
    """Seed hanya menyentuh baris miliknya sendiri, dan tetap idempoten."""
    directory = Path(tempfile.mkdtemp(prefix="dextra-seed-"))
    url = f"sqlite+pysqlite:///{(directory / 'seed.db').as_posix()}"

    _run_seed(url)

    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.begin() as conn:
        tenant_id = conn.execute(text("select id from tenants where slug='dextra-demo'")).scalar_one()
        # Baris legacy: tenant NULL, ID dan slug yang akan dipakai seed.
        conn.execute(
            text(
                "insert into agents (id, tenant_id, slug, display_name, agent_type, description, "
                "model_provider, status, is_enabled, created_at, updated_at) values "
                "('agt_legacy_probe', null, 'legacy-probe', 'Legacy Probe', 'assistant', '', "
                "'workbuddy', 'idle', 1, current_timestamp, current_timestamp)"
            )
        )
        conn.execute(
            text(
                "insert into policies (id, tenant_id, slug, title, scope, is_active, created_at, updated_at) "
                "values ('pol_legacy_probe', null, 'legacy-probe', 'Legacy Policy', 'organization', 1, "
                "current_timestamp, current_timestamp)"
            )
        )

    _run_seed(url)

    with engine.connect() as conn:
        legacy_agent = conn.execute(
            text("select tenant_id from agents where id='agt_legacy_probe'")
        ).scalar_one()
        legacy_policy = conn.execute(
            text("select tenant_id from policies where id='pol_legacy_probe'")
        ).scalar_one()
        assert legacy_agent is None, "seed mengambil alih agent legacy"
        assert legacy_policy is None, "seed mengambil alih policy legacy"
        # Seed tetap membuat barisnya sendiri untuk tenant demo.
        assert (
            conn.execute(
                text(
                    "select count(*) from agents where tenant_id=:t and slug='workforce-dispatcher'"
                ),
                {"t": tenant_id},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_seed_is_idempotent():
    directory = Path(tempfile.mkdtemp(prefix="dextra-seed-"))
    url = f"sqlite+pysqlite:///{(directory / 'seed.db').as_posix()}"

    _run_seed(url)
    _run_seed(url)

    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.connect() as conn:
        for table, expected in (
            ("agents", 4),
            ("policies", 1),
            ("work_packages", 1),
            ("tasks", 3),
        ):
            count = conn.execute(text(f"select count(*) from {table}")).scalar_one()
            assert count == expected, f"{table}: {count} != {expected}"
    engine.dispose()


# ---------------------------------------------------------------- integritas relasi


def test_assignment_uniqueness_is_enforced_by_database(client, _clean_throttle):
    """Pemeriksaan di kode bisa kalah balapan; constraint tidak."""
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    _login(client, alpha)
    created = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
    )
    assert created.status_code == 201

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(
                AgentAssignment(
                    id=new_id("asg"),
                    task_id=a["task_id"],
                    agent_id=a["agent_id"],
                    role="executor",
                    tenant_id=alpha["tenant_id"],
                )
            )

    with session_scope() as db:
        rows = db.scalars(
            select(AgentAssignment).where(AgentAssignment.task_id == a["task_id"])
        ).all()
        assert len(rows) == 1


def test_deleting_agent_removes_its_assignments_and_clears_task(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    created = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    assignment_id = created.json()["id"]

    assert client.delete(f"/api/v1/agents/{a['agent_slug']}", headers=headers).status_code == 200

    with session_scope() as db:
        assert db.get(AgentAssignment, assignment_id) is None
        assert db.get(Task, a["task_id"]).assigned_agent_id is None


def test_deleting_task_removes_its_assignments(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    a = _seed(alpha["tenant_id"], slug="alpha-agent")
    _login(client, alpha)
    headers = {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}
    created = client.post(
        f"/api/v1/tasks/{a['task_id']}/assignments",
        json={"agent_slug": "alpha-agent"},
        headers=headers,
    )
    assignment_id = created.json()["id"]

    assert client.delete(f"/api/v1/tasks/{a['task_id']}", headers=headers).status_code == 200

    with session_scope() as db:
        assert db.get(AgentAssignment, assignment_id) is None


def test_security_sessions_still_resolve_member_email(client, _clean_throttle):
    """Pencarian pengguna dipersempit ke tenant, tetapi email tetap terisi."""
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    _login(client, alpha)
    body = client.get("/api/v1/security/sessions").json()
    assert body["items"], "admin seharusnya melihat sesinya sendiri"
    assert all(item["user_email"] == alpha["email"] for item in body["items"])
