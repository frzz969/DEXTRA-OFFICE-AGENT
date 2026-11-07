# Scripts

Operational helper scripts for DEXTRA. These are developer conveniences; they do
not contain business logic.

## Planned

- **setup** — bootstrap local environment: copy `.env.example` → `.env`, create
  the database, and run Prisma migrations. Not implemented yet.
- **seed** — load demo data (employees, ledger, inventory, agents) for local
  development. Not implemented yet.
- **check-env** — verify toolchain versions and required environment variables
  before starting the stack.

## Available

### `check-env.mjs`

Prints the Node.js and pnpm versions and whether key environment variables are
set. It never prints secret values.

```bash
node scripts/check-env.mjs
# or
pnpm tsx scripts/check-env.mjs   # not required; plain node works
```

Exit code is `0` even when variables are missing; it reports status only.
