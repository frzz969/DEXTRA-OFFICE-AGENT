"""Access Management: mutasi anggota/role (POST/PATCH /users, /roles).

TDD RED: hanya GET yang ada. Mutasi butuh capability manage_users,
audit append-only, tenant-scoped. Role sistem tidak boleh diubah.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.audit import AuditEvent
from app.models.identity import User
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"


@pytest.fixture()
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_tenant_user(role_name: str, *, slug_prefix: str = "am") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="AM Test")
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


def _csrf(client) -> dict:
    return {"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""}


def test_create_user_requires_manage_users(client, _clean_throttle):
    acct = _make_tenant_user("operator")
    _login(client, acct)
    r = client.post("/api/v1/users", headers=_csrf(client), json={
        "email": "baru@example.test", "display_name": "Baru", "role": "viewer",
    })
    assert r.status_code == 403


def test_admin_can_add_member_and_change_role_audited(client, _clean_throttle):
    admin = _make_tenant_user("admin")
    suffix = uuid.uuid4().hex[:6]
    _login(client, admin)
    r = client.post("/api/v1/users", headers=_csrf(client), json={
        "email": f"member-{suffix}@example.test", "display_name": "Anggota Baru", "role": "operator",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "operator"
    assert body["tenant_id"] == admin["tenant_id"]
    # duplikat anggota -> 409
    r = client.post("/api/v1/users", headers=_csrf(client), json={
        "email": f"member-{suffix}@example.test", "display_name": "Duplikat", "role": "viewer",
    })
    assert r.status_code == 409, r.text
    # ubah role -> viewer
    r = client.patch(f"/api/v1/users/{body['id']}", headers=_csrf(client), json={"role": "viewer"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "viewer"
    # suspend -> status berubah, akses hilang
    r = client.patch(f"/api/v1/users/{body['id']}", headers=_csrf(client), json={"status": "suspended"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "suspended"
    with session_scope() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.tenant_id == admin["tenant_id"])
        ).all()
        types = {e.event_type for e in events}
        assert "member_added" in types
        assert "member_updated" in types


def test_member_mutation_is_tenant_scoped(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    _login(client, alpha)
    r = client.post("/api/v1/users", headers=_csrf(client), json={
        "email": f"lintas-{uuid.uuid4().hex[:6]}@example.test",
        "display_name": "Lintas", "role": "viewer",
    })
    new_id_ = r.json()["id"]
    client.post("/api/v1/auth/logout", headers=_csrf(client))
    _login(client, beta)
    # beta tidak bisa menyentuh anggota alpha: 404 (bukan konfirmasi keberadaan)
    assert client.patch(f"/api/v1/users/{new_id_}", headers=_csrf(client), json={"role": "admin"}).status_code == 404


def test_custom_role_create_and_system_role_immutable(client, _clean_throttle):
    admin = _make_tenant_user("admin")
    name = f"custom-{uuid.uuid4().hex[:6]}"
    _login(client, admin)
    r = client.post("/api/v1/roles", headers=_csrf(client), json={
        "name": name, "description": "Role kustom demo", "capabilities": ["view_own", "view_all"],
    })
    assert r.status_code == 201, r.text
    assert sorted(r.json()["capabilities"]) == ["view_all", "view_own"]
    assert r.json()["is_system"] is False
    # capability tidak dikenal -> 422
    r = client.post("/api/v1/roles", headers=_csrf(client), json={
        "name": f"bad-{uuid.uuid4().hex[:6]}", "capabilities": ["delete_everything"],
    })
    assert r.status_code == 422, r.text
    # role sistem tidak boleh diubah
    roles = client.get("/api/v1/roles").json()["items"]
    system_role = next(x for x in roles if x["is_system"])
    r = client.patch(f"/api/v1/roles/{system_role['id']}", headers=_csrf(client), json={"description": "ubah"})
    assert r.status_code in (403, 409), r.text


# --- GET /permissions untuk token demo (item 4) ------------------------------

def test_permissions_available_for_legacy_demo_token(client, ops_headers):
    """Token demo (ops) boleh membaca /permissions: 200, bukan 403.
    Capability-nya memang benar: endpoint ini introspeksi, bukan data tenant."""
    r = client.get("/api/v1/permissions", headers=ops_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "capabilities" in body
    assert "view_audit" in body["capabilities"]
    # Tetapi /users tetap 403 untuk token demo (manage_users tidak ada di scope ops)
    assert client.get("/api/v1/users", headers=ops_headers).status_code == 403
