"""Lane A: atribusi tenant pada workforce, tasks, governance.

Menambahkan `tenant_id` nullable (FK tenants.id ON DELETE CASCADE, indeks)
pada agents, work_packages, tasks, policies, policy_evaluations, dan
agent_assignments. Nullable dan tanpa backfill: baris lama tetap NULL dan
tidak terlihat oleh pemanggil yang terikat tenant (konsisten P9).

Slug per-tenant: unique global agents.slug / policies.slug diganti dengan
composite unique (tenant_id, slug) agar slug yang sama sah di tenant
berbeda. Constraint komposit mengikuti semantik NULL standar Postgres &
SQLite (NULL dianggap berbeda), jadi baris legacy NULL-tenant tetap tidak
saling berbenturan di kolom tenant_id — sama seperti skill_slug yang sudah
berjalan (skills.tenant_id, slug).

Non-destruktif: data tidak dihapus/ditulis ulang; downgrade hanya
mengembalikan constraint dan kolom, nilai tenant yang terlanjur diisi
TIDAK di-null-kan.

Revision ID: 726140e863cc
Revises: g6a3b4c5d6e7
Create Date: 2026-11-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "726140e863cc"
down_revision: Union[str, None] = "g6a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "agents",
    "work_packages",
    "tasks",
    "policies",
    "policy_evaluations",
    "agent_assignments",
)

#: table -> (constraint lama di-hapus, constraint komposit baru)
SLUG_UNIQUE = {
    "agents": ("uq_agents_slug", "agent_tenant_slug"),
    "policies": ("uq_policies_slug", "policy_tenant_slug"),
}


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

    for table, (old, new) in SLUG_UNIQUE.items():
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(op.f(old), type_="unique")
            batch.create_unique_constraint(new, ["tenant_id", "slug"])


def downgrade() -> None:
    for table, (old, new) in SLUG_UNIQUE.items():
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(new, type_="unique")
            batch.create_unique_constraint(op.f(old), ["slug"])

    for table in TABLES:
        op.drop_index(op.f(f"ix_{table}_tenant_id"), table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(op.f(f"fk_{table}_tenant_id_tenants"), type_="foreignkey")
            batch.drop_column("tenant_id")
