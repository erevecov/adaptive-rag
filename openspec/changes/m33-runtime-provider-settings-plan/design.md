# Design M33 runtime provider settings plan

## Context

El provider runtime actual selecciona fakes o Qwen live desde settings
globales. Las factories en `adaptive_rag.provider_runtime` resuelven
`embedding_provider`, `sparse_embedding_provider`, `chat_provider` y
`rerank_provider` desde `.env`; si falta `ADAPTIVE_RAG_QWEN_API_KEY` o
`ADAPTIVE_RAG_QWEN_BASE_URL`, el runtime falla antes de llamar red.

Ese contrato sigue siendo correcto como fallback local, pero no como producto
operable. La UI necesita guardar estado, mostrar si una conexion esta lista,
rotar secrets, mezclar hosted/local por slot y permitir que un proyecto
especial overridee defaults sin convertir providers en configuracion por
proyecto.

La referencia de BeFlow aporta tres patrones utiles:

1. Slots fijos por enum, no strings libres.
2. Un servicio de resolucion por slot con cache corta y fallback de env.
3. El pool de chat separado del slot default, con exactamente un default.

Adaptive RAG debe tomar esos patrones, no copiar el modelo completo: aqui los
proyectos existen y sus overrides son parte del contrato.

## Domain Model

### Provider connections

`provider_connections` representa conexiones globales del workspace local. Una
connection declara:

- `connection_id` estable.
- `provider`: por ejemplo `fake`, `qwen`, `local_openai_compatible`.
- `connection_type`: `fake`, `hosted` o `local`.
- `base_url` opcional.
- capacidades declaradas: `chat`, `dense_embedding`, `sparse_embedding`,
  `rerank`, `contextualization`.
- metadata no secreta para status y UI.

Hosted y local pueden coexistir. Ejemplo valido: Qwen hosted para sparse
embeddings, un endpoint local OpenAI-compatible para chat, fake para
contextualization.

### Provider secrets

Secrets son globales, no project-scoped. Se guardan cifrados server-side y se
referencian desde una connection. El API solo devuelve status seguro:
`configured`, `updated_at`, `last_four` o fingerprint no reversible cuando
aplique.

El backend requiere una key de cifrado server-side, por ejemplo
`ADAPTIVE_RAG_PROVIDER_SECRETS_KEY`. Si falta o es invalida, endpoints que
persisten o descifran secrets fallan con error estable. Endpoints de lectura de
status siguen funcionando cuando no necesitan descifrar.

### Runtime slots

El conjunto inicial de slots es fijo:

- `chat`
- `dense_embedding`
- `sparse_embedding`
- `rerank`
- `contextualization`

Cada slot normal apunta a una connection + model + parametros acotados. Unknown
slots se rechazan antes de persistir. Cambiar la lista de slots requiere nuevo
OpenSpec.

### Chat model pool

`chat` tiene dos niveles:

- un default global efectivo para llamadas sin override;
- un pool global de modelos habilitados, con exactamente un modelo marcado como
  default.

El pool permite que la UI futura ofrezca varios modelos para chat sin volver
dinamico el sistema completo. Las invariantes son:

- no puede haber cero modelos si el pool esta configurado;
- no puede haber mas de un default;
- no se puede borrar el ultimo modelo del pool;
- no se puede borrar el default sin rotarlo primero.

### Project overrides

Los proyectos heredan defaults globales. Un proyecto puede overridear:

- cualquier slot individual;
- el pool/default de chat para ese proyecto.

Los overrides guardan configuracion funcional del proyecto, no secrets. Si el
proyecto apunta a una hosted connection, sigue usando el secret global de esa
connection.

## Resolution

Cada operacion usa un resolver efectivo:

```text
project override for slot/model
  -> global slot default or global chat pool default
  -> legacy .env settings
  -> fake fallback when allowed by provider_runtime_mode
```

El resolver devuelve un `ResolvedRuntimeSlot` con slot, provider, connection,
model, base URL, parametros seguros y un secret handle interno. Los servicios
de chat/retrieval/ingestion nunca leen directamente `.env` ni tablas de
secrets; piden el provider ya resuelto a factories.

Esto permite mezclar providers en la misma corrida. Ejemplo:

