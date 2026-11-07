# AGENTS.md

Aturan kerja untuk siapa pun (manusia atau AI coding agent) yang mengubah repo ini.

## Wajib dibaca sebelum menulis kode

1. `design.md`
2. `docs/architecture/overview.md`
3. Struktur package yang sudah ada dan dependency-nya

## Prinsip arsitektur

DEXTRA adalah **Governed Enterprise AI Workforce & Operations Platform** dengan tiga lapisan:

- **Application Layer** (`apps/web`) — dashboard, workspace, halaman bisnis.
- **Intelligence Layer** (`packages/ai-core`, `agent-runtime`, `agent-registry`, `workflow-engine`) — WorkBuddy, orkestrasi agent, tools, workflow.
- **Governance Layer** (`packages/governance`, `apps/api`) — permission, approval, policy enforcement, audit.

## Aturan keras

- Pahami arsitektur sebelum membuat fitur.
- Gunakan package yang sudah tersedia; jangan membuat package baru tanpa alasan kuat.
- Jangan menduplikasi business logic. Satu sumber kebenaran per domain.
- Jangan menaruh business logic di frontend. Frontend hanya presentasi + pemanggilan API.
- Semua agent **wajib** melewati governance. Tidak ada jalur bypass.
- Semua tindakan penting harus tercatat di audit trail.
- Gunakan shared contracts (`packages/contracts`) untuk komunikasi antarmodul.
- Validasi governance di backend, bukan hanya menyembunyikan tombol di UI.
- Jangan menampilkan eksekusi AI palsu sebagai nyata.
- Jangan overengineer. Jangan membuat microservice hanya demi terlihat kompleks.

## Dependency boundaries

- `apps/*` boleh bergantung pada `packages/*`.
- `packages/*` **tidak boleh** bergantung pada `apps/*`.
- Domain package tidak boleh saling impor melingkar; gunakan `contracts` dan `shared`.
- `governance` tidak boleh bergantung pada domain bisnis; domain bisnis bergantung pada `governance`.

## Sebelum menyelesaikan perubahan

Jalankan dan pastikan lulus:

```bash
pnpm typecheck
pnpm lint
pnpm test
```

Kerjakan bertahap. Verifikasi tiap tahap sebelum lanjut.
