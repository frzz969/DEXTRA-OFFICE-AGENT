"""Office Agent: tabel titik masuk rencana.

Revision ID: f5a2d7e93c18
Revises: e7b3c9d51a84
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f5a2d7e93c18"
down_revision: Union[str, None] = "e7b3c9d51a84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "office_plan_requests",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=96), nullable=False),
        sa.Column("plan_id", sa.String(length=96), nullable=False),
        sa.Column("plan_hash", sa.String(length=128), nullable=False),
        sa.Column("source_json", sa.Text(), nullable=False),
        sa.Column("document_json", sa.Text(), nullable=False),
        sa.Column("actions_json", sa.Text(), nullable=False),
        sa.Column("findings_json", sa.Text(), nullable=False),
        sa.Column("validation_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_service_account_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_service_account_id"],
            ["service_accounts.id"],
            name=op.f("fk_office_plan_requests_created_by_service_account_id_service_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_office_plan_requests_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_office_plan_requests_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_office_plan_requests")),
        sa.UniqueConstraint("tenant_id", "request_id", name="office_plan_request_id"),
    )
    op.create_index(
        op.f("ix_office_plan_requests_tenant_id"), "office_plan_requests", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_office_plan_requests_plan_id"), "office_plan_requests", ["plan_id"], unique=False
    )
    op.create_index(
        "ix_office_plan_requests_tenant_status",
        "office_plan_requests",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_office_plan_requests_tenant_status", table_name="office_plan_requests")
    op.drop_index(op.f("ix_office_plan_requests_plan_id"), table_name="office_plan_requests")
    op.drop_index(op.f("ix_office_plan_requests_tenant_id"), table_name="office_plan_requests")
    op.drop_table("office_plan_requests")
