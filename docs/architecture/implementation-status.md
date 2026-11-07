# Status Implementasi

Status: **jujur per 2026-11-07**. Jangan menandai sesuatu "selesai" tanpa kode
yang benar-benar berjalan. Dokumen ini memperbarui dirinya saat lane lain
(backend FastAPI) berkembang.

Legenda: ✅ ada dan berfungsi · 🟡 ada sebagian/stub · ⬜ direncanakan.

## Aplikasi

| Area | Status | Catatan |
| --- | --- | --- |
| `apps/web` — Next.js App Router | ✅ | 20 rute build sukses (webpack; Turbopack tidak tersedia di Android/arm64) dan smoke 200 |
| `apps/web` — Office Agent design | ✅ | 14 view + shell + auth diport dari prototipe Office Agent, tetap memakai mock store |
| `apps/web` — integrasi API | ⬜ | UI masih memakai `mock-store.ts`, belum memanggil `/api/v1` |
| `apps/api` — FastAPI port | 🟡 | Sedang diport dari referensi (lane lain); model, auth, governance, MCP ada sebagian |
| `apps/api` — governance chain | 🟡 | File policy/approval/mandate ada; integrasi end-to-end belum diverifikasi |
| `apps/api` — MCP gateway | 🟡 | `app/mcp/registry.py` ada; gateway penuh belum |
| `apps/worker` — async execution | ⬜ | Hanya `main.py` kerangka |

## Package TypeScript

| Package | Status | Catatan |
| --- | --- | --- |
| `contracts` | ✅ | Tipe domain dipakai `apps/web` |
| `shared` | ✅ | `Result`, `Brand`, `compact` |
| `config` | 🟡 | Konstanta + catatan preset; preset build belum |
| `governance` | 🟡 | Tipe tier/risk + helper; enforcement nyata di backend |
| `ai-core` | 🟡 | Kontrak adapter; belum ada provider terpasang |
| `agent-runtime` | 🟡 | Interface saja; pipeline belum |
| `agent-registry` | 🟡 | Registry in-memory; sinkron backend belum |
| `workflow-engine` | 🟡 | Tipe definisi/run; scheduler belum |
| `auth` | 🟡 | Tipe session/principal; implementasi di backend |
| `integrations` | 🟡 | Kontrak adapter; belum ada konektor |
| `notifications` | 🟡 | Kontrak transport; pengiriman belum |
| `analytics` | 🟡 | Kontrak metric; storage belum |
| `ui`, `design-system` | 🟡 | Lane UI; bukan milik dokumen ini |
| `database` | 🟡 | Lane backend |

## Tooling & operasional

| Item | Status | Catatan |
| --- | --- | --- |
| pnpm + Turborepo | ✅ | Workspace inti |
| `pnpm typecheck` per package | ✅ | `tsc --noEmit` untuk setiap package |
| CI (`.github/workflows/ci.yml`) | 🟡 | JS job aktif; job Python `continue-on-error` |
| Vitest / Playwright | ⬜ | Direncanakan (lihat `tests/README.md`) |
| `scripts/check-env.mjs` | ✅ | Cek versi + env tanpa membocorkan nilai |
| Setup & seeding scripts | ⬜ | Direncanakan (lihat `scripts/README.md`) |
| Workflow contoh (`workflows/`) | ✅ | Definisi contoh; belum dieksekusi runtime |

## Aturan kejujuran

- Jangan menampilkan eksekusi AI palsu sebagai nyata.
- Jangan menandai integrasi "connected" sebelum benar-benar tersambung.
- Perbarui tabel ini setiap kali sebuah area naik status.
