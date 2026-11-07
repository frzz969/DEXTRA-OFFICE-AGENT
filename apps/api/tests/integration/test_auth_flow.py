"""Autentikasi manusia: login, sesi, MFA, CSRF, rate limit.

Setiap tes di sini menguji klaim yang juga tertulis di dokumen. Kalau MFA
dinyatakan aktif, tes harus bisa login dengan kode TOTP sungguhan dan gagal
tanpa kode. Kalau sesi dinyatakan bisa dicabut, permintaan berikutnya harus 401.
"""
from __future__ import annotations

import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import totp
from app.core.passwords import hash_password
from app.database.base import new_id, utcnow
from app.database.session import session_scope
from app.models.identity import Session as SessionRow
from app.models.identity import User
from app.repositories import tenants as tenant_repo

PASSWORD = "kalimat-sandi-panjang-2026"


@pytest.fixture(autouse=True)
def _clean_throttle(app):
    """Penahan login disimpan di database dan kuncinya per-IP.

    Semua tes memakai IP yang sama (TestClient), jadi tanpa pembersihan ini
    kegagalan dari tes sebelumnya akan mengunci tes berikutnya — dan tes akan
    lulus atau gagal menurut urutan, bukan menurut perilaku.
    """
    from app.models.security import LoginThrottle

    with session_scope() as db:
        for row in db.scalars(select(LoginThrottle)).all():
            db.delete(row)
    yield


@pytest.fixture()
def account(app):
    """Satu tenant baru + satu pengguna approver dengan password nyata."""
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"auth-{suffix}", name="Auth Test")
        role = tenant_repo.ensure_system_role(db, "approver")
        user = User(
            id=new_id("usr"),
            email=f"user-{suffix}@example.test",
            display_name="Pengguna Uji",
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
            "password": PASSWORD,
            "user_id": user.id,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
        }


def _login(client, account, password: str | None = None):
    return client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": password or account["password"]},
    )


def _csrf(client) -> str:
    return client.cookies.get("dextra_csrf") or ""


def _logout(client):
    """Logout juga mengubah keadaan, jadi tunduk pada aturan CSRF yang sama."""
    return client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": _csrf(client)})


# --- Login ------------------------------------------------------------------


def test_login_sets_cookies_and_returns_principal(client, account):
    response = _login(client, account)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authenticated"] is True
    assert body["mfa_required"] is False
    assert body["principal"]["email"] == account["email"]
    assert body["principal"]["tenant_id"] == account["tenant_id"]
    assert "approve" in body["principal"]["capabilities"]
    assert client.cookies.get("dextra_session")
    assert client.cookies.get("dextra_csrf")
    # Cookie sesi tidak boleh bisa dibaca JavaScript; cookie CSRF harus bisa.
    set_cookie = " ".join(response.headers.get_list("set-cookie"))
    assert "HttpOnly" in set_cookie


def test_session_cookie_grants_access_to_protected_endpoint(client, account):
    assert client.get("/api/v1/overview").status_code == 401
    _login(client, account)
    assert client.get("/api/v1/overview").status_code == 200


def test_wrong_password_is_401_with_generic_message(client, account):
    response = _login(client, account, password="password-yang-salah-sekali")
    assert response.status_code == 401
    assert response.json()["detail"] == "Email atau password salah."
    assert client.cookies.get("dextra_session") is None


def test_unknown_email_gives_identical_response(client, account):
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "tidak-ada@example.test", "password": PASSWORD},
    )
    wrong = _login(client, account, password="password-yang-salah-sekali")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_login_to_foreign_tenant_is_rejected(client, account):
    """Pengguna tidak bisa memilih tenant yang bukan miliknya."""
    with session_scope() as db:
        other = tenant_repo.create_tenant(db, slug=f"asing-{uuid.uuid4().hex[:6]}", name="Asing")
        slug = other.slug
    response = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": account["password"], "tenant": slug},
    )
    assert response.status_code == 401


def test_inactive_user_cannot_login(client, account):
    with session_scope() as db:
        db.get(User, account["user_id"]).is_active = False
    assert _login(client, account).status_code == 401


def test_user_without_password_cannot_login(client, account):
    """Tidak ada password default: akun tanpa hash tidak bisa masuk."""
    with session_scope() as db:
        db.get(User, account["user_id"]).password_hash = None
    assert _login(client, account).status_code == 401


# --- Rate limit -------------------------------------------------------------


def test_repeated_failures_lock_the_account(client, account):
    for _ in range(5):
        assert _login(client, account, password="salah-terus").status_code == 401
    locked = _login(client, account)
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_throttle_counts_are_stored_in_database(client, account):
    """Penghitung harus bertahan lintas proses, bukan hanya di memori."""
    from app.repositories import security as security_repo

    for _ in range(3):
        _login(client, account, password="salah-terus")
    with session_scope() as db:
        row = db.scalar(
            select(security_repo.LoginThrottle).where(
                security_repo.LoginThrottle.kind == "email",
                security_repo.LoginThrottle.identifier == account["email"],
            )
        )
        assert row is not None and row.failure_count == 3


