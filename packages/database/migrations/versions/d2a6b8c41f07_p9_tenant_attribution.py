"""P9: atribusi tenant pada approval, mandate, dan eksekusi

Tanpa kolom ini, otorisasi hanya bisa membedakan *jenis* pemanggil, bukan *milik
siapa* resource itu. Menambahkan `tenant_id` membuat pemeriksaan lintas tenant
mungkin dilakukan di server.

Nullable dan tanpa backfill: baris yang dibuat sebelum P9 memang tidak punya
tenant, dan menebaknya akan menghasilkan atribusi palsu. Baris seperti itu tidak
terlihat oleh pemanggil yang terikat tenant (lihat `core/authz.py`).

Revision ID: d2a6b8c41f07
Revises: c4d8e1f6a2b3
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2a6b8c41f07"
down_revision: Union[str, None] = "c4d8e1f6a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("approvals", "mandates", "executions")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=True))
            batch.create_foreign_key(
                op.f(f"fk_{table}_tenant_id_tenants"),
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="CASCADE",
            )
        op.create_index(op.f(f"ix_{table}_tenant_id"), table, ["tenant_id"], unique=False)


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(op.f(f"ix_{table}_tenant_id"), table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(op.f(f"fk_{table}_tenant_id_tenants"), type_="foreignkey")
            batch.drop_column("tenant_id")
