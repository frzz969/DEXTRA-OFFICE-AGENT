"""Fixture tes DEXTRA API.

Database: memakai PostgreSQL sungguhan bila `DEXTRA_TEST_DATABASE_URL` diisi
(disarankan, dan itulah yang dipakai di container). Tanpa itu, tes memakai
SQLite sementara agar tetap bisa dijalankan di mesin tanpa PostgreSQL.

Perbedaannya nyata dan tidak boleh disamarkan: constraint deferrable, locking,
dan JSONB tidak diuji di SQLite. Lihat docs/DATABASE_AUDIT.md.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _database_url() -> str:
    url = os.environ.get("DEXTRA_TEST_DATABASE_URL")
    if not url:
        tmp = Path(tempfile.mkdtemp(prefix="dextra-test-")) / "test.db"
        url = f"sqlite+pysqlite:///{tmp.as_posix()}"
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("DEXTRA_AGENT_TOKEN", "agent-dev-token")
    os.environ.setdefault("DEXTRA_OPS_TOKEN", "ops-dev-token")
    return url


@pytest.fixture(scope="session")
def app(_database_url: str):
    from app.database.base import Base
    from app.database.session import get_engine, reset_engine
    from app.main import app as fastapi_app
    import app.models  # noqa: F401  (mendaftarkan model ke metadata)

    reset_engine()
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    return fastapi_app


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def ops_headers() -> dict[str, str]:
    return {"Authorization": "Bearer ops-dev-token"}


@pytest.fixture()
def agent_headers() -> dict[str, str]:
    return {"Authorization": "Bearer agent-dev-token"}
