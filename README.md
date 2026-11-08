# DEXTRA

**Governed Enterprise AI Workforce & Operations Platform.**

DEXTRA menggabungkan tiga lapisan dalam satu platform:

- **Application Layer** — dashboard, workspace, dan halaman bisnis.
- **Intelligence Layer** — WorkBuddy, agent orchestration, tools, dan workflow.
- **Governance Layer** — permissions, approval, policy enforcement, dan audit trail.

AI orchestration adalah pusat produk. HR, Finance, Inventory, dan Operations adalah
domain bisnis yang dikelola oleh agent khusus di bawah pengawasan governance.

## Stack

| Area               | Keputusan                        |
| ------------------ | -------------------------------- |
| Repository         | Monorepo                         |
| Monorepo tooling   | Turborepo                        |
| Package manager    | PNPM                             |
| Language           | TypeScript                       |
| Frontend           | Next.js (App Router), Office Agent design |
| Backend            | FastAPI (Python), ported from DEXTRA reference |
| Database           | SQLite (dev) / PostgreSQL (target) |
| ORM                | SQLAlchemy 2 + Alembic           |
| Queue              | Belum ada; `apps/worker` masih kerangka |
| Validation         | Pydantic (backend); belum ada skema Zod bersama |
| UI                 | Tailwind + reusable components   |
| AI                 | Provider-agnostic; belum ada provider terpasang di backend |
| Agent architecture | Kontrak orchestration; runtime agent belum berjalan |
| Governance         | RBAC + capability + policy/approval/mandate |
| Testing            | pytest (backend). Runner JS belum terpasang |

## Struktur

```text
apps/        web, api, worker
packages/    ui, design-system, database, contracts, auth,
             ai-core, agent-runtime, agent-registry, governance,
             workflow-engine, integrations, notifications,
             analytics, shared, config
workflows/   definisi workflow AI
docs/        arsitektur, agent, modul, API, database, deployment, decisions
```

## Mulai

```bash
pnpm install
pnpm dev        # turbo dev
pnpm typecheck
pnpm lint
pnpm test
```

## Dokumen wajib

- `AGENTS.md` — aturan kerja untuk coding agent.
- `design.md` — aturan visual dan design system.
- `docs/README.md` — indeks seluruh dokumentasi.
- `docs/architecture/overview.md` — gambaran arsitektur.
- `docs/architecture/implementation-status.md` — status implementasi yang jujur.

> Backend adalah FastAPI (Python) yang diport dari referensi DEXTRA; lihat
> `docs/decisions/0002-backend-fastapi.md`.

> Catatan: ini target architecture. Mulai sebagai modular monolith; pisahkan service
> hanya bila benar-benar dibutuhkan.
