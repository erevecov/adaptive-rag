# Tareas M20 de dashboard de observability de chat

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M19 esta mergeado, archivado y cerrado con decision
  `hold_default`.
- [x] 1.2 Crear branch `codex/m20-chat-observability-dashboard-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M19.
- [x] 1.4 Aprobar direccion de UI con visual companion: layout hibrido con
  filtros, metric cards, breakdowns, provider usage y session health.

## 2. Change OpenSpec de M20

- [x] 2.1 Agregar propuesta, diseno, tasks y deltas de spec para
  `m20-chat-observability-dashboard-plan`.
- [x] 2.2 Documentar que M20 empieza consumiendo el endpoint M17 y los
  endpoints M14/M15 existentes, sin crear dashboard BI ni tablas nuevas.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M20 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m20-chat-observability-dashboard-plan
  --strict`, `openspec validate --specs --strict`, `openspec list` y
  `git diff --check`.

## 3. Slices propuestos de M20

- [x] 3.1 Implementar `m20-observability-frontend-client`.
- [ ] 3.2 Implementar `m20-observability-dashboard-shell`.
- [ ] 3.3 Implementar `m20-observability-breakdowns`.
- [ ] 3.4 Abrir `m20-observability-summary-shape` solo si el dashboard necesita
  campos agregados que el summary M17 no puede representar sin ambiguedad.
- [ ] 3.5 Ejecutar `m20-quality-gate` y archivar el change cuando se complete.
