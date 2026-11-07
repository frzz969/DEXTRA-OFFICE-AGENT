# Tests — DEXTRA API

## How to run

From the repository root:

```bash
cd apps/api
python -m pytest
```

Or from the monorepo root:

```bash
python -m pytest apps/api/tests
```

## SQLite vs PostgreSQL

By default the suite runs against a temporary SQLite database (no PostgreSQL
required). Set `DEXTRA_TEST_DATABASE_URL` to a real PostgreSQL URL to exercise
the target dialect:

```bash
DEXTRA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db python -m pytest
```

SQLite does **not** enforce foreign keys by default, has no `SELECT ... FOR
UPDATE`, and no transactional DDL. Constraints that are deferrable, locking, and
JSONB are only validated on PostgreSQL.

## Suites requiring `DEXTRA_TEST_DATABASE_URL`

- `integration/test_postgres_runtime.py` — skipped unless the URL points at
  PostgreSQL.
- `integration/test_migrations.py` — runs on SQLite too, but only exercises the
  real dialect when the URL is PostgreSQL.

## Live HTTP

No suite requires a live HTTP server; integration tests use FastAPI's
`TestClient`. Subprocess-based seed tests (`test_operational_writes_isolation.py`)
spawn `packages/database/seeds/seed.py` and require the repo layout to be intact.
