# Diseno — Chat attachments + vision model path

Spec vinculante para los implementers. Valores exactos; no improvisar
alternativas sin escalar. Espanol para prosa, codigo/identificadores en
ingles como el repo.

## 1. Constantes y tipos aceptados

Nuevo modulo `src/adaptive_rag/chat/attachments.py` define:

- `MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024` (10 MB por archivo).
- `MAX_ATTACHMENTS_PER_MESSAGE = 5`.
- `MAX_DOCUMENT_TEXT_CHARS = 8_000` (truncado por documento al subir; se
  persiste ya truncado, asi la inyeccion en prompt esta acotada).
- Imagenes: `image/png`, `image/jpeg`, `image/webp`, `image/gif`.
- Documentos: `text/plain`, `text/markdown`, `application/pdf`,
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- Fallback por extension cuando el mime llega vacio u
  `application/octet-stream` (Safari): `.png .jpg .jpeg .webp .gif` (image) y
  `.md .markdown .txt .pdf .docx` (document).

## 2. DB

Modelo `ChatAttachment` en `src/adaptive_rag/db/models/chat_attachment.py`
(seguir el estilo de `db/models/chat_session.py`): 

- `id` UUID PK; `project_id` UUID FK `projects.id` `ondelete="CASCADE"`;
  `user_id` UUID FK `users.id` `ondelete="SET NULL"` nullable;
  `session_id` UUID FK `chat_sessions.id` `ondelete="SET NULL"` nullable.
- `kind` String(16) CheckConstraint `in ("image","document")`;
  `mime` String(255); `filename` String(500); `size_bytes` Integer.
- `content` LargeBinary (bytes en DB; sirve SQLite tests + PG prod).
- `extracted_text` Text nullable (solo documentos, ya truncado a
  `MAX_DOCUMENT_TEXT_CHARS`).
- `status` String(16) CheckConstraint `in ("ready","failed")`, default
  `"ready"` (pipeline sincrono en v1; la columna cubre futuro async).
- `created_at` server_default `func.now()`.
- Indexes: `(project_id, user_id)` y `(session_id)`.

Migracion alembic nueva, `down_revision = "j9k0l1m2n3o4"` (head actual), id
mnemonico corto no usado (p.ej. `k1l2m3n4o5p6`), estilo de
`alembic/versions/c3d4e5f6a7b8_m37_auth_schema_repositories.py`.

Repositorio `ChatAttachmentRepository` en
`src/adaptive_rag/db/repositories/chat_attachments.py` (patron
`db/repositories/user_memories.py`): `create(...)`, `get(...)` scoped por
`(id, project_id)`, `get_owned(...)` scoped por `(id, project_id, user_id)`,
`list_owned_by_ids(project_id, user_id, ids)`, `delete(...)`. Exportar modelo
y repo en los `__init__.py` correspondientes.

## 3. API de attachments

Router nuevo `src/adaptive_rag/api/routes/chat_attachments.py`,
`APIRouter(prefix="/projects/{project_id}/chat/attachments", tags=["chat"])`,
registrado en `api/app.py` junto al router de chat. Deps como las rutas de
chat: `get_session` + `get_project_access` (cualquier miembro, igual que
chat) + `get_current_user`. Las rutas commitean explicitamente.

Requiere `python-multipart` en `pyproject.toml` dependencies + `uv lock`.

- `POST ""` (201): multipart `file: UploadFile` + `session_id: UUID | None`
  opcional (Form). Orden de validacion (todo 422 antes de escribir DB):
  1. filename ausente -> `missing_filename`.
  2. mime/extension no soportado -> `unsupported_attachment_type`.
  3. lectura con cap: `> MAX_CHAT_ATTACHMENT_BYTES` -> `attachment_too_large`;
     cuerpo vacio -> `empty_file`.
  4. `session_id` dado: debe existir y ser del proyecto (si no, 404
     `session_not_found`); no se auto-crean sesiones en upload.
  5. `kind`: image si el tipo resuelto es imagen, si no document.
  6. Documentos: extraer texto ahora. pdf -> `PdfEmbeddedTextParser`,
     docx -> `DocxTextParser` (via `parser_for_content_type` de
     `ingestion/parsers/registry.py`), txt/md -> decode utf-8
     (`errors="replace"`) + `normalize_text`. Truncar a
     `MAX_DOCUMENT_TEXT_CHARS`. Error de extraccion -> 422
     `text_extraction_failed`.
