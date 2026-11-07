# 0002 — Backend FastAPI (Python) hasil port referensi

- **Status:** accepted
- **Tanggal:** 2026-11-07

## Konteks

Referensi DEXTRA menyediakan backend yang sudah berjalan dengan model governance,
approval, mandate, auth, dan MCP registry. Menulis ulang seluruh perilaku
tersebut di TypeScript berisiko kehilangan detail keamanan dan memperlambat
peluncuran. Workspace monorepo sudah memiliki `apps/api` yang kini diisi dengan
port FastAPI.

## Keputusan

Backend `apps/api` adalah **FastAPI (Python)**, diport dari referensi DEXTRA.
`apps/web` tetap Next.js + TypeScript. Package TypeScript di `packages/*`
menyediakan kontrak dan tipa bersama, bukan implementasi backend.

## Konsekuensi

Positif:

- Perilaku governance/approval/auth mengikuti implementasi referensi yang sudah
  teruji, bukan reimplementasi berisiko.
- Ekosistem Python untuk keamanan (hash, MFA/TOTP, validasi) dan tooling data.
- Migrasi bertahap: web dan package bisa berjalan lebih dulu.

Negatif / trade-off:

- Dua bahasa di satu repo (TypeScript + Python) → boundary kontrak harus
  eksplisit; tidak ada tipe bersama otomatis antara `packages/contracts` dan
  model Python.
- CI membutuhkan dua toolchain (Node + Python); job backend ditandai
  `continue-on-error` selama port masih stabil.
- Duplikasi tipe domain mungkin terjadi; jaga `packages/contracts` sebagai
  rujukan dan dokumentasikan perbedaannya.

## Alternatif yang ditolak

- **Backend TypeScript penuh** — konsisten satu bahasa, tetapi menulis ulang
  governance yang sudah ada berisiko dan mahal.
- **Backend sebagai service terpisah di repo lain** — memisahkan kontrak terlalu
  awal; monorepo lebih sederhana untuk fase ini.
