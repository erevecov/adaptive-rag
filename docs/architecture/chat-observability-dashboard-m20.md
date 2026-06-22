# M20 Chat observability dashboard

Estado: activo en planificacion.

## Decision

M20 debe avanzar como un dashboard read-only ligero dentro del frontend
existente. La fuente de verdad inicial es el contrato M17:

- `GET /projects/{project_id}/chat/observability/summary`
- `adaptive-rag chat observability summary`

La decision recomendada es empezar por frontend client y UI, no por un backend
BI nuevo. El dashboard debe consumir el summary existente y reutilizar
`GET /projects/{project_id}/chat/sessions` para salud reciente de sesiones.

El layout aprobado es hibrido: filtros superiores, metric cards, breakdowns,
provider usage table y session health table. La UI debe ser operativa y densa,
orientada a debugging local-first, no marketing.

## Alcance recomendado

- Agregar tipos y cliente frontend para
  `GET /projects/{project_id}/chat/observability/summary`.
- Agregar una vista `Chat` / `Observability` o equivalente simple dentro del
  frontend actual.
- Mostrar sesiones totales, provider calls, costo estimado conocido, errores y
  latencia etiquetada con precision.
- Mostrar breakdown de status, errores agregados y provider usage por
  operation/provider/model.
- Mostrar tabla read-only de sesiones recientes usando el endpoint de history.
- Cubrir loading, empty, error y refresh manual.

## Fuera de alcance

- Dashboard BI avanzado.
- Nuevas tablas, materialized views, OpenTelemetry, Langfuse o exporters.
- Replay, edit, delete, retention o auth final.
- Cambios de retrieval, rerank, providers, streaming o graph defaults.
- Exponer mensajes completos, respuestas completas, provider payloads, prompts,
  API keys o secretos.

## Secuencia

1. `m20-chat-observability-dashboard-plan`: completo.
2. `m20-observability-frontend-client`: completo.
3. `m20-observability-dashboard-shell`: construir filtros y metric cards.
4. `m20-observability-breakdowns`: construir breakdowns y tablas.
5. `m20-observability-summary-shape`: opcional, solo si hace falta una
   extension backward-compatible del summary.
6. `m20-quality-gate`: validar y archivar M20.

## Criterio de cierre

M20 debe cerrar cuando un usuario pueda abrir el frontend local, ingresar un
`project_id`, refrescar observability con filtros acotados y ver salud/costo/
latencia/errores de chat desde APIs publicas read-only, sin cambios de defaults
ni fuga de datos sensibles.

Spec canonica esperada:

- `openspec/specs/chat-observability/spec.md`
- `openspec/specs/chat-frontend/spec.md`
