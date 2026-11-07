"""P8: kolom anti-replay TOTP

`mfa_last_step` menyimpan langkah waktu (30 detik) kode TOTP terakhir yang
diterima. Tanpa kolom ini, kode yang sudah dicegat masih bisa dipakai ulang
sampai jendelanya habis.

Revision ID: c4d8e1f6a2b3
Revises: b1f7c2a9d4e6
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d8e1f6a2b3"
down_revision: Union[str, None] = "b1f7c2a9d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("mfa_last_step", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("mfa_last_step")
