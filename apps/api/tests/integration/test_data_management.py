"""Data Management: export tenant (JSON) + seed/reset berguard.

TDD RED: endpoint belum ada. Export: permission + audit + tenant-scoped,
tanpa secret. Seed: idempotent, capability admin. Reset: hanya scope
conversations, konfirmasi = slug tenant, capability admin, audit.
Tidak ada endpoint yang menghapus governance/audit/users.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.audit import AuditEvent
from app.models.conversation import Conversation, ConversationMessage
from app.models.identity import User
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


def _make_tenant_user(role_name: str, *, slug_prefix: str = "dm") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="DM Test")
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


def _seed_conversation(tenant_id: str, *, intent: str, title: str = "C") -> str:
    with session_scope() as db:
        row = Conversation(
            id=new_id("cnv"), tenant_id=tenant_id, title=title, status="active",
            metadata_json=json.dumps({"intent": intent}),
        )
        db.add(row)
        db.flush()
        db.add(ConversationMessage(
            id=new_id("msg"), tenant_id=tenant_id, conversation_id=row.id,
            role="user", content="halo demo",
        ))
        return row.id


# --- export -----------------------------------------------------------------

def test_export_requires_auth(client):
    assert client.get("/api/v1/data/export").status_code == 401


def test_export_requires_view_audit(client, _clean_throttle):
    acct = _make_tenant_user("operator")
    _login(client, acct)
    assert client.get("/api/v1/data/export").status_code == 403


def test_export_tenant_scoped_and_audited(client, _clean_throttle):
    alpha = _make_tenant_user("admin", slug_prefix="alpha")
    beta = _make_tenant_user("admin", slug_prefix="beta")
    _seed_conversation(alpha["tenant_id"], intent="intent alpha")
    _seed_conversation(beta["tenant_id"], intent="intent beta")
    _login(client, alpha)
    r = client.get("/api/v1/data/export")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == alpha["tenant_id"]
    assert body["tenant_slug"] == alpha["tenant_slug"]
    convs = body["conversations"]
    assert len(convs) == 1
    assert convs[0]["metadata"]["intent"] == "intent alpha"
    blob = json.dumps(body)
    assert "intent beta" not in blob
    assert "password_hash" not in blob
    assert "mfa_secret" not in blob
    with session_scope() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.tenant_id == alpha["tenant_id"])
        ).all()
        assert any(e.event_type == "data_exported" for e in events)


# --- seed -------------------------------------------------------------------

def test_seed_requires_admin_and_is_idempotent(client, _clean_throttle):
    op = _make_tenant_user("operator")
    _login(client, op)
    assert client.post("/api/v1/data/seed", headers=_csrf(client), json={}).status_code == 403
    client.post("/api/v1/auth/logout", headers=_csrf(client))

    admin = _make_tenant_user("admin")
    _login(client, admin)
    r1 = client.post("/api/v1/data/seed", headers=_csrf(client), json={})
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/v1/data/seed", headers=_csrf(client), json={})
    assert r2.status_code == 200, r2.text
    assert r1.json()["conversation_id"] == r2.json()["conversation_id"]
    with session_scope() as db:
        rows = db.scalars(
            select(Conversation).where(Conversation.tenant_id == admin["tenant_id"])
        ).all()
        assert len(rows) == 1
        assert json.loads(rows[0].metadata_json).get("seed") == "demo"


# --- reset ------------------------------------------------------------------

def test_reset_guard_confirmation_and_scope(client, _clean_throttle):
    admin = _make_tenant_user("admin")
    _login(client, admin)
    # konfirmasi salah -> ditolak, data utuh
    r = client.post(
        "/api/v1/data/reset", headers=_csrf(client),
        json={"confirm": "salah", "scope": "conversations"},
    )
    assert r.status_code == 422, r.text
    # scope berbahaya tidak didukung
    r = client.post(
        "/api/v1/data/reset", headers=_csrf(client),
        json={"confirm": admin["tenant_slug"], "scope": "all"},
    )
    assert r.status_code == 422, r.text


def test_reset_only_clears_conversations_and_audits(client, _clean_throttle):
    admin = _make_tenant_user("admin")
    _seed_conversation(admin["tenant_id"], intent="intent hapus")
    _login(client, admin)
    r = client.post(
        "/api/v1/data/reset", headers=_csrf(client),
        json={"confirm": admin["tenant_slug"], "scope": "conversations"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted_conversations"] == 1
    assert body["deleted_messages"] == 1
    with session_scope() as db:
        assert db.scalars(
            select(Conversation).where(Conversation.tenant_id == admin["tenant_id"])
        ).all() == []
        # tenant + membership + user tetap ada (reset tidak menyentuh identitas)
        assert db.get(Tenant, admin["tenant_id"]) is not None
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.tenant_id == admin["tenant_id"])
        ).all()
        assert any(e.event_type == "data_reset" for e in events)
