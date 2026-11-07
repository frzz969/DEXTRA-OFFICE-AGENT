# WorkBuddy

Main AI orchestrator DEXTRA.

> Status: outline. Isi menyusul.

## Tanggung jawab

- Memahami instruksi user.
- Menyusun rencana dan mendelegasikan ke specialized agent.
- Menggabungkan hasil menjadi output akhir.
- Memastikan setiap tindakan sensitif melewati governance.

## Spesialis (4 agent)

Definisi persona ada di `workbuddy/agents/` (diadaptasi dari `D:\dextra\workbuddy`):

- `workbuddy/agents/finance-agent.md` → Finance
- `workbuddy/agents/hr-agent.md` → HR
- `workbuddy/agents/inventory-agent.md` → Inventory
- `workbuddy/agents/operations-agent.md` → Operations (koordinasi lintas domain)

Keempatnya dipanggil WorkBuddy, tidak menyetujui/membuat mandate/mengeksekusi sendiri; semua tindakan sensitif lewat `packages/governance` dan tercatat di audit trail.

## Terkait

- `workbuddy/` (connector: `connector-meta.json`, `mcp.json`, `icon.svg`; prompt generator expert: `workbuddy/prompts/my-expert.md`)
- `packages/agent-registry/src/agents/workbuddy`
- `packages/agent-runtime/src/orchestrator`
- `packages/governance`
