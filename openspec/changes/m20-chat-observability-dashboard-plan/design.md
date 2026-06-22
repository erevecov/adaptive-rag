# Diseno M20 de dashboard de observability de chat

## Contexto

M13 dejo audit trail durable. M14 expuso historial read-only. M15 agrego el
frontend inicial, M16 sumo streaming SSE y M17 agrego observability local-first
por API/CLI con:

```text
GET /projects/{project_id}/chat/observability/summary
adaptive-rag chat observability summary --project-id <uuid>
```

El shape M17 ya contiene:

- `sessions.total` y `sessions.by_status`;
- `provider_usage.total_records`;
- `provider_usage.total_estimated_cost_usd`;
- `provider_usage.missing_cost_count`;
- `provider_usage.groups[]` por `operation`, `provider` y `model`;
- `provider_usage.groups[].latency_ms`;
- `errors.session_error_count`, `errors.provider_error_count` y
  `errors.top_messages`.

El frontend actual ya tiene un `ApiClient` tipado y tests con fakes. La
integracion M20 debe seguir ese patron: primero tipos/cliente, luego UI, luego
estados y gate.

## Decision

La decision recomendada es `proceed` con un dashboard read-only ligero dentro
del frontend existente. El dashboard debe consumir el contrato M17 y los
endpoints M14/M15/M16 existentes antes de pedir backend nuevo.

El layout aprobado es hibrido:

- filtro superior por `project_id`, fecha desde/hasta, `status` y refresh;
- tarjetas para sesiones, provider calls, costo estimado y errores;
- tarjeta/panel de latencia etiquetado segun la derivacion real disponible;
- breakdown de status y errores;
- tabla de provider usage por operation/provider/model;
- tabla de sesiones recientes para salud operativa y drilldown futuro.

Si durante la implementacion el panel de tendencia necesita datos que el
summary actual no puede representar correctamente, el ajuste permitido es una
extension backward-compatible del mismo read model/endpoint, derivada desde
`chat_sessions`/`provider_usage` existentes y sin tablas nuevas. No se debe
inventar un p95 global desde p95 por grupos ni mostrar series temporales
agregadas si solo existen sesiones recientes.

## Objetivos

- Exponer una vista de observability read-only en el frontend existente.
- Consumir `GET /projects/{project_id}/chat/observability/summary`.
- Reutilizar `GET /projects/{project_id}/chat/sessions` para la tabla de salud
  reciente cuando haga falta.
- Permitir filtros por proyecto, fecha y status con query params publicos.
- Mostrar metric cards con labels fieles al contrato.
- Mostrar breakdowns de status, errores y provider usage sin exponer contenido
  sensible.
- Cubrir loading, empty, error y refresh manual.
- Mantener la app como herramienta operativa, no landing ni dashboard BI.

## No objetivos

- No agregar graph rollout, Neo4j default ni cambios de retrieval.
- No agregar replay, re-run, edit, delete, retention ni auth final.
- No agregar OpenTelemetry, Langfuse ni exporters hosted.
- No agregar nuevas tablas ni materialized views en el primer slice.
- No consultar tablas internas desde frontend.
- No exponer prompts completos, respuestas completas, provider payloads, API
  keys ni secretos.
- No reemplazar el cliente API existente ni migrar el stack frontend.

## Contrato frontend recomendado

### Cliente API

Agregar tipos TypeScript alineados con M17:

- `ChatObservabilityFilters`
- `ChatObservabilityLatencySummary`
- `ChatObservabilityProviderUsageGroup`
- `ChatObservabilitySummary`
- `ChatObservabilitySummaryParams`

Agregar al `ApiClient`:

```ts
getChatObservabilitySummary(
  projectId: string,
  params?: ChatObservabilitySummaryParams,
): Promise<ChatObservabilitySummary>
```

La implementacion debe:

- construir
  `/projects/${projectId}/chat/observability/summary?created_at_from=...`;
- omitir parametros vacios;
- preservar errores HTTP estructurados via `ApiClientError`;
- tener tests con `fetch` fake para URL, metodo y parsing.

### Dashboard UI

