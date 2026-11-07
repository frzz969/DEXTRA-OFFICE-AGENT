"""FASE 2 (A1-A3): kontrak idempotensi, backfill tenant, selaraskan audit defaults.

A1: executions.params_digest ditambah; constraint (mandate_id, action_id)
    diganti (mandate_id, action_id, params_digest) agar SATU kontrak dengan
    service (key=mandate:action:params_digest, kolom idempotency_key unik).
    Baris lama: params_digest di-derived dari idempotency_key; baris yang
    tidak bisa di-derived dibiarkan dicatat, BUKAN dihapus/ditulis ulang.
A2: Backfill tenant non-destruktif: baris NULL pada approvals/mandates/
    executions diisi tenant legacy/org default dari env
    DEXTRA_LEGACY_TENANT_BUKAN (di bawah). Hanya bila tenant sasaran itu
    benar-benar ada, dan hanya atas baris NULL. NOT NULL *tidak* dipaksa di
    sini: kolom tetap nullable agar fresh DB=dari-model dan operator bisa
    meninjau hasilnya. Guard: COUNT NULL & tabel yang tidak punya tenant
    di-skip dengan log, tidak gagal.
A3: Audit defaults disamakan model<->migrasi: server_default diselaraskan
    untuk fresh DB (detail_json '{}', prev_hash '', chain_version '2' untuk
    baris baru; lihat audit.py). Data historis TIDAK ditulis ulang; downgrade
    hanyalah keberadaan kolom, bukan menghapus baris.

Revision ID: 27ba08c94572
Revises: a8c1e5f70b92
"""
from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "27ba08c94572"
down_revision: Union[str, None] = "a8c1e5f70b92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _legacy_tenant_id(conn) -> str | None:
    """Resolusi tenant backfill: env DEXTRA_LEGACY_TENANT_BUKAN (slug atau id)."""
    value = (os.environ.get("DEXTRA_LEGACY_TENANT_BUKAN") or "").strip()
    if not value:
        return None
    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE id = :slug OR slug = :slug LIMIT 1"),
        {"slug": value},
    ).first()
    return row[0] if row else None


def _columns(conn, table: str) -> set[str]:
    if conn.dialect.name == "postgresql":
        rows = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
            ),
            {"t": table},
        ).all()
        return {r[0] for r in rows}
    return {r[1] for r in conn.execute(sa.text(f"PRAGMA table_info({table})")).all()}


def upgrade() -> None:
    conn = op.get_bind()

    # ---------- A1: params_digest + constraint baru ----------
    with op.batch_alter_table("executions") as batch:
        batch.add_column(sa.Column("params_digest", sa.String(length=128), nullable=True))
    # Derive dari idempotency_key = mandate:action:digest (suffix setelah ':')
    # Dialek-agnostik: Python, bukan substr PG/SQLite yang berbeda sintaksnya.
    rows = conn.execute(
        sa.text("SELECT id, idempotency_key, mandate_id, action_id FROM executions")
    ).all()
    for exe_id, key, mandate_id, action_id in rows:
        prefix = f"{mandate_id}:{action_id}:"
        if key and key.startswith(prefix):
            conn.execute(
                sa.text("UPDATE executions SET params_digest = :d WHERE id = :id"),
                {"d": key[len(prefix):], "id": exe_id},
            )
    left = conn.execute(
        sa.text("SELECT COUNT(*) FROM executions WHERE params_digest IS NULL")
    ).scalar_one()
    if left:
        print(f"[A1] {left} executions tanpa params_digest ter-derive; dibiarkan (tidak dihapus).")
    with op.batch_alter_table("executions") as batch:
        # NOT NULL tidak dipaksa: model tetap nullable agar fresh DB=dari-model
        # dan baris lama tanpa kunci ter-derive tidak memblokir migrasi.
        batch.drop_constraint("execution_mandate_action", type_="unique")
        batch.create_unique_constraint(
            "execution_mandate_action_params",
            ["mandate_id", "action_id", "params_digest"],
        )
    op.create_index("ix_executions_params_digest", "executions", ["params_digest"], unique=False)

    # ---------- A2: backfill tenant (non-destruktif, NULL-only) ----------
    tenant_id = _legacy_tenant_id(conn)
    if not (os.environ.get("DEXTRA_LEGACY_TENANT") or os.environ.get("DEXTRA_LEGACY_TENANT_BUKAN") or "").strip():
        # Guard: jangan memalsukan kepemilikan diam-diam. Tanpa tenant legacy
        # yang terverifikasi, baris NULL dibiarkan NULL (tak terlihat
        # pemanggil terikat tenant) — baca core/authz.py.
        print("[A2] DEXTRA_LEGACY_TENANT kosong/tidak ada; backfill dilewati (NULL dibiarkan).")
        tenant_id = None
    if tenant_id is None:
        print("[A2] DEXTRA_LEGACY_TENANT_BUKAN kosong/tidak ada; backfill dilewati.")
    else:
        for table in ("approvals", "mandates", "executions"):
            if "tenant_id" not in _columns(conn, table):
                continue
            nulls = conn.execute(
                sa.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL")
            ).scalar_one()
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL"
                ),
                {"tid": tenant_id},
            )
            print(f"[A2] {table}: {nulls} NULL -> {tenant_id} (guard COUNT NULL sebelum update).")
        print("[A2] NOT NULL tidak dipaksa: kolom tetap nullable, tenant lama yang tidak")
        print("[A2] ada di env tetap NULL dan tidak disamarkan (lihat core/authz.py).")

    # ---------- A3: selaraskan server_default audit (fresh DB = model) ----------
    # Hanya DEFAULT, bukan data: baris historis tidak ditulis ulang.
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("detail_json", server_default="{}")
        batch.alter_column("prev_hash", server_default="")
        batch.alter_column("chain_version", server_default="2")


def downgrade() -> None:
    """Non-destruktif: hanya mengembalikan DEFAULT/constraint. Tidak menghapus baris
    dan tidak membatalkan backfill (nilai tenant yang terlanjur diisi TIDAK di-null-kan)."""
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("detail_json", server_default=None)
        batch.alter_column("prev_hash", server_default=None)
        batch.alter_column("chain_version", server_default="1")
    op.drop_index("ix_executions_params_digest", table_name="executions")
    with op.batch_alter_table("executions") as batch:
        batch.drop_constraint("execution_mandate_action_params", type_="unique")
        batch.create_unique_constraint(
            "execution_mandate_action", ["mandate_id", "action_id"]
        )
        batch.drop_column("params_digest")