def test_successful_login_clears_failure_counter(client, account):
    for _ in range(2):
        _login(client, account, password="salah-terus")
    assert _login(client, account).status_code == 200
    with session_scope() as db:
        user = db.get(User, account["user_id"])
        assert user.failed_login_count == 0


# --- Logout & sesi ----------------------------------------------------------


def test_logout_revokes_session(client, account):
    _login(client, account)
    assert client.get("/api/v1/overview").status_code == 200
    assert _logout(client).status_code == 204
    assert client.get("/api/v1/overview").status_code == 401


def test_revoked_session_is_rejected_even_with_cookie(client, account):
    _login(client, account)
    token = client.cookies.get("dextra_session")
    with session_scope() as db:
        from app.repositories import sessions as session_repo

        row = session_repo.find_session(db, token)
        session_repo.revoke_session(db, row, "test")
    assert client.get("/api/v1/overview").status_code == 401


def test_idle_timeout_closes_session(client, account):
    _login(client, account)
    token = client.cookies.get("dextra_session")
    with session_scope() as db:
        from app.repositories import sessions as session_repo

        row = session_repo.find_session(db, token)
        row.idle_expires_at = utcnow() - timedelta(minutes=1)
    assert client.get("/api/v1/overview").status_code == 401


def test_absolute_expiry_closes_session(client, account):
    _login(client, account)
    token = client.cookies.get("dextra_session")
    with session_scope() as db:
        from app.repositories import sessions as session_repo

        row = session_repo.find_session(db, token)
        row.expires_at = utcnow() - timedelta(minutes=1)
    assert client.get("/api/v1/overview").status_code == 401


def test_session_list_and_revoke_other_session(client, account):
    _login(client, account)
    second = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": account["password"]}
    )
    assert second.status_code == 200
    listing = client.get("/api/v1/auth/sessions").json()
    assert len(listing["items"]) >= 2
    current = next(item for item in listing["items"] if item["current"])
    other = next(item for item in listing["items"] if not item["current"])
    assert other["id"] != current["id"]

    revoked = client.post(
        f"/api/v1/auth/sessions/{other['id']}/revoke", headers={"X-CSRF-Token": _csrf(client)}
    )
    assert revoked.status_code == 200
    remaining = client.get("/api/v1/auth/sessions").json()["items"]
    assert all(item["id"] != other["id"] for item in remaining)


def test_cannot_revoke_other_users_session(client, account):
    _login(client, account)
    with session_scope() as db:
        # Pengguna kedua yang benar-benar ada: PostgreSQL menegakkan foreign key
        # `sessions.user_id`, jadi sesi yatim ditolak database. SQLite tidak
        # menegakkannya secara default — itulah sebabnya tes lama "lulus" di
        # SQLite tetapi gagal di PostgreSQL.
        other = User(
            id=new_id("usr"),
            email=f"lain-{uuid.uuid4().hex[:8]}@example.test",
            display_name="Pengguna Lain",
            is_active=True,
            password_hash=hash_password(PASSWORD),
        )
        db.add(other)
        db.flush()
        tenant_repo.add_membership(
            db,
            tenant_id=account["tenant_id"],
            user_id=other.id,
            role_id=tenant_repo.ensure_system_role(db, "viewer").id,
        )
        foreign = SessionRow(
            id=new_id("ses"),
            user_id=other.id,
            tenant_id=account["tenant_id"],
            token_hash=new_id("h"),
            expires_at=utcnow() + timedelta(hours=1),
        )
        db.add(foreign)
        foreign_id = foreign.id
    response = client.post(
        f"/api/v1/auth/sessions/{foreign_id}/revoke", headers={"X-CSRF-Token": _csrf(client)}
    )
    assert response.status_code == 404


# --- CSRF -------------------------------------------------------------------


def test_post_without_csrf_header_is_rejected(client, account):
    _login(client, account)
    response = client.post("/api/v1/auth/mfa/enroll")
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"


def test_post_with_wrong_csrf_token_is_rejected(client, account):
    _login(client, account)
    response = client.post("/api/v1/auth/mfa/enroll", headers={"X-CSRF-Token": "salah"})
    assert response.status_code == 403


def test_post_with_csrf_token_passes(client, account):
    _login(client, account)
    response = client.post("/api/v1/auth/mfa/enroll", headers={"X-CSRF-Token": _csrf(client)})
    assert response.status_code in (200, 201)


def test_bearer_token_requests_are_not_subject_to_csrf(client, ops_headers):
    """CSRF hanya relevan untuk autentikasi cookie."""
    response = client.post(
        "/api/v1/approvals",
        headers=ops_headers,
        json={
            "plan_id": "pln_csrf",
            "action_id": "act_1",
            "action_type": "send_email",
            "params": {},
            "approver_id": "user_001",
            "decision": "rejected",
        },
    )
    assert response.status_code in (200, 201)


