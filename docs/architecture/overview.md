# Arsitektur DEXTRA — Overview

DEXTRA adalah **Governed Enterprise AI Workforce & Operations Platform**.
AI orchestration adalah pusat produk; HR, Finance, Inventory, dan Operations adalah
domain bisnis yang dikelola agent khusus di bawah governance.

## Tiga lapisan

| Lapisan              | Isi                                                          | Lokasi utama |
| -------------------- | ------------------------------------------------------------ | ------------ |
| Application Layer    | Dashboard, workspace, halaman bisnis                         | `apps/web`   |
| Intelligence Layer   | WorkBuddy, orkestrasi agent, tools, workflow                 | `packages/ai-core`, `agent-runtime`, `agent-registry`, `workflow-engine` |
| Governance Layer     | Permission, approval, policy enforcement, audit              | `packages/governance`, `apps/api` |

## Aplikasi

- `apps/web` — Next.js (App Router) dengan **Office Agent** design. Frontend
  hanya presentasi dan pemanggilan API; tidak menyimpan business logic.
- `apps/api` — **FastAPI (Python)**, hasil port dari referensi DEXTRA. Ini
  sumber kebenaran untuk auth, modul bisnis, governance, approval, dan audit.
- `apps/worker` — eksekusi asynchronous (agent, workflow, report, notifikasi,
  analytics). Status: kerangka.

> Backend sengaja Python/FastAPI, bukan TypeScript. Lihat
> [`docs/decisions/0002-backend-fastapi.md`](../decisions/0002-backend-fastapi.md).

## Alur komunikasi

```text
Web (Next.js)
   ↓ HTTP
API Layer (FastAPI: auth · modules · validation)
   ↓
WorkBuddy (orchestrator)
   ↓ delegasi
HR · Finance · Inventory · Operations agents
   ↓
Governance enforcement chain
   policy → approval → mandate → execution → audit
   ↓
Workflow Engine (execution · queue)
   ↓
PostgreSQL (business data) · Redis/Queue (async)
```

## Governance enforcement chain

Setiap tindakan agent yang menyentuh data atau aksi sensitif harus melewati
rantai berikut di backend — tanpa bypass:

1. **Policy** — evaluasi izin berdasarkan tier (`read` → `analyze` → `recommend`
   → `prepare` → `execute`) dan risk level.
2. **Approval** — aksi `prepare`/`execute` atau risiko tinggi menunggu persetujuan
   manusia.
3. **Mandate** — keputusan approval diterjemahkan menjadi mandate berbatas waktu
   dan scope untuk eksekusi.
4. **Execution** — aksi dijalankan hanya jika mandate valid.
5. **Audit** — setiap langkah dicatat ke audit trail dengan hash.

## MCP gateway (planned)

Integrasi tool eksternal direncanakan melalui **MCP gateway** di sisi backend:
satu titik masuk yang menegakkan policy, mencatat audit, dan menyembunyikan
kredensial dari agent. Belum diimplementasikan; jangan menganggapnya aktif.

## Alur contoh — laporan keuangan bulanan

1. Frontend mengirim instruksi ke API.
2. API memvalidasi identitas dan akses user.
3. WorkBuddy memahami instruksi.
4. WorkBuddy mendelegasikan analisis ke Finance Agent.
5. Agent memakai tools yang diizinkan.
6. Hasil kembali ke WorkBuddy.
7. WorkBuddy menyusun laporan.
8. Tindakan sensitif memicu approval dari governance.
9. Aktivitas dicatat di audit log.
10. Hasil tampil di dashboard.

## Prinsip

- Modular monolith lebih dulu; pisahkan service hanya bila perlu.
- Governance diperiksa di backend sebelum tindakan dijalankan.
- Semua agent melewati governance; tidak ada bypass.
- Provider AI agnostik.
- Status implementasi jujur: lihat
  [`implementation-status.md`](./implementation-status.md).
