# WorkBuddy — DEXTRA

Folder persona & artefak WorkBuddy (orchestrator DEXTRA), hasil gabungan dari
`D:\dextra\workbuddy` + paket expert `dextra-operations-team`.

## Isi

| Path | Isi |
|---|---|
| `agents/` | Persona 4 agent: `finance-agent.md`, `hr-agent.md`, `inventory-agent.md`, `operations-agent.md` (+ `dextra-operations-team-team-lead.md` koordinator tim) |
| `teams/dextra-operations-team/` | Paket expert utuh (siap import "my expert"): `.codebuddy-plugin/plugin.json`, `agents/`, `avatars/`, `settings.json`, `README.md` |
| `prompts/my-expert.md` | Prompt untuk WorkBuddy membuat file expert (Finance, HR, Inventory, Operations) |
| `mcp.json` | Konfigurasi MCP server DEXTRA (bearer `DEXTRA_AGENT_TOKEN`, ops token tidak pernah diekspos ke agent) |
| `connector-meta.json` | Metadata connector WorkBuddy |
| `icon.svg` | Ikon connector |

## Import sebagai "My Expert"

Paket `teams/dextra-operations-team/` adalah expert package yang bisa langsung
di-import. Langkahnya:

1. Salin/zip folder `teams/dextra-operations-team/` ke direktori experts:
   `C:\Users\<user>\.workbuddy-ai\plugins\marketplaces\my-experts\plugins\dextra-operations-team\`
2. Daftarkan expert-nya:
   ```bash
   python3 scripts/register_expert.py <expert-dir>
   ```
3. Expert terlihat sebagai **DEXTRA Operations Team** (tipe team; lead
   `dextra-operations-team-team-lead`, anggota: finance-agent, hr-agent,
   inventory-agent).

## Aturan

- Keempat agent tidak pernah menyetujui plan, membuat approval/mandate, atau
  mengeksekusi tindakan eksternal. Semua tindakan sensitif lewat governance
  dan tercatat di audit trail.
- `mcp.json` hanya mengekspos tool baca/buat plan ke agent; token ops
  (`execute_action`, `submit_approval`, …) tidak pernah diekspos.
