# Teams — paket expert siap import

Setiap subfolder adalah satu paket expert utuh (format WorkBuddy "my expert":
`.codebuddy-plugin/plugin.json` + `agents/` + `avatars/` + `settings.json`).

- `dextra-operations-team/` — Tim operasional lintas domain (Finance, HR,
  Inventory) dengan koordinator `dextra-operations-team-team-lead`.
  Lihat `dextra-operations-team/README.md` untuk detail dan cara import.

Cara import: salin folder paket ke
`C:\Users\<user>\.workbuddy-ai\plugins\marketplaces\my-experts\plugins\`,
lalu jalankan `python3 scripts/register_expert.py <expert-dir>`.
