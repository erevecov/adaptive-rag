# Diseno M14 de lectura/historial de chat

## Contexto

M13 agrego el audit trail durable necesario para reproducir una corrida de chat:
sesion, mensajes, tool calls, retrieval runs, retrieved chunks, citations y
usage/cost. Ese dato ya es la fuente de verdad para debugging y trazabilidad,
pero hoy solo queda accesible mediante queries internas o tests.

El siguiente paso no debe ser frontend ni dashboard todavia. Primero hace falta
un contrato backend pequeno para consultar lo persistido con aislamiento por
proyecto. Ese contrato reduce riesgo para UI, streaming y dashboards porque fija
que datos existen, como se ordenan, como se paginan y que queda fuera por
seguridad.

## Decision

La decision recomendada es `proceed` con una superficie read-only minima de
historial de chat.

M14 debe exponer listado y detalle de sesiones desde API y CLI, reutilizando el
audit trail M13. Debe mantener el alcance en lectura: no re-run, no delete, no
edicion, no streaming SSE, no dashboard y no cambios a `ChatService` salvo que
se necesiten read models compartidos.

## Objetivos

- Listar sesiones de chat por `project_id`, ordenadas de mas nuevas a mas
  antiguas.
- Filtrar el listado por status estable cuando se indique.
- Usar `limit` acotado y cursor o paginacion deterministica para no exponer
  listados no acotados.
- Consultar el detalle completo de una sesion por `session_id`, incluyendo
  mensajes, tool calls, retrieval runs, retrieved chunks/citations y provider
  usage.
- Exponer comandos CLI equivalentes para inspeccion local y QA.
- Mantener respuestas sin secretos y aisladas por proyecto.

## No objetivos

- No implementar frontend.
- No implementar streaming SSE, WebSockets ni respuestas parciales.
- No implementar dashboard de costo/latencia.
- No implementar replay/re-run de sesiones.
- No editar, borrar, archivar ni retener sesiones.
- No cambiar ranking, retrieval, rerank, providers ni defaults.
- No agregar autenticacion/autorizacion final; M14 mantiene el aislamiento por
  `project_id` ya usado por el backend.

## Contrato API recomendado

### `GET /projects/{project_id}/chat/sessions`

Devuelve resumenes de sesiones:

- `session_id`
- `status`
- `created_at`
- `updated_at`
- `model_config`
- `prompt_version`
- `message_count`
- `tool_call_count`
- `retrieval_run_count`
- `provider_usage_count`
- `total_estimated_cost_usd`
- `error_message` cuando exista

Parametros:

- `status`: opcional, uno de `running`, `succeeded`, `failed`.
- `limit`: default pequeno, maximo acotado.
- `cursor`: opcional, opaco o estable por `created_at`/`session_id`.

### `GET /projects/{project_id}/chat/sessions/{session_id}`

Devuelve detalle de una sesion:

- metadata de sesion;
- mensajes ordenados por `created_at`;
- tool calls ordenadas por `created_at`;
- retrieval runs ordenados por `created_at`;
- retrieved chunks ordenados por `rank` dentro de cada retrieval run;
- provider usage ordenado por `created_at`;
- citations exactamente como fueron persistidas en `citation_json`.

Si la sesion no pertenece al proyecto, la API debe responder como no encontrada
o error estable equivalente, sin filtrar existencia cross-project.

## Contrato CLI recomendado

- `adaptive-rag chat sessions list --project-id <uuid> [--status ...] [--limit ...]`
- `adaptive-rag chat sessions show --project-id <uuid> --session-id <uuid>`

La salida debe ser JSON estable para poder usarse en QA, scripts y futuras
herramientas. No se requiere formato table en M14.

## Boundaries de implementacion

- `ChatAuditRepository` puede crecer con read models explicitos o queries
  dedicadas para listado/detalle.
- API y CLI deben consumir el mismo contrato de serializacion cuando sea
  razonable.
- Los endpoints son read-only y no abren transacciones de escritura.
- La paginacion debe ser deterministica: ordenar por `created_at desc` y usar
  `id` como desempate.
- Los datos ya saneados por M13 se pueden devolver; M14 no debe introducir
  nuevos campos con secretos.

## Secuencia recomendada de M14

### 1. `m14-chat-history-read-surface`

Alcance:

- Crear el change OpenSpec M14.
- Documentar objetivos, no objetivos, contrato API/CLI y secuencia.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo de endpoints/comandos.

### 2. `m14-chat-history-repository-read-models`

Alcance:

- Agregar read models o DTOs internos para resumen y detalle de sesion.
- Agregar queries de listado con `project_id`, `status`, `limit` y paginacion.
- Agregar query de detalle con mensajes, tool calls, retrieval runs, retrieved
  chunks y provider usage.
- Probar aislamiento cross-project y orden deterministico.

Fuera de alcance:

- API/CLI.

### 3. `m14-chat-history-api`

Alcance:

- Agregar schemas HTTP para list/detail.
- Agregar `GET /projects/{project_id}/chat/sessions`.
- Agregar `GET /projects/{project_id}/chat/sessions/{session_id}`.
- Mapear sesion inexistente o cross-project a error estable.

Fuera de alcance:

- Streaming o dashboard.

### 4. `m14-chat-history-cli`

Alcance:

- Agregar `adaptive-rag chat sessions list`.
- Agregar `adaptive-rag chat sessions show`.
- Reutilizar serializacion/API interna cuando sea practico.
- Mantener salida JSON estable.

Fuera de alcance:

- UI interactiva o tablas Rich.

### 5. `m14-quality-gate`

Alcance:

- Validar tests, lint, types y OpenSpec.
- Ejecutar smokes CLI relevantes.
- Archivar el change M14 cuando la implementacion quede completa.

## Riesgos y mitigaciones

- Riesgo: M14 crece hasta dashboard.
  Mitigacion: solo list/detail JSON, sin agregaciones visuales ni reportes.
- Riesgo: listados no acotados degraden performance.
  Mitigacion: `limit` obligatorio/default acotado y paginacion deterministica.
- Riesgo: fuga cross-project.
  Mitigacion: todas las queries reciben `project_id`; tests cubren otro
  proyecto con mismo tipo de datos.
- Riesgo: exponer secretos guardados por error.
  Mitigacion: devolver solo campos ya saneados por M13 y no agregar raw provider
  payloads.
- Riesgo: frontend se apoye en un contrato inestable.
  Mitigacion: M14 fija shape JSON antes de construir UI.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m14-chat-history-read-surface --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Smokes live con Qwen no son necesarios para M14 porque la superficie lee datos
persistidos y debe poder validarse con fakes deterministas.