- Respuesta upload (schema en `api/schemas/chat.py` o nuevo
  `api/schemas/chat_attachments.py`): `{ id, kind, filename, mime,
  size_bytes }`.
- `DELETE "/{attachment_id}"` -> 204. Solo si el row es del proyecto y del
  usuario actual; si no, 404 `attachment_not_found` (no delatar existencia).
- `GET "/{attachment_id}/content"` -> bytes con `media_type=mime` del row;
  mismo scoping/404. (Thumbnails/descarga; el FE v1 no lo usa aun.)

Errores: seguir el mecanismo de error de la casa (mirar como chat.py mapea
errores a respuestas con codigo machine-readable en `detail`).

## 4. Chat request + service

- `ChatRequestBody` (`api/schemas/chat.py`, tiene `extra="forbid"`): anadir
  `attachment_ids: list[UUID] | None = None` con max 5 (validar en
  `to_service_request` o Field; 422 `invalid_attachment` si > 5 — ver
  convencion de validacion existente). `message` sigue requerido no-vacio.
- `ChatRequest` y `ChatRunnerRequest` (`chat/models.py`): anadir
  `attachments: tuple[ChatAttachmentContext, ...] = ()`.
- `ChatAttachmentContext` (frozen dataclass en `chat/attachments.py`):
  `id: UUID, kind: str, filename: str, mime: str, image_data_url: str | None,
  extracted_text: str | None`.
- Loader `load_chat_attachments(...)` en `chat/attachments.py`: dado
  `(session, project_id, user_id, attachment_ids)` devuelve contextos en el
  orden pedido; cualquier id inexistente o no perteneciente a
  (project,user) -> raise `ChatAttachmentError(code="invalid_attachment")`.
  Imagenes -> `image_data_url = "data:{mime};base64,{b64(content)}"`;
  documentos -> `extracted_text` persistido.
- `ChatAttachmentError(ValueError)` con `.code` y mensaje operator-safe;
  chat.py lo mapea a 422 con ese codigo.
- `ChatService`: inyectar loader como dependencia opcional
  (`attachment_loader: Callable[..., tuple[ChatAttachmentContext, ...]] |
  None` en el constructor; factories lo cablean con repo + `session_scope`;
  tests inyectan fakes). En `respond` y en el path de stream, tras
  `_validate_request`: cargar contextos si hay `attachment_ids`; persistir
  refs en el `record_message` de usuario:
  `metadata_json={"attachments": [{"id","filename","kind","mime"}]}`.
  Verificar que `GET /sessions/{id}` ya devuelve `metadata_json` de mensajes
  de usuario (lo usa el FE); si falta, cablearlo de forma quirurgica.
- Gate de vision y routing (service, antes de `runner.run`). Politica
  vinculante (add-on producto, sustituye al "fallback primero"):
  1. Sin imagenes (texto o solo documentos) -> siempre el runner de chat;
     el slot vision nunca se resuelve ni se exige.
  2. Con imagenes: si `getattr(chat_runner, "model_capabilities", None)`
     contiene "vision" -> se usa el chat runner (mismo modelo del turno).
  3. Si no, y el runtime slot `vision` esta configurado (override de proyecto
     o default global; ver §5b) -> se usa el `vision_runner` inyectado
     (conexion+modelo del slot).
  4. Si no hay slot vision, pero el chat runner tiene
     `fallback_model_capabilities` con "vision" -> se usa el chat runner,
     que auto-rutea internamente a su fallback model (red de seguridad).
  5. Si nada funciona -> `ChatAttachmentError(code="vision_model_required")`
     (mensaje operator-safe: el modelo de chat no acepta imagenes y no hay
     slot vision configurado).
  Si `model_capabilities` es None (runner custom ajeno, p.ej. evals) -> no
  gatear: comportamiento previo intacto.

## 5. Runner multimodal + capabilities

- `infer_qwen_model_capabilities` (`runtime/qwen_defaults.py`): si el
  model_id (lower) matchea familia vision — regex r"(?:^|[-_.])vl(?:[-_.]|$)"
  o contiene "vision" — devolver `("chat", "vision")`. Casos: `qwen-vl-max`,
  `qwen2.5-vl-72b`, `qwen3-vl-plus`. No marcar chat models normales.
