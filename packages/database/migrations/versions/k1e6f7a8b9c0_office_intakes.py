"""Intake WorkBuddy (deterministik, tanpa LLM).

Revision ID: k1e6f7a8b9c0
Revises: j0d5e6f7a8b9
Create Date: 2026-11-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k1e6f7a8b9c0"
down_revision: Union[str, None] = "j0d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "office_intakes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=96), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("fields_json", sa.Text(), nullable=False),
        sa.Column("clarification_json", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.String(length=96), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "request_id", name="office_intake_request_id"),
    )
    op.create_index("ix_office_intakes_tenant_id", "office_intakes", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_office_intakes_tenant_id", table_name="office_intakes")
    op.drop_table("office_intakes")
