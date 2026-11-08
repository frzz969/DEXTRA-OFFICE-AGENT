"""Konsumsi nonce mandate sekali pakai.

Revision ID: j0d5e6f7a8b9
Revises: i9d4e5f6a7b8
Create Date: 2026-11-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0d5e6f7a8b9"
down_revision: Union[str, None] = "i9d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mandates",
        sa.Column("nonce_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mandates",
        sa.Column("consumed_by_execution_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mandates", "consumed_by_execution_id")
    op.drop_column("mandates", "nonce_used_at")
