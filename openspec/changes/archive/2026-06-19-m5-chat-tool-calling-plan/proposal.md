# Propuesta M5 de chat/tool calling

## Why

M4 dejo una superficie API/CLI estable para ejecutar retrieval con query text,
filtros tipados y citations, pero el sistema todavia no tiene una capa
conversacional que decida cuando recuperar contexto y como responder usando
evidencia. El siguiente riesgo es implementar chat directamente en API o CLI y
duplicar logica de retrieval, payloads o manejo de providers.

M5 debe definir primero el contrato conversacional sobre la superficie M4:
un servicio compartido que expone chat/tool calling, usa retrieval como tool
tipada y mantiene respuestas verificables con citations, fakes deterministas y
adaptadores API/CLI delgados.

## What Changes

- Crear el change OpenSpec `m5-chat-tool-calling-plan`.
- Definir una secuencia M5 que entregue:
  `m5-chat-service-contract`, `m5-chat-api-endpoint`,
  `m5-chat-cli-command` y `m5-quality-gate`.
- Introducir la capacidad `chat-tool-calling` como contrato nuevo, sin cambiar
  los requisitos canonicos de `retrieval-surface`.
- Exigir que la capa chat reutilice `RetrievalService` y payloads compartidos
  en vez de llamar directamente a `DenseRetriever` desde API/CLI.
- Mantener streaming, persistencia de conversaciones, auth, evals, rerank,
  retrieval hibrido y providers live obligatorios fuera de este milestone
  inicial.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar el change
  activo y el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `chat-tool-calling`

### Capacidades modificadas

- Ninguna. `retrieval-surface` queda como dependencia estable que M5 consume.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- La implementacion posterior tocara modulos de `adaptive_rag.chat`,
  dependencias API/CLI y tests deterministas con modelos/providers fake.
