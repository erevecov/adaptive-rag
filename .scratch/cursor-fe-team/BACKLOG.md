# FE UI/UX Backlog (Cursor team)

Status: open | claimed:<role> | done | deferred

Branch: `feat/ui-obsessional-polish` (from main post-#206)

## Seed themes
- [x] done:chat — Chat: multi-turn transcript density vs single-response layout
- [x] done:chat — Composer: mobile touch targets, sticky behavior
- [x] done:chat — Session rail: long titles, training icon affordance, empty per filter
- [x] done:chat — Inspector: focus trap completeness, source viewer density
- [ ] claimed:fe-operator — Authoring forms: field density, binary upload feedback
- [ ] claimed:fe-operator — Ingestion jobs: relative times, grouping by status
- [ ] claimed:fe-operator — Observability: chart/metric empty vs failed
- [ ] claimed:fe-operator — Retrieval playground: result rank cards polish
- [ ] claimed:fe-operator — Runtime settings: secret-safe copy, connection status clarity
- [ ] claimed:fe-operator — Knowledge status truth + draft card affordances
- [ ] claimed:fe-operator — CapabilitySelector ARIA + observability tablist
- [ ] open — Global: focus-visible consistency, reduced-motion micro-animations
- [ ] open — Global: purple/dark contrast pass

## Chat+Shell pass 1 findings

### P0 — done
- [x] done:chat — Cancel/fail mid-stream looks like success
- [x] done:chat — Enter while asking starts parallel request
- [x] done:chat — Hamburger z pierces inspector scrim
- [x] done:chat — Closed sidebar still in tab order
- [x] done:chat — Inspector overlay without inert on chat host / focusable backdrop

### P1 — done
- [x] done:chat — Pipeline streaming aria-expanded + composed label + tabular-nums
- [x] done:chat — Pipeline StatusDot SR + summary focus ring + chip wrap
- [x] done:chat — Composer rings / Escape-cancel / citation Open source / response region
- [x] done:chat — Session EmptyState; training aria-label; detail error alert
- [x] done:chat — Escape coordination; backdrop tabIndex=-1; overlay focus close

### Deferred P2
- [ ] deferred — Full Tab-cycle focus trap beyond inert
- [ ] deferred — Speech status mobile width
- [ ] deferred — Soft-delete casing; rename blur-save; minimap label truncate

Report: `.scratch/cursor-fe-team/reports/chat-latest.md` · STATUS ready-for-lead-review
