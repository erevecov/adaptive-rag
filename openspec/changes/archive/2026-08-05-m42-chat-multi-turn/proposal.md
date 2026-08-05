# Propuesta M42 — chat multi-turn + query condenser

## Why

Cada `POST /chat` y `/chat/stream` abre una sesion nueva y el runner solo ve el
mensaje actual. Follow-ups conversacionales no reutilizan historial ni
condensan la query; la UI limpia la sesion al preguntar.

## What Changes

- `session_id` opcional en body de chat (stream y non-stream).
- Continuar sesion existente (mismo project/user); historial acotado al runner.
- Condensador de query conversacional con fake deterministico para tests.
- UI envia `session_id` de la sesion seleccionada y no la descarta en follow-up.
- Specs/tests multi-turn stream + non-stream + history consistent.

## Fuera de alcance

- Authoring lifecycle (M43), CI (M44), memory durable de usuario (post-v1).
