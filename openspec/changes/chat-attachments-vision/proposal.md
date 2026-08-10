# Propuesta — Chat attachments + vision model path

## Why

Los usuarios necesitan adjuntar archivos (sobre todo imagenes) en el composer
del chat. Las imagenes requieren un path de modelo con vision (content parts
multimodales hacia el provider OpenAI-compatible/Qwen); los documentos
(md/txt/pdf/docx) se extraen a texto y se inyectan como contexto acotado.

Referencia de patrones (solo lectura): beflow-graph-rag
(`AttachmentComposer.tsx`, `api/chat_attachments.py`). Diferencia clave: beflow
pre-describe imagenes a texto en upload; aqui el brief exige multimodal real
(parts `image_url` con data URL base64) en el turno de chat.

## What Changes

- Tabla `chat_attachments` (migracion alembic) + modelo + repositorio, con
  bytes en DB (`content` LargeBinary), scope project+user, `session_id` nullable.
- API: `POST/DELETE/GET content` bajo `/projects/{project_id}/chat/attachments`
  (multipart, Bearer, membresia de proyecto). Cap 10 MB por archivo, max 5
  adjuntos por mensaje.
- `ChatRequestBody.attachment_ids` (max 5). El chat service valida ownership
  (user+project), inyecta texto extraido de documentos y pasa imagenes como
  content parts al runner. Refs de adjuntos en `metadata_json` del mensaje de
  usuario para re-render en transcript.
- `QwenChatRunner` multimodal (parts text + image_url) con auto-routing a
  fallback model si el activo no tiene vision y el fallback si; 422
  `vision_model_required` si ninguno es capaz. `infer_qwen_model_capabilities`
  aprende a detectar vision (familias `*-vl-*` / `vision`).
- Runner fake (`RetrievalGroundedChatRunner`) acepta adjuntos sin red y
  menciona cuantas imagenes vio (para tests).
- Frontend: paperclip icon-only en el composer, chips (thumbnail/doc icon +
  nombre + X), max 5, paste desde clipboard, gate de Send mientras sube/falla,
  limpieza tras envio, `attachment_ids` en el body, refs en burbuja de usuario
  al recargar historial.
- Dependencia nueva: `python-multipart` (uploads multipart en FastAPI).

## Fuera de alcance (v1)

- OCR como job de ingestion separado; indexing KB de adjuntos; video/audio.
- Upload anonimo/publico; rate limit dedicado de uploads.
- Endpoint member-readable de capabilities (los routers de runtime-settings son
  admin-only): el FE no puede pre-avisar de falta de vision; depende del 422.
- Re-inyeccion de adjuntos de turnos previos (historial sigue text-only).
- Envio attachment-only (mensaje vacio): `message` sigue siendo requerido.
- HEIC (opcional; queda como riesgo residual).

## Impacto

Chat gana adjuntos persistidos con path de vision real y degradacion clara
(422 con codigo) cuando el modelo activo no soporta imagenes. Specs candidatas
a delta al cerrar: `chat-streaming`, `chat-audit-trail`, `provider-runtime`.
