# Propuesta M6 de evals

## Why

M5 cerro una capa de chat/tool calling sobre retrieval con citations
verificables, API y CLI, pero el sistema todavia no tiene una forma canonica de
medir si un cambio mejora o rompe calidad. El riesgo inmediato es avanzar hacia
streaming, persistencia de conversaciones o providers live sin un harness que
detecte regresiones en retrieval, groundedness y citations.

M6 debe definir primero evaluaciones offline y reproducibles sobre las
superficies ya cerradas. El objetivo no es maximizar metricas con modelos live,
sino construir un contrato pequeno para datasets versionados, runners
deterministas, metricas agregadas y reportes JSON que puedan usarse en CI y en
iteracion local.

## What Changes

- Crear el change OpenSpec `m6-evals-plan`.
- Definir una secuencia M6 que entregue:
  `m6-evals-fixtures-contract`, `m6-retrieval-eval-runner`,
  `m6-chat-eval-runner`, `m6-evals-cli-reporting` y `m6-quality-gate`.
- Introducir la capacidad `evals-baseline` como contrato nuevo sobre
  `retrieval-surface` y `chat-tool-calling`.
- Exigir datasets locales versionados, pequenos y deterministas, con casos de
  retrieval y chat anclados a expected citations/evidence.
- Exigir runners que reutilicen `RetrievalService`, `ChatService` y providers o
  runners fake; no deben llamar a red ni depender de credenciales.
- Exigir reportes JSON con resultados por caso, metricas agregadas, umbrales y
  exit code estable para regresiones.
- Mantener providers live, LLM-as-judge hosted, UI, dashboards, persistencia de
  historiales, streaming y tuning automatico fuera de este milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar M6 activo y
  el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `evals-baseline`

### Capacidades modificadas

- Ninguna. M6 consume las specs canonicas de retrieval/chat sin cambiar sus
  contratos publicos.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- No requiere credenciales de providers live.
- La implementacion posterior tocara un paquete nuevo `adaptive_rag.evals`,
  un subcomando CLI y tests deterministas sobre fixtures locales.

