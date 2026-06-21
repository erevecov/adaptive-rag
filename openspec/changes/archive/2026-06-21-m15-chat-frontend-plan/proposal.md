# Propuesta M15 de frontend inicial de chat

## Why

M14 cerro la superficie backend read-only para historial de chat: la API ya
puede listar sesiones y consultar detalle auditable por proyecto. El repo aun
no tiene frontend (`package.json`, Vite/Next o archivos TS/JS), por lo que el
siguiente riesgo no es agregar streaming ni dashboards, sino definir primero
una UI base que consuma los contratos existentes sin inventar queries internas.

Adaptive RAG necesita una primera experiencia operativa para enviar preguntas,
ver la respuesta con citations y navegar sesiones persistidas. Esa experiencia
debe estar delimitada antes de scaffoldar dependencias frontend para evitar
mezclar stack setup, UX, streaming, replay y reporting en un solo PR.

## What Changes

- Crear el change OpenSpec `m15-chat-frontend-plan`.
- Agregar la capacidad `chat-frontend` para definir:
  - scaffold frontend inicial bajo un directorio dedicado;
  - cliente API tipado para `POST /projects/{project_id}/chat` y los endpoints
    `chat-history`;
  - vista principal de chat con citations y estado de envio;
  - listado/detalle de sesiones persistidas;
  - boundaries explicitos contra secretos, streaming, dashboards y replay.
- Definir una secuencia M15 para:
  - crear el scaffold React/TypeScript con Vite;
  - agregar configuracion de API base y cliente fetch;
  - construir la experiencia de chat;
  - construir historial read-only;
  - validar build/lint/test y handoff local.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M15
  activo.

## Capacidades

### Capacidades nuevas

- `chat-frontend`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M15.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no agrega `package.json`, lockfiles ni codigo
  frontend productivo.
- No cambia API/CLI backend, ranking, providers, rerank, datasets de eval,
  defaults de retrieval, streaming SSE, dashboards, replay ni auth final.
