# Propuesta M9 de calidad de retrieval/rerank

## Why

M8 dejo un harness hosted pequeno para medir calidad, usage y costo con Qwen
sin convertir la red en requisito de CI. El riesgo siguiente es mejorar ranking
sin perder la frontera que ya existe: dense retrieval exacto sigue siendo el
baseline verificable, los filtros se aplican antes del ranking y las citas
siguen ancladas al texto normalizado.

La mejora mas acotada para M9 es agregar rerank como etapa opt-in sobre
candidatos dense ya filtrados. Eso usa la infraestructura de providers y evals
existente, permite comparar calidad/costo contra el baseline de M8 y evita
mezclar en el mismo milestone lexical retrieval, RRF, dashboards o
tuning automatico.

## What Changes

- Crear el change OpenSpec `m9-retrieval-quality-rerank-plan`.
- Definir una secuencia M9 que entregue:
  `m9-rerank-provider-contract`, `m9-live-qwen-rerank-provider`,
  `m9-retrieval-rerank-service`, `m9-rerank-api-cli-surface`,
  `m9-rerank-hosted-evals` y `m9-quality-gate`.
- Introducir la capacidad `retrieval-quality` sobre `retrieval-baseline`,
  `retrieval-surface`, `provider-runtime` y `hosted-evals`.
- Exigir que retrieval dense siga siendo el comportamiento por defecto.
- Exigir que rerank sea explicito, presupuestado, acotado por candidate limit y
  medido con evals antes de convertirse en default.
- Exigir que los tests sigan usando fakes/monkeypatches y no requieran
  credenciales live.
- Mantener lexical retrieval, RRF, sparse retrieval, dashboards,
  LLM-as-judge, streaming, persistencia de retrieval runs y tuning automatico
  fuera de este milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar M9 activo y
  el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `retrieval-quality`

### Capacidades modificadas

- Ninguna. M9 consume `retrieval-baseline`, `retrieval-surface`,
  `provider-runtime` y `hosted-evals` sin cambiar sus contratos canonicos en
  este PR de planificacion.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- No requiere credenciales live para validar este PR de planificacion.
- La implementacion posterior tocara contratos de provider rerank, runtime
  Qwen, `RetrievalService`, payloads API/CLI, evals hosted y tests con fakes.

