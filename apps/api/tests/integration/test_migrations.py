"""Migrasi harus bisa dijalankan maju, mundur, dan tidak menyimpang dari model.

Tes ini menjalankan Alembic sungguhan pada database sementara, bukan memeriksa
isi berkas migrasi. Yang dibuktikan:

1. `upgrade head` membuat tabel yang diklaim ada.
2. `downgrade base` benar-benar menghapusnya (tidak ada "migrasi sekali jalan").
3. `upgrade head` lagi berhasil — migrasi tidak bergantung pada sisa keadaan.
4. `alembic check` tidak menemukan selisih antara model dan migrasi. Tanpa ini,
   `create_all` di tes dan `upgrade` di deployment bisa menghasilkan skema yang
   berbeda tanpa ada yang tahu.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[4]


def _config(url: str) -> Config:
    cfg = Config(str(ROOT / "packages" / "database" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "packages" / "database" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _postgres_base() -> str:
    """URL PostgreSQL dari environment, atau kosong bila suite berjalan di SQLite."""
    url = os.environ.get("DEXTRA_TEST_DATABASE_URL", "")
    return url if url.startswith("postgresql") else ""


@pytest.fixture()
def migrated_url(_database_url: str):
    """Database sementara terpisah; DATABASE_URL asli dipulihkan setelahnya.

    Bila `DEXTRA_TEST_DATABASE_URL` menunjuk PostgreSQL, tes memakai **schema**
    tersendiri di server yang sama (bukan database baru: pembuatan database
    menuntut hak superuser yang belum tentu ada di CI). Dengan begitu migrasi
    benar-benar dijalankan pada dialek target, bukan hanya SQLite.
    """
    base = _postgres_base()
    schema = None
    if base:
        from sqlalchemy.engine import make_url

        schema = f"mig_{os.urandom(4).hex()}"
        admin = create_engine(base, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        admin.dispose()
        separator = "&" if "?" in base else "?"
        url = f"{base}{separator}options=-csearch_path={schema}"
    else:
        directory = Path(tempfile.mkdtemp(prefix="dextra-mig-"))
        url = f"sqlite+pysqlite:///{(directory / 'migration.db').as_posix()}"

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        yield url
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        if schema:
            admin = create_engine(base, isolation_level="AUTOCOMMIT")
            with admin.connect() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def test_upgrade_creates_p7_tables(migrated_url):
    command.upgrade(_config(migrated_url), "head")
    engine = create_engine(migrated_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "tenants",
        "memberships",
        "service_accounts",
        "api_tokens",
        "security_events",
        "login_throttles",
        "users",
        "roles",
        "sessions",
    } <= tables

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    # Dibandingkan dengan kepala skrip, bukan literal: menambah migrasi baru
    # tidak boleh membuat tes ini gagal, tetapi database yang tertinggal harus.
    from alembic.script import ScriptDirectory

    assert version == ScriptDirectory.from_config(_config(migrated_url)).get_current_head()
    engine.dispose()


def test_upgrade_adds_expected_columns(migrated_url):
    command.upgrade(_config(migrated_url), "head")
    engine = create_engine(migrated_url)
    inspector = inspect(engine)
    users = {c["name"] for c in inspector.get_columns("users")}
    sessions = {c["name"] for c in inspector.get_columns("sessions")}
    roles = {c["name"] for c in inspector.get_columns("roles")}
    assert {"password_hash", "mfa_secret", "mfa_enabled", "locked_until"} <= users
    assert {"tenant_id", "csrf_hash", "idle_expires_at", "mfa_verified"} <= sessions
    assert {"tenant_id", "is_system"} <= roles
    engine.dispose()


def test_partial_unique_index_for_system_roles_exists(migrated_url):
    """Index parsial harus benar-benar parsial, dan itu dibaca dari katalog dialek."""
    command.upgrade(_config(migrated_url), "head")
    engine = create_engine(migrated_url)
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            sql = conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE schemaname = current_schema() AND indexname = 'uq_roles_system_name'"
                )
            ).scalar_one()
        else:
            sql = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type='index' AND name='uq_roles_system_name'"
                )
            ).scalar_one()
    assert "tenant_id IS NULL" in sql
    assert "UNIQUE" in sql.upper()
    engine.dispose()


def test_downgrade_removes_p7_tables_and_can_upgrade_again(migrated_url):
    cfg = _config(migrated_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(migrated_url)
    remaining = set(inspect(engine).get_table_names())
    assert "tenants" not in remaining
    assert "api_tokens" not in remaining
    assert "users" not in remaining
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(migrated_url)
    assert "api_tokens" in set(inspect(engine).get_table_names())
    engine.dispose()


def test_migrations_match_models(migrated_url):
    """`alembic check` gagal bila model punya kolom yang tidak ada di migrasi."""
    cfg = _config(migrated_url)
    command.upgrade(cfg, "head")
    command.check(cfg)  # raise AutogenerateDiffsDetected bila menyimpang
