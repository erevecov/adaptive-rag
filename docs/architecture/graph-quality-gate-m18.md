# M18 graph quality gate

Fecha: 2026-06-22.

## Decision

M18 cierra con graph retrieval en estado opt-in. `strategy=dense` sigue siendo
el default y `strategy=graph` queda disponible para experimentos controlados
cuando la proyeccion del proyecto esta `ready`.

El gate compara dense baseline vs graph-enabled retrieval en el mismo fixture
versionado y toma una decision conservadora: `hold_default`.

## Implementacion

- `run_graph_quality_gate_eval_suite(...)` construye el fixture de evals una
  vez y ejecuta dense baseline y `strategy=graph` sobre los mismos casos.
- El gate marca la proyeccion del fixture como `ready` en Postgres para ejercer
  el contrato real de fallback/readiness.
- El graph retriever offline es determinista y no requiere Neo4j live, Docker,
  Aura ni credenciales.
- `adaptive-rag evals graph-quality-gate <suite>` serializa el reporte desde
  CLI.

## Metricas

- `dense_retrieval_hit_rate`
- `graph_retrieval_hit_rate`
- `graph_retrieval_hit_rate_delta`
- `graph_case_improvement_count`
- `graph_case_tie_count`
- `graph_case_regression_count`
- `graph_best_rank_delta_avg`
- `graph_metadata_filter_case_count`
- `graph_metadata_filter_passed_count`
- `graph_citation_coverage`
- `graph_provider_cost_delta_usd`

## Resultado M18

El gate permite validar que graph retrieval preserve calidad, filtros y
citations frente al baseline. No promueve graph como default; cualquier cambio
futuro de default debe abrir un nuevo milestone con evidencia adicional de
latencia/costo operativo en un entorno graph live.
