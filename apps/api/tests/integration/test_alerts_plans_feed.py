"""Wire plan source ke alerts scan.

TDD RED: belum ada feed plans dari DB nyata. Conversation yang metadata-nya
membawa `intent` adalah work request dari conversation -> harus muncul
sebagai ConversationPlanFact (plan_id/intent/created_at) untuk
DetectInput.plans. Conversation tanpa intent tidak muncul.
Feed tenant-scoped, auth wajib.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.passwords import hash_password
from app.database.base import new_id
from app.database.session import session_scope
from app.models.conversation import Conversation
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


def _make_tenant_user(role_name: str, *, slug_prefix: str = "ap") -> dict:
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"{slug_prefix}-{suffix}", name="AP Test")
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


def _seed_conv(tenant_id: str, metadata: dict, title: str = "C") -> str:
    with session_scope() as db:
        row = Conversation(
            id=new_id("cnv"), tenant_id=tenant_id, title=title, status="active",
            metadata_json=json.dumps(metadata),
        )
        db.add(row)
        db.flush()
        return row.id


def test_alerts_plans_requires_auth(client):
    assert client.get("/api/v1/alerts/plans").status_code == 401


def test_alerts_plans_feed_from_db_and_isolation(client, _clean_throttle):
    alpha = _make_tenant_user("operator", slug_prefix="alpha")
    beta = _make_tenant_user("operator", slug_prefix="beta")
    _seed_conv(alpha["tenant_id"], {"intent": "Kirim laporan ke finance", "plan_id": "pln_alpha_1"})
    _seed_conv(alpha["tenant_id"], {"note": "tanpa intent"})
    _seed_conv(beta["tenant_id"], {"intent": "intent beta"})
    _login(client, alpha)
    r = client.get("/api/v1/alerts/plans")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["plan_id"] == "pln_alpha_1"
    assert item["intent"] == "Kirim laporan ke finance"
    assert item["created_at"]
    blob = json.dumps(items)
    assert "intent beta" not in blob


def test_alerts_plans_service_shape_matches_detect_input(client, _clean_throttle):
    """Fungsi service list_conversation_work_requests mengembalikan bentuk
    persis ConversationPlanFact detect.ts: plan_id, intent, created_at."""
    acct = _make_tenant_user("operator")
    _seed_conv(acct["tenant_id"], {"intent": "Susun rencana contoh"})
    from app.repositories.plans import list_conversation_work_requests

    with session_scope() as db:
        facts = list_conversation_work_requests(db, acct["tenant_id"])
    assert len(facts) == 1
    fact = facts[0]
    assert set(fact) == {"plan_id", "intent", "created_at"}
    assert fact["intent"] == "Susun rencana contoh"
