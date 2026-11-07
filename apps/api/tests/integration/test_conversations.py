"""Integrasi percakapan dan pesan.

Yang dibuktikan: percakapan tersimpan per tenant, urutan pesan stabil, peran
pesan divalidasi, dan percakapan tenant lain tidak bisa dibaca maupun ditulisi
(404, bukan 403). Audit mencatat pembuatan percakapan dan penambahan pesan.
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


@pytest.fixture(autouse=True)
def _clean_throttle(app):
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


def _make_user(role_name: str = "admin", *, tenant_slug: str | None = None) -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        if tenant_slug:
            tenant = tenant_repo.get_tenant_by_slug(db, tenant_slug)
        else:
            tenant = tenant_repo.create_tenant(
                db, slug=f"conv-{suffix}", name="Conversation Test"
            )
        role = tenant_repo.ensure_system_role(db, role_name)
        user = User(
            id=new_id("usr"),
            email=f"conv-{role_name}-{suffix}@example.test",
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


def _login(client, account) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": PASSWORD}
    )
    assert response.status_code == 200, response.text


def _post(client, url: str, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["X-CSRF-Token"] = client.cookies.get("dextra_csrf") or ""
    return client.post(url, headers=headers, **kwargs)


def _create_conversation(client, **payload):
    response = _post(client, "/api/v1/conversations", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_conversation_create_list_and_get(client):
    account = _make_user()
    _login(client, account)

    created = _create_conversation(client, title="Rencana Q4", metadata={"source": "test"})
    assert created["id"].startswith("cnv_")
    assert created["title"] == "Rencana Q4"
    assert created["status"] == "active"
    assert created["metadata"] == {"source": "test"}

    listed = client.get("/api/v1/conversations")
    assert listed.status_code == 200, listed.text
    ids = [item["id"] for item in listed.json()["items"]]
    assert created["id"] in ids

    detail = client.get(f"/api/v1/conversations/{created['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == created["id"]


def test_conversation_is_invisible_to_other_tenant(client):
    owner = _make_user()
    _login(client, owner)
    conversation = _create_conversation(client, title="Milik tenant A")

    other = _make_user()
    _login(client, other)

    assert (
        client.get(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    )
    assert client.get("/api/v1/conversations").json()["items"] == []

    appended = _post(
        client,
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"role": "user", "content": "menyusup"},
    )
    assert appended.status_code == 404

    # Pesan tidak tertulis meski percobaan penulisan ditolak.
    _login(client, owner)
    messages = client.get(f"/api/v1/conversations/{conversation['id']}/messages")
    assert messages.status_code == 200
    assert messages.json()["items"] == []


def test_anonymous_access_is_rejected(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        assert client.get("/api/v1/conversations").status_code >= 400
        response = client.post("/api/v1/conversations", json={"title": "x"})
        assert 400 <= response.status_code < 500


def test_message_ordering_and_role_validation(client):
    account = _make_user()
    _login(client, account)
    conversation = _create_conversation(client, title="Urutan pesan")

    for role, content in (
        ("user", "pertama"),
        ("assistant", "kedua"),
        ("user", "ketiga"),
    ):
        response = _post(
            client,
            f"/api/v1/conversations/{conversation['id']}/messages",
            json={"role": role, "content": content},
        )
        assert response.status_code == 201, response.text
        assert response.json()["id"].startswith("msg_")

    messages = client.get(f"/api/v1/conversations/{conversation['id']}/messages")
    assert messages.status_code == 200, messages.text
    assert [item["content"] for item in messages.json()["items"]] == [
        "pertama",
        "kedua",
        "ketiga",
    ]

    invalid = _post(
        client,
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"role": "root", "content": "tidak boleh"},
    )
    assert invalid.status_code == 422


def test_audit_events_are_written_for_conversation_and_message(client):
    account = _make_user()
    _login(client, account)
    conversation = _create_conversation(client, title="Audit")

    _post(
        client,
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"role": "user", "content": "halo"},
    )

    with session_scope() as db:
        events = db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.event_type.in_(
                    ("conversation_created", "conversation_message_appended")
                ),
                AuditEvent.tenant_id == account["tenant_id"],
            )
            .order_by(AuditEvent.seq.asc())
        ).all()
        assert [event.event_type for event in events] == [
            "conversation_created",
            "conversation_message_appended",
        ]
        assert all(event.actor == "conversations" for event in events)
        for event in events:
            detail = event.detail_json
            for forbidden in ("body", "email", "phone", "address"):
                assert forbidden not in detail
