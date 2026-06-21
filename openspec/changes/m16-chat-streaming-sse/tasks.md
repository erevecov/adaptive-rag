# Tareas M16 de streaming SSE para chat

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M15 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m16-chat-streaming-plan` desde el `origin/main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M15.
- [x] 1.4 Consultar documentacion actual de FastAPI con `ctx7` para streaming
  SSE y confirmar version local/import de `fastapi.sse`.

## 2. Change OpenSpec de M16

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m16-chat-streaming-sse`.
- [x] 2.2 Documentar que M16 define SSE por `POST`, consumo con `fetch`
  streaming, fallback no streaming y persistencia compatible con audit trail.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M16 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m16-chat-streaming-sse --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M16

- [x] 3.1 Implementar `m16-streaming-event-contract`.
- [ ] 3.2 Implementar `m16-chat-service-streaming`.
- [ ] 3.3 Implementar `m16-chat-streaming-api`.
- [ ] 3.4 Implementar `m16-chat-streaming-frontend-client`.
- [ ] 3.5 Implementar `m16-chat-streaming-ui`.
- [ ] 3.6 Ejecutar `m16-quality-gate` y archivar el change cuando se complete.
