"""FASE 4 A14: perlebar users.mfa_secret untuk ciphertext at-rest (64->256).

Nilai legacy base32 (32 char) tetap muat; format enc$v1$ (nonce+b64 ct)
butuh ~60-80 char. Tanpa migrasi ini, alembic check vs model gagal.

Revision ID: g6a3b4c5d6e7
Revises: 27ba08c94572
Create Date: 2026-11-04
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "g6a3b4c5d6e7"
down_revision: Union[str, None] = "27ba08c94572"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("mfa_secret", type_=sa.String(256), existing_type=sa.String(64), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("mfa_secret", type_=sa.String(64), existing_type=sa.String(256), nullable=True)
