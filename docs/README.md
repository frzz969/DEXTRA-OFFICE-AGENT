# Dokumentasi DEXTRA

Indeks seluruh dokumentasi. Dokumen arsitektur dan keputusan adalah sumber
kebenaran; status implementasi dijaga tetap jujur di
[`architecture/implementation-status.md`](architecture/implementation-status.md).

## Wajib dibaca

- [`../AGENTS.md`](../AGENTS.md) — aturan kerja untuk manusia dan coding agent.
- [`../design.md`](../design.md) — aturan visual dan design system.
- [`architecture/overview.md`](architecture/overview.md) — gambaran arsitektur.

## Arsitektur

- [overview.md](architecture/overview.md) — tiga lapisan, aplikasi, governance chain.
- [packages.md](architecture/packages.md) — peta package dan batas dependency.
- [system-design.md](architecture/system-design.md) — outline boundary dan eksekusi.
- [data-flow.md](architecture/data-flow.md) — outline alur data.
- [security.md](architecture/security.md) — keamanan dan governance.
- [implementation-status.md](architecture/implementation-status.md) — apa yang ada, stub, dan direncanakan.

## Keputusan (ADR)

- [0001-monorepo.md](decisions/0001-monorepo.md) — PNPM + Turborepo.
- [0002-backend-fastapi.md](decisions/0002-backend-fastapi.md) — backend FastAPI (Python).

## Agent

- [workbuddy.md](agents/workbuddy.md)
- [hr-agent.md](agents/hr-agent.md)
- [finance-agent.md](agents/finance-agent.md)
- [inventory-agent.md](agents/inventory-agent.md)
- [operations-agent.md](agents/operations-agent.md)

## Modul bisnis

- [human-resources.md](modules/human-resources.md)
- [finance.md](modules/finance.md)
- [inventory.md](modules/inventory.md)
- [governance.md](modules/governance.md)

## Operasional

- [api/README.md](api/README.md)
- [database/README.md](database/README.md)
- [deployment/README.md](deployment/README.md)
- [`../scripts/README.md`](../scripts/README.md) — setup dan seeding (rencana).
- [`../tests/README.md`](../tests/README.md) — strategi testing.
- [`../workflows/`](../workflows/) — contoh definisi workflow.
