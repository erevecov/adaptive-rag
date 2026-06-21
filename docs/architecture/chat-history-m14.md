# M14 Chat history/read surface

## Decision

M14 cerro una superficie read-only para consultar sesiones de chat persistidas
antes de construir frontend, streaming SSE o dashboards.

La razon es que M13 ya dejo una fuente durable para sesiones, mensajes, tool
calls, retrieval runs, citations y usage/cost. M14 fijo el contrato publico para
leer esos datos de forma aislada por proyecto. Un frontend estable debe consumir
ese contrato de listado/detalle.

## Alcance recomendado

- Listar sesiones por proyecto con status, limite y paginacion deterministica.
- Mostrar detalle de una sesion con mensajes, tool calls, retrieval runs,
  retrieved chunks/citations y provider usage.
- Agregar comandos CLI equivalentes para QA y debugging local.
- Mantener salida JSON estable para que la futura UI no dependa de queries
  internas.

## Fuera de alcance

- Frontend.
- Streaming SSE y WebSockets.
- Replay/re-run de sesiones.
- Dashboard de costo/latencia.
- Edicion, borrado o retencion de sesiones.
- Cambios de ranking, retrieval, rerank, providers o defaults.

## Secuencia

1. `m14-chat-history-read-surface`: completo.
2. `m14-chat-history-repository-read-models`: completo.
3. `m14-chat-history-api`: completo.
4. `m14-chat-history-cli`: completo.
5. `m14-quality-gate`: completo y archivado.

## Criterio de cierre

M14 queda cerrado porque API y CLI pueden listar y mostrar sesiones de chat
persistidas con aislamiento por proyecto, orden estable, limites acotados y sin
mutar el audit trail ni exponer secretos.