- `QwenChatRunner` (`chat/qwen.py`): campos nuevos `model_capabilities` y
  `fallback_model_capabilities` (tuplas, via inference sobre
  `model_name`/`fallback_model_name`; si no hay fallback, tupla vacia).
  Auto-routing interno a fallback SOLO como ultimo recurso (paso 4 de la
  politica de §4): cuando el service le pasa imagenes porque no hay slot
  vision, si "vision" esta en las caps del fallback -> usar el fallback
  model para todas las llamadas de este request (contrato JSON intacto).
- `_initial_messages`: cuando hay contextos de imagen, el turno user pasa de
  string a parts: `[{"type":"text","text": user_text},
  {"type":"image_url","image_url":{"url": data_url}}, ...]` (texto primero).
  El texto extraido de documentos se anexa al `user_text` con cabecera
  separadora (una sola vez, antes del primer documento):
  `\n\n=== USER-ATTACHED FILES (not retrieved from the knowledge base) ===`
  y por documento `[Attached: {filename}]\n{extracted_text}` unido con
  `\n\n`. Sin imagenes -> comportamiento actual intacto (strings planos).
  Mantener `enable_thinking: False`, `response_format` json y el contrato
  `{"answer","cited_chunk_ids"}`.
- `RetrievalGroundedChatRunner` (`chat/runners.py`): declarar
  `model_capabilities = ("chat", "vision")`; aceptar `request.attachments`
  sin red y, si hay imagenes, incluir en la respuesta una linea
  `Attached images: N` (test hook). Streaming igual que text-only.
- Historial: text-only en v1 (no re-render de adjuntos de turnos previos).

## 5b. Runtime slot `vision` (end-to-end)

Add-on de producto: el slot `vision` no existe hoy; se anade completo.

- `RUNTIME_SLOT_VALUES` (`db/models/runtime_settings.py`) gana `"vision"` y
  los dos CheckConstraints (`runtime_slot_defaults_slot_check`,
  `project_runtime_slot_overrides_slot_check`) lo incluyen. Migracion
  alembic NUEVA (encadenada tras la de chat_attachments) que altera ambos
  constraints: en SQLite hace falta `batch_alter_table` (recreate); seguir el
  patron de migraciones previas que alteren constraints si existe.
- `PROVIDER_CONNECTION_CAPABILITY_VALUES`
  (`db/models/provider_connection.py`) gana `"vision"` SOLO si el repo la usa
  para validar slot<->capability al hacer upsert de slots (verificar en
  `db/repositories/runtime_settings.py`; la validacion de slot es contra
  `RUNTIME_SLOT_VALUES`, que ya cubre `vision` al actualizar la constante).
- Resolucion: reutilizar el patron generico de `runtime/resolution.py`
  (`_resolve_persisted_slot`) para `vision` (override de proyecto -> default
  global). Sin modelo VL por defecto hard-codeado: slot vacio hasta que el
  operador lo configure.
- Factories + DI: builder de runner para el slot vision (mismo patron que
  `_build_resolved_chat_runner`; devuelve `None` si el slot no esta
  configurado o esta incompleto) y dependencia API opcional
  (p.ej. `get_vision_chat_runner`) que `ChatService` recibe como
  `vision_runner: ChatRunner | None`.
- API runtime-settings: el upsert/list de slots acepta `vision` en cuanto la
  constante crece (verificar que ningun schema pydantic fija el enum de
  slots; si lo fija, anadir `vision`).
- FE runtime settings: `frontend/src/features/runtime/runtimeUi.ts` enumera
  slots — anadir `vision` con su label ("Vision") y cubrir en
  `runtimeUi.test.ts`. Misma UX que dense_embedding/rerank; opcional hasta
  que haya imagenes.
- Catalogo: las capabilities de modelos VL llegan via
  `infer_qwen_model_capabilities` (§5); metadata_json del catalogo queda
  como escape futuro (fuera de v1).

## 6. Frontend

- `apiClient.ts`: helper `requestForm` (FormData directo, sin content-type;
  `withAuthToken` ya inyecta Bearer). Metodos:
  `uploadChatAttachment(projectId, file, sessionId?) ->
  ChatAttachmentUploadResponse` (`{ id, kind, filename, mime, size_bytes }`)
  y `deleteChatAttachment(projectId, attachmentId) -> void`.
  `ChatRequestBody` gana `attachment_ids?: string[]`.
