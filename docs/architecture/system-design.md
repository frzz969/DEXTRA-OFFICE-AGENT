# System Design

> Status: outline. Isi menyusul.

## Bagian

1. Boundary antar package dan arah dependency.
2. Kontrak antar layer (Application → Intelligence → Governance).
3. Model eksekusi agent (sync request vs async worker).
4. State management eksekusi dan retry.
5. Persistensi: PostgreSQL, Redis, queue.
6. Observability dan audit.

## Aturan dependency

- `apps/*` → `packages/*`
- `packages/*` ⇏ `apps/*`
- `governance` tidak bergantung pada domain bisnis.
- Komunikasi lintas domain lewat `contracts`/`shared`, bukan impor langsung.
