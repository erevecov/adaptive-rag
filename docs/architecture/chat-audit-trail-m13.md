# M13 Chat audit trail

## Decision

M13 debe avanzar con persistencia durable de chat antes de streaming SSE,
dashboards, historial de sesiones o nuevos cambios de retrieval.

La razon es operativa: el sistema ya puede responder con citations y tool
calling, pero una corrida conversacional todavia no deja un registro durable que
una mensajes, tool calls, retrieval runs, citations y usage/cost. Sin ese
registro, debugging, costo, streaming y reportes futuros quedan sin una fuente
de verdad reproducible.

## Alcance recomendado

- Crear `chat_sessions`, `chat_messages`, `tool_calls`, `retrieval_runs`,
  `retrieved_chunks` y `provider_usage`.
- Agregar repositories con aislamiento por `project_id`.
- Integrar la escritura del audit trail en `ChatService`.
- Hacer que API/CLI de chat persistan la corrida sin cambiar el contrato
  principal.
- Exponer solo metadata minima de trazabilidad, como `session_id`, si el spec lo
  requiere.

## Fuera de alcance

- Streaming SSE y WebSockets.
- Endpoints o comandos para historial de sesiones.
- Dashboard de costo/latencia.
- OpenTelemetry exporter.
- LLM-as-judge persistido.
- Cambios de ranking, rerank, lexical/RRF, sparse retrieval o defaults.

## Secuencia

1. `m13-audit-schema`
2. `m13-audit-repositories`
3. `m13-chat-service-audit-wiring`
4. `m13-api-cli-audit-surface`
5. `m13-provider-usage-linking`
6. `m13-quality-gate`

## Criterio de cierre

M13 queda listo cuando una request de chat exitosa y una corrida fallida dejan
audit trail consistente, sin secretos, con citations que correspondan a
retrieval real o fake deterministico, y con usage/cost vinculado cuando exista.
