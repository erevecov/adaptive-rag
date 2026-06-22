# Tareas M18 de Neo4j graph DB decision

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M17 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m18-neo4j-graph-db-decision` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M17.
- [x] 1.4 Confirmar que M18 queda acotado a decision/plan routeable, sin
  dependencias Neo4j, settings productivos, migrations, adapter live, indexer ni
  cambios de retrieval defaults en este PR.

## 2. Change OpenSpec de M18

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m18-neo4j-graph-db-decision`.
- [x] 2.2 Documentar decision matrix, alternativas, routeability, ownership de
  datos, health checks y gates de evals.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M18 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m18-neo4j-graph-db-decision --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M18

- [x] 3.1 Implementar `m18-graph-db-decision-matrix`.
- [x] 3.2 Implementar `m18-graph-store-contract`, incluyendo
  readiness/backfill por proyecto en Postgres antes del adapter live.
- [x] 3.3 Implementar `m18-neo4j-adapter-and-health`.
- [x] 3.4 Implementar `m18-neo4j-indexer`.
- [x] 3.5 Implementar `m18-graph-retrieval-route`.
- [ ] 3.6 Ejecutar `m18-evals-quality-gate` y archivar el change cuando se
  complete.
