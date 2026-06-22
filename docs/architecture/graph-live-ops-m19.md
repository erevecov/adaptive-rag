# M19 graph live ops evidence

Fecha: 2026-06-22.

## Decision

M19 debe medir y operar Neo4j live antes de cualquier promocion de graph
retrieval. M18 dejo `strategy=graph` disponible como opt-in, pero el cierre fue
`hold_default`; por eso M19 conserva `strategy=dense` y `graph_store=disabled`
como defaults.

La meta es pasar de "la ruta existe" a "la ruta se puede correr, reconstruir y
medir con Neo4j real". Si la evidencia resulta positiva, M19 solo puede cerrar
con `limited_experiment`; un cambio de default requiere un milestone posterior.

## Alcance

- Smoke local con Docker o Neo4j Desktop.
- Smoke managed con URI cifrada `neo4j+s://...` y secretos por settings/env.
- Backfill/reindex idempotente por `project_id`.
- Transiciones claras de readiness: `pending_backfill`, `indexing`, `ready`,
  `stale` y `failed`.
- Retrieval graph live con proyeccion `ready`, filtros, citations y fallback.
- Reporte JSON de evidencia con calidad, latencia, fallback, error codes,
  duracion de backfill/reindex y costo operacional declarado.

## Fuera de alcance

- Promover `strategy=graph` como default.
- Agregar nuevos algoritmos de ranking.
- Agregar dashboards, UI o auth final.
- Convertir Neo4j en fuente durable primaria.
- Exponer secretos en logs, errores o reportes.

## Secuencia recomendada

1. `m19-graph-live-ops-plan`: planificacion y delta OpenSpec.
2. `m19-neo4j-local-managed-harness`: setup/smoke local y managed.
3. `m19-graph-backfill-reindex-ops`: completo; comandos operativos de
   backfill/reindex con readiness persistida y reporte JSON.
4. `m19-graph-live-retrieval-smoke`: smoke de retrieval graph con Neo4j real.
5. `m19-graph-live-evidence-report`: reporte comparativo live.
6. `m19-quality-gate`: validacion, decision y archive.

## Criterio de cierre

M19 cierra con una decision explicita:

- `hold_default`: graph sigue opt-in por evidencia insuficiente o regresiones.
- `limited_experiment`: graph puede probarse en proyectos acotados con fallback
  dense y monitoreo.
- `no_go_promotion`: graph queda pausado para promocion por problemas
  operativos o de calidad.

`promote_default` queda fuera de alcance de M19.