- `chat`: local OpenAI-compatible, model `qwen2.5:14b`.
- `dense_embedding`: Qwen hosted.
- `sparse_embedding`: Qwen hosted.
- `rerank`: Qwen hosted.
- `contextualization`: fake/local.

## API Shape

El detalle final puede ajustarse durante implementacion, pero el contrato debe
separar global runtime settings de project overrides.

Global:

- `GET /runtime-settings/connections`
- `PUT /runtime-settings/connections/{connection_id}`
- `DELETE /runtime-settings/connections/{connection_id}`
- `PUT /runtime-settings/connections/{connection_id}/secrets/{secret_name}`
- `DELETE /runtime-settings/connections/{connection_id}/secrets/{secret_name}`
- `GET /runtime-settings/slots`
- `PUT /runtime-settings/slots/{slot}`
- `GET /runtime-settings/chat/models`
- `POST /runtime-settings/chat/models`
- `DELETE /runtime-settings/chat/models/{connection_id}/{model_id}`
- `PUT /runtime-settings/chat/models/{connection_id}/{model_id}/default`

Project-scoped:

- `GET /projects/{project_id}/runtime-settings`
- `PUT /projects/{project_id}/runtime-settings/slots/{slot}`
- `DELETE /projects/{project_id}/runtime-settings/slots/{slot}`
- `GET /projects/{project_id}/runtime-settings/chat/models`
- `PUT /projects/{project_id}/runtime-settings/chat/models`
- `DELETE /projects/{project_id}/runtime-settings/chat/models/{connection_id}/{model_id}`
- `PUT /projects/{project_id}/runtime-settings/chat/models/{connection_id}/{model_id}/default`

Responses never include plaintext secrets or encrypted blobs.

## Frontend

Add a global `Runtime settings` surface:

- list connections and provider readiness;
- create/update local or hosted connections;
- set/rotate/delete secrets without reading them back;
- configure global defaults per fixed slot;
- manage global chat model pool and default.

Project surfaces show inherited/effective runtime settings and allow explicit
overrides. The UI must make inherited vs overridden state visible and provide a
clear reset-to-global action.

## Error Handling

Stable error codes should include:

- `unsupported_slot`
- `unsupported_provider`
- `unsupported_connection_type`
- `connection_not_found`
- `connection_unavailable`
- `missing_provider_secret`
- `provider_secret_key_missing`
- `provider_secret_decrypt_failed`
- `incompatible_model`
- `cannot_delete_default_chat_model`
- `cannot_delete_last_chat_model`
- `project_not_found`

Errors, logs, audit metadata and provider usage records must not include API
keys, Authorization headers, encrypted blobs or raw provider payloads.

## Sequencing

1. `m33-runtime-provider-settings-plan`: planning and OpenSpec only.
2. `m33-provider-connections-secrets`: schema, repositories, encryption helper,
   status APIs and docs.
3. `m33-global-slot-defaults`: slot enum, global defaults, chat pool and
   admin/global APIs.
4. `m33-project-runtime-overrides`: project-scoped override storage and APIs.
5. `m33-runtime-resolution-wiring`: factories resolve effective slots for
   chat, dense embedding, sparse embedding, rerank and contextualization.
6. `m33-runtime-settings-ui`: frontend global Runtime settings and project
   override controls.
7. `m33-quality-gate`: docs, smokes, tests and OpenSpec archive.

## Risks

- **Scope creep.** Runtime settings could grow into provider management,
  model downloads or dynamic workflows. Mitigation: fixed slots, no local
  process lifecycle, no dynamic slot registry in M33.
- **Secret exposure.** Persisted API keys create a stronger safety bar than
  `.env`. Mitigation: encrypted storage, no readback, stable redaction tests.
- **Resolution ambiguity.** Global defaults and project overrides can conflict.
  Mitigation: one resolver contract and explicit precedence.
- **Migration conflicts.** This work needs schema changes. Mitigation: one
  schema slice at a time; do not run parallel PRs touching Alembic/models.
- **Offline regressions.** Tests and first-run must remain fake/local by
  default. Mitigation: `.env`/fake fallback and no live calls in mandatory
  tests.
