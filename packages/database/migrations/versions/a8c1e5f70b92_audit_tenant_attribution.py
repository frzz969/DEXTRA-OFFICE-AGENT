"""Atribusi tenant pada audit lewat rantai berversi.

Masalahnya: `audit_events` tidak punya kolom tenant, sehingga peristiwa dari
satu tenant tidak bisa dipisahkan dari tenant lain — dan menambahkan kolom itu
ke payload yang di-hash akan mengubah hash setiap baris historis.

Pendekatannya: **versi rantai**. Baris lama tetap `chain_version = 1` dan
payload hash-nya tidak disentuh sama sekali (12 kunci, tanpa `tenant_id`).
Baris baru ditulis `chain_version = 2` dengan `tenant_id` ikut di-hash, sehingga
atribusi tenant tidak bisa diubah tanpa memutus rantai.

Tidak ada baris lama yang diubah. Tidak ada hash historis yang ditulis ulang.

Revision ID: a8c1e5f70b92
Revises: f5a2d7e93c18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a8c1e5f70b92"
down_revision = "f5a2d7e93c18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("chain_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_index("ix_audit_events_tenant_id", ["tenant_id"])

    # `server_default="1"` mengisi baris lama dengan 1 tanpa UPDATE terpisah,
    # dan memastikan penulisan di luar ORM pun mendapat versi yang sah.


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_index("ix_audit_events_tenant_id")
        batch.drop_column("chain_version")
        batch.drop_column("tenant_id")
