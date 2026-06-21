# M17 Chat observability y costo-latencia

Estado: completo y archivado.

## Decision

M17 debe avanzar como una superficie read-only de observability local-first
para chat, costo y latencia. La fuente de verdad son las tablas existentes del
audit trail: `chat_sessions`, `tool_calls`, `retrieval_runs` y
`provider_usage`.

La decision recomendada es empezar por API y CLI, no por frontend. Esto fija un
contrato estable para demos, reportes y automatizacion antes de decidir si una
UI o dashboard ligero aporta valor. M17 no debe crear un dashboard avanzado,
OpenTelemetry, exporters hosted ni nuevas tablas obligatorias.

## Alcance recomendado

- Agregar read models de observability por proyecto.
- Exponer `GET /projects/{project_id}/chat/observability/summary`.
- Exponer `adaptive-rag chat observability summary`.
- Resumir sesiones por status.
- Resumir provider usage por operation/provider/model.
- Reportar costo conocido, missing cost count, tokens/unidades conocidas y
  latencias.
- Agrupar errores de forma segura sin raw provider payloads ni mensajes
  completos.

## Fuera de alcance

- Dashboard avanzado o frontend obligatorio.
- OpenTelemetry, Langfuse o exporters hosted.
- Nuevas tablas o materialized views en el primer slice.
- Replay, edit, delete o retention de sesiones.
- Auth final.
- Cambios de retrieval, rerank, providers, streaming o historial.

## Secuencia

1. `m17-chat-observability`: completo.
2. `m17-observability-read-models`: completo.
3. `m17-observability-api`: completo.
4. `m17-observability-cli`: completo.
5. `m17-quality-gate`: completo.

## Criterio de cierre

M17 cerro cuando API y CLI pudieron producir el mismo resumen JSON estable de
sesiones, usage/costo, latencia y errores por proyecto, con filtros acotados y
sin exponer contenido sensible.

Archive:

- `openspec/changes/archive/2026-06-21-m17-chat-observability/`

Spec canonica:

- `openspec/specs/chat-observability/spec.md`
