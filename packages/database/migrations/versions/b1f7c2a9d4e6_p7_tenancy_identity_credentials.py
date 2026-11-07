"""P7: tenant, keanggotaan, kredensial mesin, peristiwa keamanan

Migrasi ini menambah fondasi identitas yang dipakai P8-P12:

- `tenants` + `memberships`: batas data keras, dan role per tenant.
- `roles` menjadi milik tenant; role sistem tetap lintas tenant lewat partial
  unique index (`tenant_id IS NULL`), karena NULL tidak saling bentrok pada
  unique constraint biasa.
- `users` mendapat kolom kredensial (hash password, TOTP, lockout).
- `sessions` mendapat tenant aktif, batas idle, CSRF, dan jejak rotasi.
- `service_accounts` + `api_tokens`: identitas non-manusia dan kredensialnya.
  Secret token tidak pernah disimpan — hanya hash dan prefix tampilan.
- `security_events` + `login_throttles`: sumber data Security Center dan
  penahan brute-force yang bertahan lintas proses.

Semua penambahan kolom memakai `batch_alter_table` supaya dapat dijalankan di
SQLite (pengembangan) maupun PostgreSQL (target). Di PostgreSQL batch hanya
menghasilkan ALTER TABLE biasa.

Revision ID: b1f7c2a9d4e6
Revises: d9cd32b89961
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1f7c2a9d4e6"
down_revision: Union[str, None] = "d9cd32b89961"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Tenant ---
    op.create_table(
        "tenants",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("settings_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("slug", name=op.f("uq_tenants_slug")),
    )

    # --- 2. Role menjadi milik tenant ---
    with op.batch_alter_table("roles") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.drop_constraint(op.f("uq_roles_name"), type_="unique")
        batch.create_foreign_key(
            op.f("fk_roles_tenant_id_tenants"),
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint("role_tenant_name", ["tenant_id", "name"])
    op.create_index(op.f("ix_roles_tenant_id"), "roles", ["tenant_id"], unique=False)
    op.create_index(
        "uq_roles_system_name",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
        sqlite_where=sa.text("tenant_id IS NULL"),
    )

    # --- 3. Kredensial manusia pada users ---
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("mfa_secret", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # --- 4. Keanggotaan ---
    op.create_table(
        "memberships",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_memberships_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_memberships_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint("tenant_id", "user_id", name="membership_user"),
    )
    op.create_index(op.f("ix_memberships_tenant_id"), "memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)
    op.create_index(
        "ix_memberships_tenant_status", "memberships", ["tenant_id", "status"], unique=False
    )

    # --- 5. Sesi: tenant aktif, idle timeout, CSRF, rotasi ---
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("csrf_hash", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("revoked_reason", sa.String(length=64), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("rotated_from_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("ip_address", sa.String(length=64), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("user_agent", sa.String(length=255), nullable=False, server_default="")
        )
        batch.create_foreign_key(
            op.f("fk_sessions_tenant_id_tenants"),
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_foreign_key(
            op.f("fk_sessions_rotated_from_id_sessions"),
            "sessions",
            ["rotated_from_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(op.f("ix_sessions_tenant_id"), "sessions", ["tenant_id"], unique=False)
    op.create_index("ix_sessions_user_revoked", "sessions", ["user_id", "revoked_at"], unique=False)
    op.create_index(
        "ix_sessions_tenant_created", "sessions", ["tenant_id", "issued_at"], unique=False
    )

    # --- 6. Identitas non-manusia ---
    op.create_table(
        "service_accounts",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_service_accounts_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_service_accounts_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_accounts")),
        sa.UniqueConstraint("tenant_id", "name", name="service_account_name"),
    )
    op.create_index(
        op.f("ix_service_accounts_tenant_id"), "service_accounts", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_service_accounts_tenant_status",
        "service_accounts",
        ["tenant_id", "status"],
        unique=False,
    )

    # --- 7. Kredensial ---
    op.create_table(
        "api_tokens",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("service_account_id", sa.String(length=64), nullable=True),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND service_account_id IS NULL) "
            "OR (owner_user_id IS NULL AND service_account_id IS NOT NULL)",
            name="api_token_single_owner",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_api_tokens_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_api_tokens_owner_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rotated_from_id"],
            ["api_tokens.id"],
            name=op.f("fk_api_tokens_rotated_from_id_api_tokens"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["service_account_id"],
            ["service_accounts.id"],
            name=op.f("fk_api_tokens_service_account_id_service_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_api_tokens_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_api_tokens_token_hash")),
    )
    op.create_index(op.f("ix_api_tokens_tenant_id"), "api_tokens", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_api_tokens_owner_user_id"), "api_tokens", ["owner_user_id"], unique=False)
    op.create_index(
        op.f("ix_api_tokens_service_account_id"), "api_tokens", ["service_account_id"], unique=False
    )
    op.create_index("ix_api_tokens_tenant_status", "api_tokens", ["tenant_id", "status"], unique=False)
    op.create_index("ix_api_tokens_prefix", "api_tokens", ["token_prefix"], unique=False)

    # --- 8. Peristiwa keamanan ---
    op.create_table(
        "security_events",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("actor_service_account_id", sa.String(length=64), nullable=True),
        sa.Column("actor_label", sa.String(length=160), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_service_account_id"],
            ["service_accounts.id"],
            name=op.f("fk_security_events_actor_service_account_id_service_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_security_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_security_events_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_events")),
    )
    op.create_index(op.f("ix_security_events_tenant_id"), "security_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_security_events_at"), "security_events", ["at"], unique=False)
    op.create_index(
        op.f("ix_security_events_actor_user_id"), "security_events", ["actor_user_id"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_actor_service_account_id"),
        "security_events",
        ["actor_service_account_id"],
        unique=False,
    )
    op.create_index("ix_security_events_tenant_at", "security_events", ["tenant_id", "at"], unique=False)
    op.create_index("ix_security_events_type_at", "security_events", ["event_type", "at"], unique=False)

    op.create_table(
        "login_throttles",
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("first_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_throttles")),
        sa.UniqueConstraint("kind", "identifier", name="login_throttle_subject"),
    )


def downgrade() -> None:
    op.drop_table("login_throttles")
    op.drop_index("ix_security_events_type_at", table_name="security_events")
    op.drop_index("ix_security_events_tenant_at", table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_service_account_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_user_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_at"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_tenant_id"), table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_api_tokens_prefix", table_name="api_tokens")
    op.drop_index("ix_api_tokens_tenant_status", table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_service_account_id"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_owner_user_id"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_tenant_id"), table_name="api_tokens")
    op.drop_table("api_tokens")
    op.drop_index("ix_service_accounts_tenant_status", table_name="service_accounts")
    op.drop_index(op.f("ix_service_accounts_tenant_id"), table_name="service_accounts")
    op.drop_table("service_accounts")

    op.drop_index("ix_sessions_tenant_created", table_name="sessions")
    op.drop_index("ix_sessions_user_revoked", table_name="sessions")
    op.drop_index(op.f("ix_sessions_tenant_id"), table_name="sessions")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_constraint(op.f("fk_sessions_rotated_from_id_sessions"), type_="foreignkey")
        batch.drop_constraint(op.f("fk_sessions_tenant_id_tenants"), type_="foreignkey")
        batch.drop_column("user_agent")
        batch.drop_column("ip_address")
        batch.drop_column("mfa_verified")
        batch.drop_column("rotated_from_id")
        batch.drop_column("revoked_reason")
        batch.drop_column("last_seen_at")
        batch.drop_column("idle_expires_at")
        batch.drop_column("csrf_hash")
        batch.drop_column("tenant_id")

    op.drop_index("ix_memberships_tenant_status", table_name="memberships")
    op.drop_index(op.f("ix_memberships_user_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_tenant_id"), table_name="memberships")
    op.drop_table("memberships")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("last_login_at")
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_count")
        batch.drop_column("mfa_enrolled_at")
        batch.drop_column("mfa_enabled")
        batch.drop_column("mfa_secret")
        batch.drop_column("password_changed_at")
        batch.drop_column("password_hash")

    op.drop_index("uq_roles_system_name", table_name="roles")
    op.drop_index(op.f("ix_roles_tenant_id"), table_name="roles")
    with op.batch_alter_table("roles") as batch:
        batch.drop_constraint("role_tenant_name", type_="unique")
        batch.drop_constraint(op.f("fk_roles_tenant_id_tenants"), type_="foreignkey")
        batch.drop_column("is_system")
        batch.drop_column("tenant_id")
        batch.create_unique_constraint(op.f("uq_roles_name"), ["name"])

    op.drop_table("tenants")
