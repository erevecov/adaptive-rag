# Propuesta M10 de datasets y decision gates de retrieval

## Why

M9 cerro rerank opt-in y una primera comparacion dense vs reranked retrieval
con usage/cost. Eso prueba la ruta tecnica, pero los fixtures actuales siguen
siendo smokes pequenos: validan conectividad, no alcanzan para decidir si el
siguiente incremento debe ser lexical retrieval, RRF, sparse retrieval,
tuning de candidate limits o solo mejores suites.

El siguiente riesgo es implementar mas ranking sin evidencia suficiente. M10
debe ampliar el harness de evals para que las decisiones de calidad se apoyen
en suites versionadas, metricas por caso mas utiles y decision gates explicitos
antes de agregar mas algoritmos al runtime.

## What Changes

- Crear el change OpenSpec `m10-retrieval-eval-datasets-plan`.
- Definir una secuencia M10 que entregue:
  `m10-eval-case-metrics`, `m10-retrieval-dataset-pack`,
  `m10-rerank-ab-reporting`, `m10-decision-gate-docs` y
  `m10-quality-gate`.
- Modificar la capacidad `retrieval-quality` para exigir:
  - suites de retrieval versionadas con casos diversos y metadata de intencion;
  - metricas por caso que distingan hit, best rank, matched count y degradacion;
  - reportes comparativos que indiquen ganancia, empate o regresion frente a
    dense baseline;
  - decision gates antes de aprobar lexical/RRF, sparse retrieval o tuning
    automatico.
- Mantener dense retrieval y rerank como las unicas estrategias productivas en
  M10, salvo que un slice posterior se apruebe explicitamente con evidencia.
- Mantener dashboards, LLM-as-judge, persistencia de retrieval runs,
  endpoints HTTP de evals y tuning automatico fuera de este milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar M10 activo y
  el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- Ninguna.

### Capacidades modificadas

- `retrieval-quality`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- No requiere credenciales live para validar este PR de planificacion.
- La implementacion posterior tocara `adaptive_rag.evals`, fixtures bajo
  `evals/fixtures/`, reportes JSON y docs de decision. Solo tocara retrieval
  productivo si un slice posterior queda justificado por evals.

