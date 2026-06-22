# M19 graph live ops evidence

Fecha: 2026-06-22.

## Decision

M19 midio y operativizo Neo4j live antes de cualquier promocion de graph
retrieval. M18 dejo `strategy=graph` disponible como opt-in y M19 conserva la
decision `hold_default`; por eso `strategy=dense` y `graph_store=disabled`
siguen como defaults.

El repo ahora puede ejecutar smoke de conectividad, backfill/reindex, smoke de
retrieval graph y reporte de evidencia consolidada. El gate local no tuvo
entorno Neo4j live configurado, por lo que no existe evidencia concluyente de
latencia/costo operacional para avanzar a `limited_experiment`.

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

1. `m19-graph-live-ops-plan`: completo; planificacion y delta OpenSpec.
2. `m19-neo4j-local-managed-harness`: completo; setup/smoke local y managed.
3. `m19-graph-backfill-reindex-ops`: completo; comandos operativos de
   backfill/reindex con readiness persistida y reporte JSON.
4. `m19-graph-live-retrieval-smoke`: completo; smoke de retrieval graph con
   proyeccion `ready`, filtros, citations, latencia y fallback visible.
5. `m19-graph-live-evidence-report`: completo; reporte comparativo live que
   consolida calidad dense-vs-graph, artefactos backfill/reindex, retrieval
   smoke, error codes, latencia/fallback y costo operacional declarado.
6. `m19-quality-gate`: completo; validacion, decision `hold_default` y archive.

## Criterio de cierre

M19 cierra con una decision explicita:

- `hold_default`: graph sigue opt-in por evidencia insuficiente o regresiones.
- `limited_experiment`: graph puede probarse en proyectos acotados con fallback
  dense y monitoreo.
- `no_go_promotion`: graph queda pausado para promocion por problemas
  operativos o de calidad.

Decision final: `hold_default`. `promote_default` queda fuera de alcance de M19.
Un cambio futuro requiere un milestone posterior con rollout, rollback,
observability y evidencia live real.
