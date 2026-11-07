# Tests

## Strategy

- **Frontend / packages** — [Vitest](https://vitest.dev) for unit and integration
  tests, [Playwright](https://playwright.dev) for end-to-end flows against
  `apps/web`. Both are planned; no test runner is configured in the workspace yet.
- **Backend** — `pytest` under `apps/api/tests`. The FastAPI backend is ported
  from the DEXTRA reference and is the source of truth for governance,
  authentication and business rules.

## Boundaries

- Package tests must not import `apps/*`.
- Governance behaviour is tested in the backend (`apps/api`), not simulated in
  the frontend.
- Do not assert "AI executed" unless a real run occurred; use fixtures for
  deterministic agent scenarios.

## Running

Once configured:

```bash
pnpm test           # turbo test (JS packages + web)
cd apps/api && pytest
```
