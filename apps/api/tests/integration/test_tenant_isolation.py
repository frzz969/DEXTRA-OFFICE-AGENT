"""Isolasi tenant dan siklus hidup kredensial, diuji di lapisan repository.

Tes ini tidak memakai HTTP: P7 membuktikan batas data dan perilaku kredensial
sebelum P9 memasang endpoint. Kalau batas ini bocor di repository, endpoint yang
rapi di atasnya hanya menyamarkan kebocoran.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.base import new_id, utcnow
from app.database.session import session_scope
from app.models.credentials import ApiToken
from app.models.identity import User
from app.models.tenant import Tenant
from app.repositories import credentials as cred
from app.repositories import tenants as tenant_repo


@pytest.fixture()
def fixture_tenants(app):
    """Dua tenant terpisah, masing-masing dengan satu anggota."""
    suffix = uuid.uuid4().hex[:8]
    with session_scope() as db:
        role = tenant_repo.ensure_system_role(db, "approver")
        viewer = tenant_repo.ensure_system_role(db, "viewer")

        alpha = tenant_repo.create_tenant(db, slug=f"alpha-{suffix}", name="Alpha")
        beta = tenant_repo.create_tenant(db, slug=f"beta-{suffix}", name="Beta")

        user_alpha = User(
            id=new_id("usr"),
            email=f"alpha-{suffix}@example.test",
            display_name="Alpha User",
            is_active=True,
        )
        user_beta = User(
            id=new_id("usr"),
            email=f"beta-{suffix}@example.test",
            display_name="Beta User",
            is_active=True,
        )
        db.add_all([user_alpha, user_beta])
        db.flush()

        tenant_repo.add_membership(
            db, tenant_id=alpha.id, user_id=user_alpha.id, role_id=role.id, is_default=True
        )
        tenant_repo.add_membership(
            db, tenant_id=beta.id, user_id=user_beta.id, role_id=viewer.id, is_default=True
        )

        return {
            "alpha": alpha.id,
            "beta": beta.id,
            "user_alpha": user_alpha.id,
            "user_beta": user_beta.id,
            "role_approver": role.id,
            "role_viewer": viewer.id,
        }


def test_principal_is_none_without_membership(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        # Pengguna Beta tidak punya keanggotaan di Alpha.
        assert tenant_repo.principal_for(db, tenant_id=ids["alpha"], user_id=ids["user_beta"]) is None


def test_principal_capabilities_come_from_role(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        principal = tenant_repo.principal_for(db, tenant_id=ids["alpha"], user_id=ids["user_alpha"])
        assert principal is not None
        assert principal.role_name == "approver"
        assert principal.can("approve")
        assert principal.can("execute")
        assert not principal.can("manage_users")  # belum punya endpoint penegak


def test_suspended_tenant_revokes_principal(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        tenant = db.get(Tenant, ids["alpha"])
        tenant.status = "suspended"
    with session_scope() as db:
        assert tenant_repo.principal_for(db, tenant_id=ids["alpha"], user_id=ids["user_alpha"]) is None


def test_membership_cannot_link_role_from_other_tenant(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        custom_role = tenant_repo.ensure_system_role(db, "operator")
        custom_role.tenant_id = ids["beta"]  # role sekarang milik Beta
        db.flush()
    with session_scope() as db:
        with pytest.raises(ValueError, match="tenant lain"):
            tenant_repo.add_membership(
                db,
                tenant_id=ids["alpha"],
                user_id=ids["user_beta"],
                role_id=custom_role.id,
            )
        db.rollback()


def test_token_scope_cannot_exceed_owner_capabilities(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        with pytest.raises(cred.CredentialError, match="melebihi wewenang"):
            cred.issue_token(
                db,
                tenant_id=ids["beta"],  # user_beta hanya viewer
                name="terlalu-lebar",
                scopes=["view_own", "approve"],
                owner_user_id=ids["user_beta"],
            )
        db.rollback()


def test_issued_token_authenticates_with_effective_scopes(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        token, plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="cli",
            scopes=["view_own", "approve"],
            owner_user_id=ids["user_alpha"],
        )
        token_id = token.id
        assert token.token_hash != plaintext
        assert plaintext.startswith(token.token_prefix)

    with session_scope() as db:
        principal = cred.authenticate_token(db, plaintext)
        assert principal is not None
        assert principal.tenant_id == ids["alpha"]
        assert principal.principal_id == ids["user_alpha"]
        assert "approve" in principal.capabilities
        assert "execute" not in principal.capabilities  # tidak diminta saat terbit
        assert principal.token_id == token_id


def test_revoked_token_is_rejected_immediately(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        token, plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="sementara",
            scopes=["view_own"],
            owner_user_id=ids["user_alpha"],
        )
        cred.revoke_token(db, token, "test")
    with session_scope() as db:
        assert cred.authenticate_token(db, plaintext) is None


def test_expired_token_is_rejected(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        _, plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="kedaluwarsa",
            scopes=["view_own"],
            owner_user_id=ids["user_alpha"],
            expires_at=utcnow() - timedelta(seconds=1),
        )
    with session_scope() as db:
        assert cred.authenticate_token(db, plaintext) is None


def test_unknown_token_is_rejected(fixture_tenants):
    with session_scope() as db:
        assert cred.authenticate_token(db, "dx_0123456789ab_" + "x" * 40) is None


def test_membership_loss_revokes_token_access(fixture_tenants):
    """Token tidak boleh hidup lebih lama dari keanggotaan pemiliknya."""
    ids = fixture_tenants
    with session_scope() as db:
        _, plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="anggota",
            scopes=["view_own"],
            owner_user_id=ids["user_alpha"],
        )
    with session_scope() as db:
        membership = tenant_repo.get_membership(db, tenant_id=ids["alpha"], user_id=ids["user_alpha"])
        membership.status = "suspended"
    with session_scope() as db:
        assert cred.authenticate_token(db, plaintext) is None


def test_token_lookup_is_tenant_scoped(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        token, _ = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="alpha-token",
            scopes=["view_own"],
            owner_user_id=ids["user_alpha"],
        )
        token_id = token.id
    with session_scope() as db:
        assert cred.get_token(db, tenant_id=ids["alpha"], token_id=token_id) is not None
        assert cred.get_token(db, tenant_id=ids["beta"], token_id=token_id) is None
        beta_tokens = [t.id for t in cred.list_tokens(db, ids["beta"])]
        assert token_id not in beta_tokens


def test_service_account_rotation_revokes_old_token(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        account = cred.create_service_account(
            db,
            tenant_id=ids["alpha"],
            name="worker-test",
            kind="worker",
            scopes=["view_own", "execute"],
        )
        token, old_plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="worker-token",
            scopes=["view_own"],
            service_account_id=account.id,
        )
        replacement, new_plaintext = cred.rotate_token(db, token)
        assert replacement.rotated_from_id == token.id
        assert replacement.service_account_id == account.id

    with session_scope() as db:
        assert cred.authenticate_token(db, old_plaintext) is None
        principal = cred.authenticate_token(db, new_plaintext)
        assert principal is not None
        assert principal.kind == "service"


def test_revoking_service_account_kills_all_its_tokens(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        account = cred.create_service_account(
            db,
            tenant_id=ids["alpha"],
            name="worker-cascade",
            kind="worker",
            scopes=["view_own"],
        )
        _, plaintext = cred.issue_token(
            db,
            tenant_id=ids["alpha"],
            name="cascade",
            scopes=["view_own"],
            service_account_id=account.id,
        )
        revoked = cred.revoke_service_account(db, account, "dinonaktifkan")
        assert revoked == 1
    with session_scope() as db:
        assert cred.authenticate_token(db, plaintext) is None


def test_token_must_have_exactly_one_owner(fixture_tenants):
    """Dijaga oleh CHECK constraint, bukan hanya oleh kode Python."""
    ids = fixture_tenants
    with session_scope() as db:
        account = cred.create_service_account(
            db, tenant_id=ids["alpha"], name="both", kind="worker", scopes=["view_own"]
        )
        db.add(
            ApiToken(
                id=new_id("tok"),
                tenant_id=ids["alpha"],
                name="dua-pemilik",
                token_prefix="dx_000000000000",
                token_hash=new_id("h"),
                owner_user_id=ids["user_alpha"],
                service_account_id=account.id,
                scopes_json="[]",
                status="active",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_service_account_name_is_unique_per_tenant(fixture_tenants):
    ids = fixture_tenants
    with session_scope() as db:
        cred.create_service_account(
            db, tenant_id=ids["alpha"], name="duplikat", kind="worker", scopes=["view_own"]
        )
        with pytest.raises(cred.CredentialError, match="sudah dipakai"):
            cred.create_service_account(
                db, tenant_id=ids["alpha"], name="duplikat", kind="worker", scopes=["view_own"]
            )
        db.rollback()
    # Nama sama di tenant lain tidak bentrok.
    with session_scope() as db:
        cred.create_service_account(
            db, tenant_id=ids["beta"], name="duplikat", kind="worker", scopes=["view_own"]
        )
