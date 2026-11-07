# Pull Request

## Ringkasan

<!-- Apa yang berubah dan kenapa -->

## Layer yang tersentuh

- [ ] Application (`apps/web`)
- [ ] API (`apps/api`)
- [ ] Worker (`apps/worker`)
- [ ] Intelligence (`ai-core`, `agent-runtime`, `agent-registry`, `workflow-engine`)
- [ ] Governance (`governance`, approval, audit)
- [ ] Packages pendukung

## Checklist

- [ ] `pnpm typecheck` lulus
- [ ] `pnpm lint` lulus
- [ ] `pnpm test` lulus
- [ ] Tidak menambah business logic di frontend
- [ ] Agent baru/perubahan agent melewati governance
- [ ] Tindakan penting tercatat di audit trail
