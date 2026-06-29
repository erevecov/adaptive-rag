# Tasks M39 chat stepper live events

- [x] 1. OpenSpec
  - [x] 1.1 Crear proposal, tasks y deltas para `chat-streaming`,
    `chat-frontend` y `chat-history`.
  - [x] 1.2 Validar `npx --yes @fission-ai/openspec validate
    m39-chat-stepper-live-events --strict`.

- [x] 2. Backend streaming y persistencia
  - [x] 2.1 Agregar tests fallidos para serializacion de eventos `step`.
  - [x] 2.2 Agregar tests fallidos para orden de eventos `step` en
    `ChatService.stream`.
  - [x] 2.3 Agregar tests fallidos para metadata `steps` persistida en el
    mensaje assistant.
  - [x] 2.4 Implementar tipos, factories y serializacion de `step`.
  - [x] 2.5 Emitir steps `answer` y `retrieval` sin cambiar el payload `final`.
  - [x] 2.6 Persistir solo steps terminales en `metadata_json.steps`.

- [x] 3. Frontend stepper
  - [x] 3.1 Agregar tests fallidos para parsing SSE `step`.
  - [x] 3.2 Agregar tests fallidos para parsing tolerante de metadata steps.
  - [x] 3.3 Agregar tests fallidos para preferencia `localStorage`.
  - [x] 3.4 Implementar tipos/helpers en `frontend/src/lib/chatSteps.ts`.
  - [x] 3.5 Implementar `frontend/src/lib/stepperPreference.ts`.
  - [x] 3.6 Implementar renderer `ChatPipelineSteps`.
  - [x] 3.7 Wirear streaming, respuesta final e historial en `App.tsx`.

- [x] 4. Validacion y PR
  - [x] 4.1 Ejecutar tests backend relevantes.
  - [x] 4.2 Ejecutar tests frontend relevantes.
  - [x] 4.3 Ejecutar typecheck/lint relevantes, OpenSpec strict y
    `git diff --check`.
  - [x] 4.4 Commit, push y actualizar el PR existente.
