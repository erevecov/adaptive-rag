# Tareas M5 de chat/tool calling

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #25 (`m4-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m5-chat-tool-calling-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M4.
- [x] 1.4 Revisar specs canonicas M4 y docs de progreso/roadmap.
- [x] 1.5 Revisar la superficie actual de retrieval, API y CLI para definir
  limites de reutilizacion.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m5-chat-tool-calling-plan`.
- [x] 2.2 Validar `openspec validate m5-chat-tool-calling-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M5.

## 3. Slices futuros de M5

- [x] 3.1 Implementar `m5-chat-service-contract`.
- [x] 3.2 Implementar `m5-chat-api-endpoint`.
- [x] 3.3 Implementar `m5-chat-cli-command`.
- [x] 3.4 Ejecutar `m5-quality-gate` y archivar el change cuando M5 quede
  cerrado.
