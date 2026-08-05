# FE UI/UX Backlog (Cursor team)

Status: open | claimed:<role> | done | deferred

Branch: `feat/ui-obsessional-polish` (post-#206/#207/#208)

## Seed themes
- [x] done:chat — Chat / composer / session rail / inspector (pass 1)
- [ ] claimed:fe-operator — Authoring / ingestion / observability / retrieval / runtime
- [x] done:chat — Global: purple primary focus ring solid (pass 2)
- [x] done:chat — Global: knowledge draft ring aligns to DS (pass 2)
- [ ] open — Global: remaining focus-visible / motion sweep outside chat

## Chat+Shell pass 2

### P0 — done
- [x] done:chat — Primary button `ring-primary-foreground` (no /55) for purple AA
- [x] done:chat — Knowledge draft textarea full `ring-ring` + offset-2

### P1 — done
- [x] done:chat — Overlay inert hosts (sidebar/topline) — already on tip
- [x] done:chat — Soft-delete badge `Deleted`; cascade `source removed`
- [x] done:chat — Minimap aria truncation; speech mobile full-width status
- [x] done:chat — History skeletons `motion-safe`; AppShell width transition
- [x] done:chat — Rename blur saves when dirty (unchanged blur cancels)

### Deferred
- [ ] deferred — Locale mix EN chrome vs ES rail (copy pass)
- [ ] deferred — Inspector Escape gated to overlay only (if undesired on inline)

Report: `.scratch/cursor-fe-team/reports/chat-latest.md`
