# Peta Package

Status: deskriptif. Menjelaskan package yang ada di workspace dan batas
dependency yang dijaga. Untuk status implementasi lihat
[`implementation-status.md`](./implementation-status.md).

## Package

| Package | Tanggung jawab | Status |
| --- | --- | --- |
| `packages/contracts` | Tipe domain bersama (single source of truth) | Ada, dipakai web |
| `packages/shared` | Primitif tanpa dependency (`Result`, `Brand`, util) | Ada |
| `packages/config` | Konstanta dan catatan preset build | Ada (minimal) |
| `packages/governance` | Tipe permission tier, risk level, decision | Tipe + helper; enforcement di `apps/api` |
| `packages/ai-core` | Kontrak adapter provider AI | Tipe/interface |
| `packages/agent-runtime` | Eksekusi satu run agent | Tipe/interface |
| `packages/agent-registry` | Katalog agent + in-memory registry | Minimal, ada implementasi in-memory |
| `packages/workflow-engine` | Definisi dan run workflow | Tipe/interface |
| `packages/auth` | Tipe principal, session, provider | Tipe/interface |
| `packages/integrations` | Kontrak adapter integrasi | Tipe/interface |
| `packages/notifications` | Kontrak transport notifikasi | Tipe/interface |
| `packages/analytics` | Kontrak metric sink/query | Tipe/interface |
| `packages/database` | Skema dan akses data | Dimiliki lane backend |
| `packages/ui` | Komponen reusable | Ada |
| `packages/design-system` | Token dan theme | Ada |

## Aplikasi

| App | Tanggung jawab |
| --- | --- |
| `apps/web` | Next.js App Router + Office Agent design. Hanya presentasi. |
| `apps/api` | FastAPI (Python), port referensi. Auth, governance, modul bisnis, audit. |
| `apps/worker` | Kerangka eksekusi asynchronous. |

## Batas dependency

```text
apps/*  ──→  packages/*
packages/*  ──✕──→  apps/*
```

- `apps/*` boleh bergantung pada `packages/*`; sebaliknya dilarang.
- `governance` tidak boleh bergantung pada domain bisnis. Domain bisnis
  bergantung pada governance, bukan sebaliknya.
- Komunikasi lintas domain lewat `contracts`/`shared`, bukan impor langsung.
- Hindari siklus antar package. Saat ini package intelligence/governance
  sengaja dependency-free (tidak mengimpor `contracts`) untuk menjaga batas.
- `contracts` adalah sumber tipe domain; `governance` menduplikasi `RiskLevel`
  secara sadar agar tetap tanpa dependency.
