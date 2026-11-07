"""API token, identitas mesin, dan Security Center.

Tes ini memakai jalur HTTP yang sama dengan dashboard: login sungguhan, cookie
sungguhan, token yang benar-benar diterbitkan. Tidak ada token yang dikarang di
dalam tes — kalau diterbitkan lewat API, ia harus bisa dipakai; kalau dicabut,
ia harus langsung mati.
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
            tenant = tenant_repo.create_tenant(db, slug=f"sec-{suffix}", name="Security Test")
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


def _login(client, account) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": PASSWORD}
    )
    assert response.status_code == 200, response.text


def _csrf(client) -> str:
    return client.cookies.get("dextra_csrf") or ""


def _post(client, url: str, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["X-CSRF-Token"] = _csrf(client)
    return client.post(url, headers=headers, **kwargs)


# --- P10: API token ---------------------------------------------------------


def test_create_token_returns_secret_once(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client,
        "/api/v1/tokens",
        json={"name": "cli", "scopes": ["view_own", "view_all"], "expires_in_days": 30},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["token"].startswith("dx_")
    assert body["prefix"] in body["token"]
    assert body["expires_at"]

    listing = client.get("/api/v1/tokens").json()["items"]
    assert listing
    assert all("token" not in item for item in listing)
    assert all(item["id"] != body["id"] or "token" not in item for item in listing)


def test_issued_token_works_as_bearer(client):
    account = _make_user("admin")
    _login(client, account)
    token = _post(
        client, "/api/v1/tokens", json={"name": "cli", "scopes": ["view_own", "view_all"]}
    ).json()["token"]

    fresh = client.__class__(client.app)
    response = fresh.get("/api/v1/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_token_scope_cannot_exceed_owner(client):
    account = _make_user("viewer")
    _login(client, account)
    response = _post(
        client, "/api/v1/tokens", json={"name": "naik", "scopes": ["view_own", "approve"]}
    )
    assert response.status_code == 422
    assert "melebihi wewenang" in response.json()["detail"]


def test_revoked_token_stops_working_immediately(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client, "/api/v1/tokens", json={"name": "sementara", "scopes": ["view_all"]}
    ).json()
    bearer = {"Authorization": f"Bearer {created['token']}"}
    fresh = client.__class__(client.app)
    assert fresh.get("/api/v1/overview", headers=bearer).status_code == 200

    revoked = _post(client, f"/api/v1/tokens/{created['id']}/revoke", json={"reason": "uji"})
    assert revoked.status_code == 200
    assert fresh.get("/api/v1/overview", headers=bearer).status_code == 401


def test_rotation_revokes_old_and_returns_new(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client, "/api/v1/tokens", json={"name": "rotasi", "scopes": ["view_all"]}
    ).json()
    rotated = _post(client, f"/api/v1/tokens/{created['id']}/rotate", json={})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["token"] != created["token"]

    fresh = client.__class__(client.app)
    assert (
        fresh.get(
            "/api/v1/overview", headers={"Authorization": f"Bearer {created['token']}"}
        ).status_code
        == 401
    )
    assert (
        fresh.get(
            "/api/v1/overview", headers={"Authorization": f"Bearer {rotated.json()['token']}"}
        ).status_code
        == 200
    )


def test_token_cannot_mint_another_token(client):
    """Token yang bocor tidak boleh bisa mencetak penggantinya."""
    account = _make_user("admin")
    _login(client, account)
    token = _post(
        client, "/api/v1/tokens", json={"name": "cli", "scopes": ["view_own", "manage_integrations"]}
    ).json()["token"]
    fresh = client.__class__(client.app)
    response = fresh.post(
        "/api/v1/tokens",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "turunan", "scopes": ["view_own"]},
    )
    assert response.status_code == 403


def test_non_admin_sees_only_own_tokens(client):
    admin = _make_user("admin")
    _login(client, admin)
    _post(client, "/api/v1/tokens", json={"name": "milik-admin", "scopes": ["view_all"]})
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": _csrf(client)})

    viewer = _make_user("viewer")
    _login(client, viewer)
    items = client.get("/api/v1/tokens").json()["items"]
    assert items == []


def test_token_creation_requires_session(client):
    account = _make_user("admin")
    _login(client, account)
    token = _post(client, "/api/v1/tokens", json={"name": "x", "scopes": ["view_all"]}).json()[
        "token"
    ]
    fresh = client.__class__(client.app)
    response = fresh.post(
        "/api/v1/tokens",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "y", "scopes": ["view_all"]},
    )
    assert response.status_code == 403


def test_token_creation_requires_csrf(client):
    account = _make_user("admin")
    _login(client, account)
    response = client.post("/api/v1/tokens", json={"name": "tanpa-csrf", "scopes": ["view_own"]})
    assert response.status_code == 403


# --- P11: service identity --------------------------------------------------


def test_admin_creates_service_account_and_issues_its_token(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client,
        "/api/v1/service-accounts",
        json={
            "name": "office-agent-worker",
            "kind": "worker",
            "description": "Worker Office Agent",
            "scopes": ["view_own", "view_all", "create_request"],
        },
    )
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]

    token = _post(
        client,
        "/api/v1/tokens",
        json={"name": "worker-token", "scopes": ["view_own"], "service_account_id": account_id},
    )
    assert token.status_code == 201, token.text

    fresh = client.__class__(client.app)
    response = fresh.get(
        "/api/v1/auth/session", headers={"Authorization": f"Bearer {token.json()['token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["auth_kind"] == "service_token"
    assert body["principal"]["kind"] == "service"
    assert body["principal"]["principal_id"] == account_id
    # Identitas mesin tidak punya email dan tidak memakai akun manusia.
    assert body["principal"].get("email") is None


def test_service_token_scope_is_limited_by_account(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client,
        "/api/v1/service-accounts",
        json={"name": "terbatas", "kind": "mcp", "scopes": ["view_own"]},
    ).json()
    response = _post(
        client,
        "/api/v1/tokens",
        json={
            "name": "lebih",
            "scopes": ["view_own", "approve"],
            "service_account_id": created["id"],
        },
    )
    assert response.status_code == 422


def test_non_admin_cannot_manage_service_accounts(client):
    account = _make_user("approver")
    _login(client, account)
    assert client.get("/api/v1/service-accounts").status_code == 403
    assert _post(
        client, "/api/v1/service-accounts", json={"name": "x", "kind": "worker", "scopes": ["view_own"]}
    ).status_code == 403


def test_revoking_service_account_kills_its_tokens(client):
    account = _make_user("admin")
    _login(client, account)
    created = _post(
        client,
        "/api/v1/service-accounts",
        json={"name": "worker-mati", "kind": "worker", "scopes": ["view_own", "view_all"]},
    ).json()
    token = _post(
        client,
        "/api/v1/tokens",
        json={"name": "t", "scopes": ["view_all"], "service_account_id": created["id"]},
    ).json()["token"]

    fresh = client.__class__(client.app)
    assert fresh.get("/api/v1/overview", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    revoked = _post(
        client, f"/api/v1/service-accounts/{created['id']}/revoke", json={"reason": "selesai"}
    )
    assert revoked.status_code == 200
    assert revoked.json()["tokens_revoked"] == 1
    assert fresh.get("/api/v1/overview", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_service_accounts_are_tenant_isolated(client):
    first = _make_user("admin")
    _login(client, first)
    _post(
        client,
        "/api/v1/service-accounts",
        json={"name": "milik-pertama", "kind": "worker", "scopes": ["view_own"]},
    )
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": _csrf(client)})

    second = _make_user("admin")
    _login(client, second)
    items = client.get("/api/v1/service-accounts").json()["items"]
    assert all(item["name"] != "milik-pertama" for item in items)


# --- P12: Security Center ---------------------------------------------------


def test_overview_reports_zero_for_new_tenant(client):
    account = _make_user("admin")
    _login(client, account)
    payload = client.get("/api/v1/security/overview").json()
    assert payload["tokens"]["total"] == 0
    assert payload["service_accounts"]["active"] == 0
    assert payload["members"]["active"] == 1
    # Login yang baru saja terjadi tercatat, bukan nol palsu.
    assert payload["last_24h"]["events_by_type"].get("login_succeeded", 0) >= 1


def test_overview_counts_tokens_and_sessions(client):
    account = _make_user("admin")
    _login(client, account)
    _post(client, "/api/v1/tokens", json={"name": "a", "scopes": ["view_all"]})
    payload = client.get("/api/v1/security/overview").json()
    assert payload["tokens"]["active"] == 1
    assert payload["sessions"]["active"] >= 1


def test_access_denied_is_recorded(client):
    admin = _make_user("admin")
    viewer = _make_user("viewer", tenant_slug=admin["tenant_slug"])

    viewer_client = client.__class__(client.app)
    _login(viewer_client, viewer)
    assert viewer_client.get("/api/v1/audit-events").status_code == 403

    _login(client, admin)
    events = client.get("/api/v1/security/events", params={"event_type": "access_denied"}).json()
    assert events["total"] >= 1
    assert events["items"][0]["detail"]


def test_login_history_contains_failure(client):
    account = _make_user("approver")
    client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": "salah-sekali-lagi"}
    )
    _login(client, account)
    history = client.get("/api/v1/security/login-history").json()["items"]
    types = {item["event_type"] for item in history}
    assert "login_failed" in types
    assert "login_succeeded" in types


def test_admin_sees_tenant_sessions_and_can_revoke(client):
    admin = _make_user("admin")
    member = _make_user("viewer", tenant_slug=admin["tenant_slug"])

    other_client = client.__class__(client.app)
    _login(other_client, member)
    _login(client, admin)

    sessions = client.get("/api/v1/security/sessions").json()["items"]
    target = next(item for item in sessions if item["user_id"] == member["user_id"])
    revoked = _post(client, f"/api/v1/security/sessions/{target['id']}/revoke")
    assert revoked.status_code == 200
    assert other_client.get("/api/v1/overview").status_code == 401


def test_non_admin_cannot_read_tenant_sessions(client):
    account = _make_user("auditor")
    _login(client, account)
    assert client.get("/api/v1/security/sessions").status_code == 403
    # Auditor tetap boleh membaca peristiwa.
    assert client.get("/api/v1/security/events").status_code == 200


def test_token_inventory_never_contains_secret(client):
    account = _make_user("admin")
    _login(client, account)
    secret = _post(client, "/api/v1/tokens", json={"name": "inv", "scopes": ["view_all"]}).json()[
        "token"
    ]
    inventory = client.get("/api/v1/security/tokens").json()["items"]
    assert inventory
    assert all("token" not in item for item in inventory)
    assert secret not in str(inventory)


def test_mfa_status_counts_real_rows(client):
    account = _make_user("admin")
    _login(client, account)
    payload = client.get("/api/v1/security/mfa-status").json()
    assert payload["total"] == 1
    assert payload["enabled"] == 0
    assert payload["items"][0]["email"] == account["email"]


def test_security_center_is_tenant_isolated(client):
    first = _make_user("admin")
    _login(client, first)
    _post(client, "/api/v1/tokens", json={"name": "rahasia-pertama", "scopes": ["view_all"]})
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": _csrf(client)})

    second = _make_user("admin")
    _login(client, second)
    inventory = client.get("/api/v1/security/tokens").json()["items"]
    assert inventory == []
