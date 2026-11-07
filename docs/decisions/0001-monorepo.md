# 0001 — Monorepo dengan PNPM + Turborepo

- **Status:** accepted
- **Tanggal:** 2026-11-07

## Konteks

DEXTRA memisahkan Application, Intelligence, dan Governance layer, dengan beberapa
agent dan domain bisnis yang akan terus bertambah.

## Keputusan

Satu repository monorepo dengan PNPM workspace + Turborepo + TypeScript.

## Konsekuensi

- Satu sumber kontrak dan konfigurasi.
- Boundary antar package harus dijaga (lihat `AGENTS.md`).
- Mulai sebagai modular monolith; pisahkan service hanya bila dibutuhkan.