La UI puede vivir primero en `frontend/src/App.tsx` si el cambio es pequeno,
pero el slice debe separar componentes cuando el archivo deje de ser facil de
leer. El primer route/navigation puede ser un toggle simple entre `Chat` y
`Observability`; no hace falta router externo.

La vista de observability debe incluir:

- filtros controlados: `project_id`, `created_at_from`, `created_at_to`,
  `status`;
- boton `Refresh`;
- tarjetas:
  - `Sessions`: `summary.sessions.total`;
  - `Provider calls`: `summary.provider_usage.total_records`;
  - `Estimated cost`: `summary.provider_usage.total_estimated_cost_usd`;
  - `Errors`: session + provider errors;
  - `Latency`: maxima latencia p95 disponible entre grupos, etiquetada como
    grupo mas lento, o un campo backend nuevo si un slice posterior agrega
    latencia global;
- breakdown de `sessions.by_status`;
- lista de `errors.top_messages` truncados por backend;
- tabla de `provider_usage.groups`;
- tabla de sesiones recientes desde `listChatSessions` con status, updated at,
  counts y costo estimado.

## Secuencia recomendada de M20

### 1. `m20-chat-observability-dashboard-plan`

Alcance:

- Crear el change OpenSpec M20.
- Documentar layout aprobado, alcance, no objetivos y slices.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo frontend/backend.

### 2. `m20-observability-frontend-client`

Alcance:

- Agregar tipos de observability en `frontend/src/lib/apiClient.ts`.
- Agregar `getChatObservabilitySummary`.
- Agregar tests de URL/query params, shape parseado y errores.

Fuera de alcance:

- UI de dashboard.
- Cambios backend.

### 3. `m20-observability-dashboard-shell`

Alcance:

- Agregar navegacion simple `Chat` / `Observability`.
- Construir filtros controlados y refresh.
- Renderizar tarjetas de resumen desde el endpoint M17.
- Probar loading, empty, error y preservacion de inputs.

Fuera de alcance:

- Cambios al contrato backend.
- Drilldown avanzado.

### 4. `m20-observability-breakdowns`

Alcance:

- Renderizar status breakdown.
- Renderizar errores agregados.
- Renderizar provider usage table.
- Renderizar session health table reutilizando `listChatSessions`.
- Etiquetar latencia/costo segun la derivacion real.

Fuera de alcance:

- Graficos complejos o dependencias charting nuevas si HTML/CSS simple alcanza.

### 5. `m20-observability-summary-shape` opcional

Abrir este slice solo si la implementacion del dashboard demuestra que el
contrato M17 no permite un panel aprobado sin derivaciones ambiguas.

Alcance permitido:

- Extender el mismo endpoint con campos derivados backward-compatible, por
  ejemplo buckets de sesiones/usage por dia u hora.
- Reutilizar tablas existentes y calculos portables.
- Agregar tests API/CLI si el shape publico cambia.

Fuera de alcance:

- Nuevas tablas, materialized views, exporters hosted o otro endpoint BI.

### 6. `m20-quality-gate`

Alcance:

- Validar frontend, Python si hubo contrato backend, OpenSpec y docs.
- Verificar el frontend con navegador local cuando haya UI.
- Archivar el change M20 y publicar specs canonicas.

## Riesgos y mitigaciones

- Riesgo: inflar el alcance hacia BI.
  Mitigacion: consumir M17/M14 y usar HTML/CSS simple antes de charting externo.
- Riesgo: metric cards ambiguas.
  Mitigacion: labels precisos y backend opcional solo para campos agregados
  realmente necesarios.
- Riesgo: filtrar contenido sensible.
  Mitigacion: usar solo agregados M17 y sesiones resumen M14, no mensajes
  completos ni raw provider payloads.
- Riesgo: archivo `App.tsx` crece demasiado.
  Mitigacion: extraer componentes focalizados en el slice de UI si la difusion
  de estado deja de ser manejable.
- Riesgo: duplicar logica de URL/query.
  Mitigacion: extender `appendSearchParam` y tests del cliente existente.

## Validacion esperada por slice

Planificacion:

```text
npx --yes @fission-ai/openspec validate m20-chat-observability-dashboard-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Implementacion frontend:

```text
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

Si un slice toca backend Python:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
```
