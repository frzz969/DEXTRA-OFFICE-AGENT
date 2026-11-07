"""RBAC dan isolasi tenant, diuji lewat HTTP.

Yang dibuktikan di sini bukan "tombolnya disembunyikan", melainkan bahwa server
menolak. Setiap tes memakai identitas yang benar-benar login, bukan header yang
dikarang, supaya hasilnya mencerminkan jalur yang dipakai dashboard.
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


def _approve(client, *, plan_id: str, action_id: str = "act_1", decision: str = "approved"):
    return client.post(
        "/api/v1/approvals",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={
            "plan_id": plan_id,
            "action_id": action_id,
            "action_type": "send_email",
            "params": {"to": "budi@example.test"},
            "approver_id": "apa-saja",
            "decision": decision,
        },
    )


# --- RBAC -------------------------------------------------------------------


def test_viewer_cannot_approve(client, _clean_throttle):
    account = _make_tenant_user("viewer")
    _login(client, account)
    response = _approve(client, plan_id="pln_viewer")
    assert response.status_code == 403


def test_viewer_cannot_read_audit(client, _clean_throttle):
    account = _make_tenant_user("viewer")
    _login(client, account)
    assert client.get("/api/v1/audit-events").status_code == 403


def test_operator_can_create_but_not_approve(client, _clean_throttle):
    account = _make_tenant_user("operator")
    _login(client, account)
    assert _approve(client, plan_id="pln_operator").status_code == 403
    # Operator tetap boleh melihat pekerjaan tenant-nya.
    assert client.get("/api/v1/mandates").status_code == 200


def test_approver_can_approve(client, _clean_throttle):
    account = _make_tenant_user("approver")
    _login(client, account)
    response = _approve(client, plan_id=f"pln_ok_{uuid.uuid4().hex[:6]}")
    assert response.status_code == 201, response.text
    assert response.json()["mandate_id"]


def test_auditor_can_read_audit_but_not_execute(client, _clean_throttle):
    account = _make_tenant_user("auditor")
    _login(client, account)
    assert client.get("/api/v1/audit-events").status_code == 200
    response = client.post(
        "/api/v1/executions",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf") or ""},
        json={"mandate_id": "mnd_x", "action_id": "act_1", "action_type": "send_email"},
    )
    assert response.status_code == 403


def test_permissions_reports_real_role(client, _clean_throttle):
    account = _make_tenant_user("auditor")
    _login(client, account)
    payload = client.get("/api/v1/permissions").json()
    assert payload["scope"] == "user"
    assert payload["principal"]["role"] == "auditor"
    assert "view_audit" in payload["capabilities"]
    assert "execute" not in payload["capabilities"]


def test_suspended_membership_loses_access_immediately(client, _clean_throttle):
    account = _make_tenant_user("approver")
    _login(client, account)
    assert client.get("/api/v1/mandates").status_code == 200
    with session_scope() as db:
        membership = tenant_repo.get_membership(
            db, tenant_id=account["tenant_id"], user_id=account["user_id"]
        )
        membership.status = "suspended"
    assert client.get("/api/v1/mandates").status_code == 401


def test_unknown_capability_is_rejected_at_definition():
    """Default-deny juga berlaku untuk salah ketik di kode."""
    from app.core.security import require_capability

    with pytest.raises(ValueError):
        require_capability("delete_everything")


# --- Isolasi tenant ---------------------------------------------------------


def test_tenant_cannot_read_other_tenants_mandate(client, _clean_throttle):
    owner = _make_tenant_user("approver", slug_prefix="alpha")
    other = _make_tenant_user("approver", slug_prefix="beta")

    _login(client, owner)
    created = _approve(client, plan_id=f"pln_iso_{uuid.uuid4().hex[:6]}")
    mandate_id = created.json()["mandate_id"]
    assert client.get(f"/api/v1/mandates/{mandate_id}").status_code == 200
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    _login(client, other)
    # 404, bukan 403: keberadaan mandate tenant lain tidak dikonfirmasi.
    assert client.get(f"/api/v1/mandates/{mandate_id}").status_code == 404
    listed = client.get("/api/v1/mandates").json()["items"]
    assert all(item["id"] != mandate_id for item in listed)


def test_tenant_cannot_revoke_other_tenants_mandate(client, _clean_throttle):
    owner = _make_tenant_user("approver", slug_prefix="alpha")
    other = _make_tenant_user("approver", slug_prefix="beta")

    _login(client, owner)
    mandate_id = _approve(client, plan_id=f"pln_rev_{uuid.uuid4().hex[:6]}").json()["mandate_id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    _login(client, other)
    response = client.post(
        f"/api/v1/mandates/{mandate_id}/revoke",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")},
        json={"reason": "lintas tenant"},
    )
    assert response.status_code == 404


def test_tenant_cannot_execute_other_tenants_mandate(client, _clean_throttle):
    owner = _make_tenant_user("approver", slug_prefix="alpha")
    other = _make_tenant_user("approver", slug_prefix="beta")

    _login(client, owner)
    mandate_id = _approve(
        client, plan_id=f"pln_exec_{uuid.uuid4().hex[:6]}", action_id="act_exec"
    ).json()["mandate_id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    _login(client, other)
    response = client.post(
        "/api/v1/executions",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")},
        json={
            "mandate_id": mandate_id,
            "action_id": "act_exec",
            "action_type": "send_email",
            "params": {"to": "budi@example.test"},
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "MANDATE_NOT_FOUND"


def test_approval_is_attributed_to_caller_tenant(client, _clean_throttle):
    account = _make_tenant_user("approver")
    _login(client, account)
    _approve(client, plan_id=f"pln_attr_{uuid.uuid4().hex[:6]}")
    with session_scope() as db:
        from app.models.governance import Approval

        row = db.scalars(
            select(Approval).order_by(Approval.created_at.desc()).limit(1)
        ).one()
        assert row.tenant_id == account["tenant_id"]


def test_tenant_lists_are_isolated_for_executions(client, _clean_throttle):
    owner = _make_tenant_user("approver", slug_prefix="alpha")
    other = _make_tenant_user("approver", slug_prefix="beta")

    _login(client, owner)
    mandate_id = _approve(
        client, plan_id=f"pln_run_{uuid.uuid4().hex[:6]}", action_id="act_run"
    ).json()["mandate_id"]
    executed = client.post(
        "/api/v1/executions",
        headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")},
        json={
            "mandate_id": mandate_id,
            "action_id": "act_run",
            "action_type": "send_email",
            "params": {"to": "budi@example.test"},
        },
    )
    assert executed.status_code == 201
    execution_id = executed.json()["id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    _login(client, other)
    ids = [item["id"] for item in client.get("/api/v1/executions").json()["items"]]
    assert execution_id not in ids


def test_unbound_legacy_token_cannot_reach_tenant_data(client, ops_headers, _clean_throttle, monkeypatch):
    """Tanpa `DEXTRA_LEGACY_TENANT`, token gateway gagal-tertutup.

    Dulu token ini bisa membaca mandate tenant mana pun karena `tenant_id`
    kosong dan pemeriksaan tenant dilewati. Sekarang tidak: ketiadaan tenant
    berarti penolakan, bukan akses tanpa batas.
    """
    monkeypatch.delenv("DEXTRA_LEGACY_TENANT", raising=False)
    account = _make_tenant_user("approver")
    _login(client, account)
    mandate_id = _approve(client, plan_id=f"pln_legacy_{uuid.uuid4().hex[:6]}").json()["mandate_id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    response = client.get(f"/api/v1/mandates/{mandate_id}", headers=ops_headers)
    assert response.status_code in (403, 404)


def test_bound_legacy_token_sees_only_its_own_tenant(client, ops_headers, _clean_throttle, monkeypatch):
    """Dengan pengikatan, token gateway hanya melihat tenant yang ditunjuk."""
    first = _make_tenant_user("approver", slug_prefix="legacy-a")
    second = _make_tenant_user("approver", slug_prefix="legacy-b")

    _login(client, first)
    own_mandate = _approve(client, plan_id=f"pln_own_{uuid.uuid4().hex[:6]}").json()["mandate_id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    _login(client, second)
    foreign_mandate = _approve(client, plan_id=f"pln_foreign_{uuid.uuid4().hex[:6]}").json()[
        "mandate_id"
    ]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("dextra_csrf")})

    monkeypatch.setenv("DEXTRA_LEGACY_TENANT", first["tenant_slug"])

    assert client.get(f"/api/v1/mandates/{own_mandate}", headers=ops_headers).status_code == 200
    # Mandate tenant lain: 404, bukan 403 — 403 akan mengonfirmasi keberadaannya.
    assert client.get(f"/api/v1/mandates/{foreign_mandate}", headers=ops_headers).status_code == 404

    listed = client.get("/api/v1/mandates", headers=ops_headers).json()["items"]
    ids = {item["id"] for item in listed}
    assert own_mandate in ids
    assert foreign_mandate not in ids


def test_bound_legacy_token_rejects_unknown_tenant_slug(client, ops_headers, monkeypatch):
    """Salah konfigurasi harus menolak, bukan diam-diam memberi akses global."""
    monkeypatch.setenv("DEXTRA_LEGACY_TENANT", "tenant-yang-tidak-ada")
    assert client.get("/api/v1/mandates", headers=ops_headers).status_code == 401
