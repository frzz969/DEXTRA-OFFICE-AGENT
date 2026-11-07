"""Demo-ready endpoints: integrations/settings/policy-versions/wp-detail/analytics/search.

TDD RED: ditulis sebelum endpoint ada. Semua endpoint harus auth + tenant
isolation + permission sesuai pola router existing.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id, utcnow
from app.database.session import session_scope
from app.models.audit import AuditEvent
from app.models.execution import Execution
from app.models.governance import Policy, PolicyVersion
from app.models.identity import User
from app.models.tasks import Task, WorkPackage
from app.models.tenant import Tenant
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"


@pytest.fixture()
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_tenant_user(role_name: str, *, slug_prefix: str = "demo") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="Demo Test")
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
    r = client.post("/api/v1/auth/login", json={"email": account["email"], "password": PASSWORD})
    assert r.status_code == 200, r.text


def _logout(client) -> None:
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""})


def _csrf(client) -> dict:
    return {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}


def _seed_wp(tenant_id: str, title: str = "Paket Demo") -> dict:
    with session_scope() as db:
        wp = WorkPackage(id=new_id("wpg"), tenant_id=tenant_id, title=title, status="draft")
        db.add(wp)
        db.flush()
        task = Task(id=new_id("tsk"), tenant_id=tenant_id, work_package_id=wp.id, title="Tugas Demo", status="todo")
        db.add(task)
        db.flush()
        return {"wp_id": wp.id, "task_id": task.id}


def _seed_policy(tenant_id: str, slug: str = "demo-policy") -> dict:
    with session_scope() as db:
        pol = Policy(id=new_id("pol"), tenant_id=tenant_id, slug=slug, title="Policy Demo", scope="organization")
        db.add(pol)
        db.flush()
        db.add(PolicyVersion(id=new_id("pov"), policy_id=pol.id, version=1, rules_json="{}", change_note="awal"))
        db.flush()
        return {"policy_id": pol.id, "slug": slug}


def _seed_execution(tenant_id: str, *, status: str, when: datetime) -> str:
    eid = new_id("exe")
    with session_scope() as db:
        db.add(
            Execution(
                id=eid, plan_id="pln_demo", mandate_id="mnd_demo", tenant_id=tenant_id,
                action_id="act_demo", status=status, idempotency_key=f"{eid}:k",
                started_at=when, finished_at=when, duration_ms=5,
            )
        )
        db.flush()
        return eid


# --- integrations/status -------------------------------------------------

def test_integrations_status_requires_auth(client):
    assert client.get("/api/v1/integrations/status").status_code == 401


def test_integrations_status_is_honest_no_fake_badges(client, _clean_throttle, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    acct = _make_tenant_user("operator")
    _login(client, acct)
    r = client.get("/api/v1/integrations/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body or "connectors" in body
    items = {i["name"]: i for i in (body.get("items") or body.get("connectors"))}
    assert set(items) == {"telegram", "whatsapp", "email", "calendar", "documents"}
    # WhatsApp/documents: tidak ada adapter -> tidak boleh claimed terhubung
    assert items["whatsapp"]["configured"] is False
    assert items["whatsapp"]["adapter"] in (None, "")
    assert items["documents"]["configured"] is False
    # Email/calendar: adapter outbox lokal terdaftar nyata
    assert items["email"]["adapter"] == "outbox"
    assert items["calendar"]["adapter"] == "outbox"
    # Telegram: config dari env nyata, bukan badge palsu
    assert items["telegram"]["configured"] is False
    # tidak membocorkan nilai secret
    assert "bot-token-secret" not in json.dumps(body)
    assert "secret" not in json.dumps(body).lower() or "configured" in json.dumps(body)


def test_integrations_status_reflects_env(client, _clean_throttle, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token-secret-value")
    acct = _make_tenant_user("operator")
    _login(client, acct)
    body = client.get("/api/v1/integrations/status").json()
    items = {i["name"]: i for i in (body.get("items") or body.get("connectors"))}
    assert items["telegram"]["configured"] is True
    assert "bot-token-secret-value" not in json.dumps(body)


# --- settings ------------------------------------------------------------

def test_settings_requires_auth_and_tenant(client, ops_headers):
    assert client.get("/api/v1/settings").status_code == 401
    # tenantless legacy -> 400 (require_tenant)
    r = client.get("/api/v1/settings", headers=ops_headers)
    assert r.status_code in (400, 401, 403, 404)


def test_settings_roundtrip_and_tenant_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    # seed beta settings directly
    with session_scope() as db:
        t = db.get(Tenant, beta["tenant_id"])
        t.settings_json = json.dumps({"org_name": "Beta"})

    _login(client, alpha)
    r = client.get("/api/v1/settings")
    assert r.status_code == 200, r.text
    assert r.json()["tenant_id"] == alpha["tenant_id"]
    assert r.json()["settings"] == {}
    # PATCH merge
    r = client.patch("/api/v1/settings", headers=_csrf(client), json={"settings": {"org_name": "Alpha", "theme": "dark"}})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["org_name"] == "Alpha"
    r = client.get("/api/v1/settings")
    assert r.json()["settings"] == {"org_name": "Alpha", "theme": "dark"}
    # audit event ter-append
    with session_scope() as db:
        events = db.scalars(select(AuditEvent).where(AuditEvent.tenant_id == alpha["tenant_id"])).all()
        assert any(e.event_type == "settings_updated" for e in events)
    _logout(client)
    # beta tidak melihat settings alpha
    _login(client, beta)
    r = client.get("/api/v1/settings")
    assert r.json()["settings"] == {"org_name": "Beta"}


def test_settings_patch_requires_manage_integrations(client, _clean_throttle):
    acct = _make_tenant_user("operator")
    with session_scope() as db:
        t = db.get(Tenant, acct["tenant_id"])
        t.settings_json = json.dumps({"org_name": "Asli"})
    _login(client, acct)
    r = client.patch("/api/v1/settings", headers=_csrf(client), json={"settings": {"org_name": "Ubah"}})
    assert r.status_code == 403
    with session_scope() as db:
        assert json.loads(db.get(Tenant, acct["tenant_id"]).settings_json) == {"org_name": "Asli"}


# --- policies versions ---------------------------------------------------

def test_policy_versions_requires_auth(client):
    assert client.get("/api/v1/policies/demo-policy/versions").status_code == 401


def test_policy_versions_list_and_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    seeded = _seed_policy(alpha["tenant_id"])
    _login(client, alpha)
    r = client.get(f"/api/v1/policies/{seeded['slug']}/versions")
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["version"] == 1
    _logout(client)
    _login(client, beta)
    assert client.get(f"/api/v1/policies/{seeded['slug']}/versions").status_code == 404


# --- work-packages detail ------------------------------------------------

def test_work_package_detail_requires_auth(client):
    assert client.get("/api/v1/work-packages/wpg_x").status_code == 401


def test_work_package_detail_includes_tasks_and_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    seeded = _seed_wp(alpha["tenant_id"])
    _login(client, alpha)
    r = client.get(f"/api/v1/work-packages/{seeded['wp_id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == seeded["wp_id"]
    assert any(t["id"] == seeded["task_id"] for t in body["tasks"])
    _logout(client)
    _login(client, beta)
    assert client.get(f"/api/v1/work-packages/{seeded['wp_id']}").status_code == 404


# --- analytics/daily -----------------------------------------------------

def test_analytics_daily_requires_auth(client):
    assert client.get("/api/v1/analytics/daily").status_code == 401


def test_analytics_daily_7_days_and_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    now = datetime.now(timezone.utc)
    _seed_execution(alpha["tenant_id"], status="succeeded", when=now)
    _seed_execution(alpha["tenant_id"], status="failed", when=now)
    _seed_execution(beta["tenant_id"], status="failed", when=now)
    _login(client, alpha)
    r = client.get("/api/v1/analytics/daily")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 7
    today = body["items"][-1]
    assert today["date"] == now.date().isoformat()
    assert today["total"] == 2
    assert today["succeeded"] == 1
    assert today["failed"] == 1
    assert today["blocked"] == 0
    # total 7 hari tidak mencakup tenant lain
    assert sum(d["total"] for d in body["items"]) == 2


# --- search --------------------------------------------------------------

def test_search_requires_auth(client):
    assert client.get("/api/v1/search", params={"q": "demo"}).status_code == 401


def test_search_cross_entity_and_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    seeded = _seed_wp(alpha["tenant_id"], title="Paket UnicornZebra")
    _seed_wp(beta["tenant_id"], title="Paket UnicornZebra")
    _login(client, alpha)
    r = client.get("/api/v1/search", params={"q": "UnicornZebra"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    ids = {i["id"] for i in body["items"]}
    assert seeded["wp_id"] in ids
    # tidak bocor tenant lain: hanya 1 hasil wp untuk alpha
    wp_hits = [i for i in body["items"] if i["entity"] == "work_package"]
    assert len(wp_hits) == 1
    # q kosong -> 422
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422