- Nuevo `frontend/src/features/chat/ChatAttachments.tsx`:
  - `type LocalAttachment = { localId: string; file: File; previewUrl:
    string; status: "uploading" | "ready" | "failed"; attachmentId?: string;
    kind?: "image" | "document"; error?: string }`.
  - `AttachmentChips` (presentacional): fila flex-wrap; imagen -> thumbnail
    24px `object-cover` desde `previewUrl`; documento -> icono `FileText`;
    nombre truncado; boton X (`aria-label="Remove attachment {filename}"`);
    estados: uploading `opacity-60`, failed borde `border-destructive` y
    `title` con el error. Sin boton retry (quitar y re-anadir).
  - Hook `useChatAttachments({ upload, deleteRemote, maxAttachments = 5 })`
    con la maquina uploading->ready|failed, admission cap dentro del updater
    funcional de setState, revocacion de object URLs al quitar/resetear/
    desmontar, y `reset()` + derivados `readyAttachments` y `blocked`
    (true si alguno uploading|failed).
- Composer (`ChatWorkspaceView.tsx`): boton paperclip icon-only
  (`Paperclip` de lucide, `COMPOSER_TOOL_BUTTON_CLASS`, `aria-label="Attach
  files"`) en el grupo de acciones junto a CircleDot/Map/mic; hidden
  `<input type="file" multiple>` con `accept` de la lista de §1; disabled
  cuando `attachments.length >= 5`; `onPaste` en el Textarea: si
  `clipboardData.files` no vacio -> preventDefault + add. Chips sobre el
  input-shell. Send disabled si `question` vacio (v1) o `blocked`.
- `App.tsx`: estado `chatAttachments` via el hook con los metodos del client;
  `submitChatQuestion` incluye `attachment_ids` (ids ready en orden) solo si
  hay; tras exito (`setQuestion('')`) tambien `reset()` de adjuntos; pasar
  props al panel.
- Transcript: `ChatTranscriptTurn` gana `attachments?: { id, filename, kind,
  mime }[]`; `transcriptTurnsFromSessionDetail` parsea `metadata.attachments`
  del mensaje de usuario (patron `parseChatStepsFromMetadata`);
  `QuestionPrompt` renderiza chips read-only (icono kind + filename; sin
  fetch de blobs en v1).
- Tests vitest: `ChatAttachments.test.tsx` (add file con upload mockeado,
  remove, max 5 cap, gating de send mientras uploading/failed) + tests de
  apiClient para upload (FormData, Bearer, URL) y `attachment_ids` en el body
  si aplica.

## 7. Tests backend requeridos

- Repo unit: create/get/scoping/delete, `list_owned_by_ids` filtra ajenos.
- API integration (`tests/integration/api/test_chat_attachments.py`,
  self-contained estilo `test_chat.py`, recordar anadir la tabla nueva al
  `create_all(tables=[...])`): upload ok por tipo; 422 type/size/empty;
  ownership (otro usuario no borra ni lee -> 404); GET content roundtrip;
  `session_id` ajeno -> 404.
- Chat path: unit qwen (`RecordingChatClient`) — payload con parts
  text+image_url, modelo fallback cuando activo no-vision, docs inyectan
  texto con cabecera; unit capabilities (vl/vision vs chat normal); unit fake
  runner echo `Attached images: N`; integration chat API — chat con
  attachment_id de imagen llega al runner fake; ids ajenos -> 422
  `invalid_attachment`; imagen con runner no-vision -> 422
  `vision_model_required`.
- Vision slot (§5b): unit de capabilities VL; unit/integration de routing —
  chat vision-capable -> se usa chat; chat no-vision + slot vision
  configurado -> se usa el vision runner; ninguno -> 422
  `vision_model_required`; docs-only -> nunca toca el slot. Slot API:
  upsert acepta `vision` y sigue rechazando nombres invalidos; migracion
  validada offline (`alembic history` + `upgrade --sql`) o contra SQLite tmp.

## 8. Verificacion (cada tarea backend; al final FE)

- `uv run pytest <paths nuevos> -q` y suite completa antes de cerrar.
- `uv run ruff check .`
- `uv run mypy src`
- `cd frontend && pnpm exec vitest run` y `pnpm typecheck`.
- Sin commits ni PR (lo decide el usuario).
