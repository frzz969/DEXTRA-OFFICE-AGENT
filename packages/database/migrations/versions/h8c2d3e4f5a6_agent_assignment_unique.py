"""Keunikan penugasan agen: (task_id, agent_id, role).

Pemeriksaan "sudah ada?" di endpoint assign berjalan sebelum INSERT, jadi dua
permintaan bersamaan sama-sama lolos dan menghasilkan dua baris. Constraint ini
memindahkan jaminannya ke database.

Duplikat yang mungkin sudah ada dihapus lebih dulu — menyisakan baris dengan id
terkecil per kelompok — supaya migrasi tidak gagal pada data lama.

Revision ID: h8c2d3e4f5a6
Revises: 726140e863cc
Create Date: 2026-11-05
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op

revision: str = "h8c2d3e4f5a6"
down_revision: Union[str, None] = "726140e863cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "agent_assignment_unique"


def upgrade() -> None:
    # Rapikan duplikat lama sebelum constraint dipasang.
    op.execute(
        """
        DELETE FROM agent_assignments
        WHERE id NOT IN (
            SELECT keep_id FROM (
                SELECT MIN(id) AS keep_id
                FROM agent_assignments
                GROUP BY task_id, agent_id, role
            ) AS keep
        )
        """
    )
    with op.batch_alter_table("agent_assignments") as batch:
        batch.create_unique_constraint(_CONSTRAINT, ["task_id", "agent_id", "role"])


def downgrade() -> None:
    with op.batch_alter_table("agent_assignments") as batch:
        batch.drop_constraint(_CONSTRAINT, type_="unique")
