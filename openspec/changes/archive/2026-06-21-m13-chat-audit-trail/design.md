# Diseno M13 de audit trail de chat

## Contexto

M4 y M5 estabilizaron retrieval y chat/tool calling con API/CLI delgados. M7,
M8 y M9 agregaron providers live, usage/cost runtime, hosted evals y rerank
opt-in. M10-M12 cerraron una etapa de decision de retrieval: dense sigue como
default y no hay evidencia suficiente para promover candidate tuning,
lexical/RRF ni sparse retrieval.

La brecha ahora es operativa. Una respuesta de chat puede ser correcta y
citable en memoria, pero el sistema todavia no deja un registro durable que una
la sesion, los mensajes, las tools, los retrieval runs, las citations y el
usage/costo. Sin ese audit trail, streaming, dashboards, historial, debugging de
providers y evals persistidos quedan sobre una base debil.

## Decision

La decision recomendada es `proceed` con un audit trail durable minimo para
chat.

M13 debe persistir la corrida conversacional completa sin convertirla en una
feature de historial, dashboard o streaming. La API/CLI pueden exponer un
`session_id` minimo si eso es necesario para trazabilidad, pero no deben agregar
endpoints de listado ni cambiar el contrato principal de respuesta.

## Objetivos

- Persistir sesiones, mensajes, tool calls, retrieval runs, retrieved chunks y
  citations de una corrida de chat.
- Vincular usage/cost de providers a sesion, job o eval cuando exista contexto.
- Registrar estados y errores auditables sin secretos.
- Mantener `ChatService`, API y CLI como consumidores de un contrato estable de
  audit trail.
- Usar fakes deterministas para probar persistencia sin red ni credenciales.

## No objetivos

- No implementar streaming SSE ni WebSockets.
- No agregar endpoints/comandos para listar historial de sesiones.
- No crear dashboards, reportes persistidos ni OpenTelemetry exporter.
- No agregar LLM-as-judge ni Ragas persistido.
- No cambiar ranking, rerank, providers, defaults de retrieval ni eval datasets.
- No guardar API keys, prompts completos sensibles ni texto completo de chunks
  fuera de las tablas de dominio existentes.

## Modelo durable minimo

M13 debe agregar tablas orientadas a audit trail:

- `chat_sessions`: una corrida conversacional por proyecto, con status,
  timestamps, prompt/model config y error resumido.
- `chat_messages`: mensajes asociados a una sesion, con role, content y metadata
  acotada.
- `tool_calls`: llamadas de tool por sesion, con nombre, argumentos
  serializables, resumen de resultado, status, latencia y error.
- `retrieval_runs`: ejecuciones de retrieval asociadas a sesion o tool call, con
  query, strategy, top_k, rerank flag, latencia y filtros aplicados.
- `retrieved_chunks`: resultados de retrieval por run, con `chunk_id`, rank,
  scores disponibles y `citation_json`.
- `provider_usage`: eventos de usage/cost vinculables a `project_id`,
  `session_id`, `job_id` o `eval_run_id`.

Los nombres finales pueden ajustarse para encajar con las convenciones de
modelos existentes, pero el contrato debe preservar esos conceptos y relaciones.

## Flujo

1. Una request valida de chat crea una `chat_session` en estado `running`.
2. El mensaje del usuario se guarda como `chat_message`.
3. Cada tool call se registra con argumentos saneados antes de ejecutar la tool.
4. Cada llamada a retrieval crea un `retrieval_run` y persiste sus
   `retrieved_chunks` con citations.
5. La respuesta final del assistant se guarda como `chat_message` y la sesion
   pasa a `succeeded`.
6. Si ocurre un error estable de validacion, runner, retrieval o provider, la
   sesion o el evento relevante guarda `failed` y `error_message` sin secretos.
7. Cuando el runtime capture usage/cost, el evento se vincula al contexto
   durable disponible.

## Boundaries de implementacion

La persistencia debe vivir debajo de la superficie conversacional actual:

- `ChatService` sigue validando citations contra resultados recuperados.
- `RetrievalService` no persiste audit trail por si solo salvo que reciba un
  writer/contexto explicito desde chat.
- API y CLI siguen siendo adaptadores delgados.
- Repositories encapsulan SQLAlchemy y aislamiento por `project_id`.
- Tests usan SQLite cuando sea suficiente y Postgres/pgvector solo donde ya sea
  necesario por contratos existentes.

## Secuencia recomendada de M13

### 1. `m13-chat-audit-trail`

Alcance:

- Crear el change OpenSpec M13.
- Documentar objetivos, no objetivos, riesgos y secuencia.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Migraciones, modelos y cambios runtime.

### 2. `m13-audit-schema`

Alcance:

- Agregar migracion Alembic y modelos SQLAlchemy para las tablas de audit trail.
- Definir claves foraneas, indices por `project_id`/`session_id` y status
  estables.
- Mantener compatibilidad con el schema multi-project existente.

Fuera de alcance:

- Integrar `ChatService`.

### 3. `m13-audit-repositories`

Alcance:

- Agregar repositories para crear sesiones, mensajes, tool calls, retrieval
  runs, retrieved chunks y provider usage.
- Probar aislamiento por proyecto y transiciones de status.
- Saneamiento de metadata sin secretos.

Fuera de alcance:

- Exponer historial por API/CLI.

### 4. `m13-chat-service-audit-wiring`

Alcance:

- Integrar audit trail en `ChatService` con fakes deterministas.
- Persistir request, tool calls, retrieval context, respuesta final y errores.
- Preservar validacion de citations y shape publico de respuesta.

Fuera de alcance:

- Streaming SSE.

### 5. `m13-api-cli-audit-surface`

Alcance:

- Hacer que API/CLI usen el audit writer por defecto.
- Exponer `session_id` o metadata minima si el contrato lo requiere.
- Agregar tests de integracion API/CLI que verifiquen audit trail consistente.

Fuera de alcance:

- Listado/lectura de sesiones historicas.

### 6. `m13-provider-usage-linking`

Alcance:

- Vincular usage/cost live u offline al contexto durable disponible.
- Mantener budget guard y metadata sin secretos.
- Probar que provider usage puede asociarse a chat, jobs o evals sin romper los
  runners offline.

Fuera de alcance:

- Dashboard de costo.

### 7. `m13-quality-gate`

Alcance:

- Validar tests, lint, types, specs, API/CLI smokes relevantes y archivar el
  change cuando M13 quede cerrado.

## Riesgos y mitigaciones

- Riesgo: M13 se convierta en historial de producto.
  Mitigacion: no agregar endpoints de listado ni UI; solo metadata minima de
  trazabilidad.
- Riesgo: acoplar retrieval productivo a persistencia.
  Mitigacion: audit writer/contexto explicito desde chat; retrieval standalone
  sigue funcionando sin audit trail.
- Riesgo: guardar datos sensibles.
  Mitigacion: serializar argumentos/resultados resumidos, no secretos ni API
  keys, y mantener texto fuente en tablas de dominio existentes.
- Riesgo: errores parciales de chat dejen auditoria inconsistente.
  Mitigacion: status por sesion/evento y tests de fallos antes/despues de tool
  calls.
- Riesgo: transacciones demasiado grandes.
  Mitigacion: empezar con una transaccion simple por request y separar solo si
  los tests o smokes muestran necesidad real.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m13-chat-audit-trail --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Smokes live con Qwen quedan opt-in y solo se ejecutan si el slice toca providers
live y hay `.env` local con credenciales y budget explicito.
