"""Engine, session factory, dan dependency sesi.

Catatan jujur: mesin pengembangan di sini memakai SQLite karena PostgreSQL tidak
terpasang di mesin ini dan Docker tidak tersedia. Kode model dan migrasi ditulis
untuk PostgreSQL (UUID string, TIMESTAMPTZ, JSONB-ready) dan `DATABASE_URL`
menentukan target sebenarnya. Perilaku khas PostgreSQL — constraint deferrable,
locking, tipe JSONB — **belum terverifikasi** di sini; lihat docs/DATABASE_AUDIT.md.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pathlib import Path

from ..core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        # SQLite + FastAPI berjalan di thread berbeda; tanpa ini sesi akan gagal.
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_parent(url: str) -> None:
    """Pastikan direktori berkas SQLite ada sebelum engine membukanya."""
    if not url.startswith("sqlite"):
        return
    prefix = "sqlite+pysqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix):]
    elif url.startswith("sqlite:///"):
        raw = url[len("sqlite:///"):]
    else:
        return
    if not raw or raw == ":memory:" or raw.startswith("file:"):
        return
    Path(raw).expanduser().parent.mkdir(parents=True, exist_ok=True)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _ensure_sqlite_parent(url)
        _engine = create_engine(url, connect_args=_connect_args(url), pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def reset_engine() -> None:
    """Dipakai tes setelah DATABASE_URL diubah antar-kasus."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_health() -> dict:
    """Cek koneksi nyata, bukan sekadar status proses."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "dialect": get_engine().dialect.name}
    except Exception as exc:  # pragma: no cover - jalur kegagalan
        return {"ok": False, "error": type(exc).__name__}
