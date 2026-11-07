"""Perilaku yang hanya bisa dibuktikan pada PostgreSQL sungguhan.

SQLite menjalankan seluruh suite, tetapi ia **tidak** menegakkan foreign key
secara default, tidak punya `SELECT ... FOR UPDATE`, dan tidak punya DDL
transaksional. Berkas ini menguji hal-hal itu pada server nyata dan **dilewati**
(dengan alasan tertulis) bila `DEXTRA_TEST_DATABASE_URL` bukan PostgreSQL.

Aturan yang dipegang: tes di sini tidak boleh lulus di SQLite. Kalau sebuah
klaim hanya bisa dibuktikan di PostgreSQL, ia tinggal di sini, bukan di tes
yang berjalan di dua dialek.
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database.base import new_id, utcnow
from app.database.session import get_engine, session_scope
from app.models.credentials import ApiToken
from app.models.identity import Role, Session as SessionRow, User
from app.repositories import tenants as tenant_repo

PG_URL = os.environ.get("DEXTRA_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="Butuh PostgreSQL nyata: set DEXTRA_TEST_DATABASE_URL=postgresql+psycopg://…",
)


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


# --- identitas dialek -------------------------------------------------------


def test_suite_really_runs_on_postgresql(app):
    """Gerbang: kalau ini gagal, tes lain di berkas ini tidak membuktikan apa pun."""
    engine = get_engine()
    assert engine.dialect.name == "postgresql"
    with engine.connect() as conn:
        version = conn.execute(text("SHOW server_version")).scalar_one()
    major = int(str(version).split(".")[0])
    assert major >= 14, f"PostgreSQL {version} terlalu tua untuk partial index & DDL transaksional"


# --- constraint yang ditegakkan database ------------------------------------


def test_foreign_key_rejects_orphan_session(app):
    """Sesi tanpa pengguna harus ditolak database, bukan hanya oleh kode aplikasi."""
    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(
                SessionRow(
                    id=new_id("ses"),
                    user_id=f"usr_tidak_ada_{_suffix()}",
                    token_hash=new_id("h"),
                    expires_at=utcnow() + timedelta(hours=1),
                )
            )


def test_partial_unique_index_blocks_second_system_role(app):
    """`uq_roles_system_name` hanya berlaku saat `tenant_id IS NULL`."""
    name = "admin"
    with session_scope() as db:
        tenant_repo.ensure_system_role(db, name)

    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(
                Role(
                    id=new_id("rol"),
                    name=name,
                    description="duplikat role sistem",
                    tenant_id=None,
                    is_system=True,
                )
            )


def test_tenant_roles_may_share_a_name_across_tenants(app):
    """Kebalikan dari tes di atas: index parsial tidak boleh terlalu ketat."""
    suffix = _suffix()
    with session_scope() as db:
        first = tenant_repo.create_tenant(db, slug=f"ix-a-{suffix}", name="A")
        second = tenant_repo.create_tenant(db, slug=f"ix-b-{suffix}", name="B")
        for tenant in (first, second):
            db.add(Role(id=new_id("rol"), name=f"kustom-{suffix}", tenant_id=tenant.id))
        db.flush()
        count = db.scalar(
            text("SELECT count(*) FROM roles WHERE name = :n").bindparams(n=f"kustom-{suffix}")
        )
    assert count == 2


def test_check_constraint_rejects_token_with_two_owners(app):
    """Token harus milik pengguna **atau** service account, tidak keduanya."""
    suffix = _suffix()
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"ck-{suffix}", name="CK")
        user = User(
            id=new_id("usr"),
            email=f"ck-{suffix}@example.test",
            display_name="CK",
            is_active=True,
        )
        db.add(user)
        db.flush()
        user_id, tenant_id = user.id, tenant.id

    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(
                ApiToken(
                    id=new_id("tok"),
                    tenant_id=tenant_id,
                    name="dua pemilik",
                    token_hash=new_id("h"),
                    token_prefix="dx_test",
                    owner_user_id=user_id,
                    service_account_id="svc_palsu",
                    scopes_json="[]",
                )
            )


def test_api_token_hash_is_unique(app):
    suffix = _suffix()
    token_hash = f"h_dup_{suffix}"
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"tok-{suffix}", name="Tok")
        user = User(
            id=new_id("usr"),
            email=f"tok-{suffix}@example.test",
            display_name="Tok",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(
            ApiToken(
                id=new_id("tok"),
                tenant_id=tenant.id,
                name="pertama",
                token_hash=token_hash,
                token_prefix="dx_test",
                owner_user_id=user.id,
                scopes_json="[]",
            )
        )
        tenant_id, user_id = tenant.id, user.id

    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(
                ApiToken(
                    id=new_id("tok"),
                    tenant_id=tenant_id,
                    name="kedua",
                    token_hash=token_hash,
                    token_prefix="dx_test",
                    owner_user_id=user_id,
                    scopes_json="[]",
                )
            )


# --- transaksi --------------------------------------------------------------


def test_ddl_is_transactional(app):
    """PostgreSQL membatalkan DDL bila transaksi gagal — SQLite tidak."""
    table = f"tmp_probe_{_suffix()}"
    engine = get_engine()
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table} (id text)"))
            raise RuntimeError("gagal setelah DDL")

    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT to_regclass(:t) IS NOT NULL").bindparams(t=table)
        ).scalar_one()
    assert exists is False, "tabel sisa berarti DDL tidak transaksional"


def test_uncommitted_rows_are_invisible_to_other_connections(app):
    suffix = _suffix()
    engine = get_engine()
    slug = f"iso-{suffix}"
    with engine.connect() as writer:
        tx = writer.begin()
        writer.execute(
            text("INSERT INTO tenants (id, slug, name, status, settings_json, created_at, updated_at) "
                 "VALUES (:i, :s, 'Isolasi', 'active', '{}', now(), now())"),
            {"i": new_id("ten"), "s": slug},
        )
        with engine.connect() as reader:
            seen = reader.execute(
                text("SELECT count(*) FROM tenants WHERE slug = :s"), {"s": slug}
            ).scalar_one()
        assert seen == 0, "pembaca melihat baris yang belum di-commit"
        tx.rollback()


def test_row_lock_blocks_competing_writer(app):
    """`SELECT ... FOR UPDATE` benar-benar mengunci baris di PostgreSQL."""
    suffix = _suffix()
    engine = get_engine()
    with session_scope() as db:
        tenant = tenant_repo.create_tenant(db, slug=f"lock-{suffix}", name="Lock")
        tenant_id = tenant.id

    with engine.connect() as first:
        tx = first.begin()
        first.execute(
            text("SELECT id FROM tenants WHERE id = :i FOR UPDATE"), {"i": tenant_id}
        )
        with engine.connect() as second:
            second.execute(text("SET lock_timeout = '250ms'"))
            with pytest.raises(OperationalError):
                second.execute(
                    text("SELECT id FROM tenants WHERE id = :i FOR UPDATE"), {"i": tenant_id}
                )
        tx.rollback()


def test_savepoint_rollback_keeps_earlier_work(app):
    """Rollback ke savepoint tidak menghapus pekerjaan sebelumnya dalam transaksi."""
    suffix = _suffix()
    engine = get_engine()
    kept = f"sp-keep-{suffix}"
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(
            text("INSERT INTO tenants (id, slug, name, status, settings_json, created_at, updated_at) "
                 "VALUES (:i, :s, 'Simpan', 'active', '{}', now(), now())"),
            {"i": new_id("ten"), "s": kept},
        )
        nested = conn.begin_nested()
        conn.execute(
            text("INSERT INTO tenants (id, slug, name, status, settings_json, created_at, updated_at) "
                 "VALUES (:i, :s, 'Buang', 'active', '{}', now(), now())"),
            {"i": new_id("ten"), "s": f"sp-drop-{suffix}"},
        )
        nested.rollback()
        tx.commit()

    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM tenants WHERE slug = :s"), {"s": kept}
        ).scalar_one() == 1
        assert conn.execute(
            text("SELECT count(*) FROM tenants WHERE slug = :s"), {"s": f"sp-drop-{suffix}"}
        ).scalar_one() == 0