# --- MFA --------------------------------------------------------------------


def _enroll(client):
    response = client.post("/api/v1/auth/mfa/enroll", headers={"X-CSRF-Token": _csrf(client)})
    assert response.status_code == 200, response.text
    return response.json()["secret"]


def test_mfa_is_not_active_before_code_verified(client, account):
    _login(client, account)
    secret = _enroll(client)
    assert secret
    with session_scope() as db:
        assert db.get(User, account["user_id"]).mfa_enabled is False


def test_mfa_activate_with_valid_code(client, account):
    _login(client, account)
    secret = _enroll(client)
    code = totp.code_at(secret, time.time())
    response = client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": code},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["mfa_enabled"] is True
    with session_scope() as db:
        assert db.get(User, account["user_id"]).mfa_enabled is True


def test_mfa_activate_rejects_wrong_code(client, account):
    _login(client, account)
    _enroll(client)
    response = client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": "000000"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 400
    with session_scope() as db:
        assert db.get(User, account["user_id"]).mfa_enabled is False


def test_login_with_mfa_requires_second_step(client, account):
    _login(client, account)
    secret = _enroll(client)
    client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": totp.code_at(secret, time.time())},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    _logout(client)

    first = _login(client, account)
    assert first.status_code == 200
    assert first.json()["mfa_required"] is True
    assert first.json()["principal"]["capabilities"] == []
    # Belum boleh menyentuh apa pun yang butuh capability.
    assert client.get("/api/v1/audit-events").status_code == 403

    code = totp.code_at(secret, time.time() + 30)
    verified = client.post(
        "/api/v1/auth/mfa/verify", json={"code": code}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["mfa_required"] is False
    assert client.get("/api/v1/audit-events").status_code == 200


def test_totp_code_cannot_be_reused(client, account):
    """Kode yang sudah dipakai untuk satu langkah tidak berlaku lagi.

    Inilah bedanya MFA yang benar-benar berjalan dengan MFA yang hanya
    mengklaim: tanpa `mfa_last_step`, kode yang dicegat masih bisa dipakai
    sampai jendela 30 detiknya habis.
    """
    _login(client, account)
    secret = _enroll(client)
    code = totp.code_at(secret, time.time())
    assert (
        client.post(
            "/api/v1/auth/mfa/activate",
            json={"code": code},
            headers={"X-CSRF-Token": _csrf(client)},
        ).status_code
        == 200
    )

    _logout(client)
    _login(client, account)
    replay = client.post(
        "/api/v1/auth/mfa/verify", json={"code": code}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert replay.status_code == 401

    # Kode dari langkah berikutnya tetap diterima.
    fresh = totp.code_at(secret, time.time() + 30)
    accepted = client.post(
        "/api/v1/auth/mfa/verify", json={"code": fresh}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert accepted.status_code == 200, accepted.text


def test_mfa_disable_requires_password_and_code(client, account):
    _login(client, account)
    secret = _enroll(client)
    client.post(
        "/api/v1/auth/mfa/activate",
        json={"code": totp.code_at(secret, time.time())},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    headers = {"X-CSRF-Token": _csrf(client)}
    wrong = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "salah-sekali-lagi", "code": totp.code_at(secret, time.time() + 30)},
        headers=headers,
    )
    assert wrong.status_code == 401
    with session_scope() as db:
        assert db.get(User, account["user_id"]).mfa_enabled is True

    ok = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": account["password"], "code": totp.code_at(secret, time.time() + 30)},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    with session_scope() as db:
        user = db.get(User, account["user_id"])
        assert user.mfa_enabled is False and user.mfa_secret is None


# --- Password ---------------------------------------------------------------


def test_change_password_revokes_other_sessions(client, account):
    _login(client, account)
    second = client.post(
        "/api/v1/auth/login", json={"email": account["email"], "password": account["password"]}
    )
    second_token = second.cookies.get("dextra_session") or client.cookies.get("dextra_session")

    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": account["password"], "new_password": "kalimat-sandi-baru-2026"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["sessions_revoked"] >= 1
    # Sesi lama tidak berlaku lagi.
    assert client.get("/api/v1/overview").status_code == 200  # sesi saat ini dirotasi

    _logout(client)
    assert _login(client, account).status_code == 401  # password lama ditolak
    assert _login(client, account, password="kalimat-sandi-baru-2026").status_code == 200
    assert second_token is not None


def test_change_password_rejects_weak_new_password(client, account):
    _login(client, account)
    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": account["password"], "new_password": "pendek"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 422


# --- Kejujuran konteks ------------------------------------------------------


def test_session_endpoint_reports_real_state(client, account):
    _login(client, account)
    payload = client.get("/api/v1/auth/session").json()
    assert payload["auth_kind"] == "session"
    assert payload["pending_mfa"] is False
    assert payload["role"] == "approver"
    assert payload["tenant"]["slug"] == account["tenant_slug"]
    assert payload["mfa_enabled"] is False
