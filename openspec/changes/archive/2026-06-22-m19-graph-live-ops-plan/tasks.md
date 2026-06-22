# Tareas M19 de graph live ops evidence

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M18 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m19-graph-live-ops-plan` desde el `origin/main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M18.
- [x] 1.4 Confirmar que M19 queda acotado a evidencia/operacion graph live, sin
  cambiar defaults ni promover `strategy=graph`.

## 2. Change OpenSpec de M19

- [x] 2.1 Agregar propuesta, diseno, tasks y delta de spec para
  `m19-graph-live-ops-plan`.
- [x] 2.2 Documentar setup local/managed, backfill/reindex, smokes live,
  evidencia de latencia/costo y gate de decision.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M19 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m19-graph-live-ops-plan --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M19

- [x] 3.1 Implementar `m19-neo4j-local-managed-harness`.
- [x] 3.2 Implementar `m19-graph-backfill-reindex-ops`.
- [x] 3.3 Implementar `m19-graph-live-retrieval-smoke`.
- [x] 3.4 Implementar `m19-graph-live-evidence-report`.
- [x] 3.5 Ejecutar `m19-quality-gate` y archivar el change cuando se complete.
