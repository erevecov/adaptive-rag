# Tareas M15 de frontend inicial de chat

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M14 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m15-chat-frontend-plan` desde el `origin/main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M14.
- [x] 1.4 Confirmar que el repo no tiene frontend existente ni lockfile Node.
- [x] 1.5 Consultar documentacion actual de Vite con `ctx7` para el scaffold
  React TypeScript recomendado.

## 2. Change OpenSpec de M15

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m15-chat-frontend-plan`.
- [x] 2.2 Documentar que M15 define UI inicial sobre `POST /chat` y
  `chat-history`, sin streaming SSE, dashboards, replay ni auth final.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M15 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m15-chat-frontend-plan --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M15

- [x] 3.1 Implementar `m15-frontend-scaffold`.
- [ ] 3.2 Implementar `m15-chat-api-client`.
- [ ] 3.3 Implementar `m15-chat-workspace-ui`.
- [ ] 3.4 Implementar `m15-chat-history-ui`.
- [ ] 3.5 Ejecutar `m15-quality-gate` y archivar el change cuando se complete.
