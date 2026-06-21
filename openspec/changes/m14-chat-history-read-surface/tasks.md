# Tareas M14 de lectura/historial de chat

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M13 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m14-chat-history-plan` desde el `origin/main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M13.
- [x] 1.4 Revisar `chat-audit-trail`, rutas de chat, CLI y repositories M13.

## 2. Change OpenSpec de M14

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m14-chat-history-read-surface`.
- [x] 2.2 Documentar que M14 expone lectura/historial read-only sin agregar
  frontend, streaming, dashboards, replay ni cambios de ranking.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M14 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m14-chat-history-read-surface --strict` y
  `openspec validate --specs --strict`.

## 3. Slices propuestos de M14

- [ ] 3.1 Implementar `m14-chat-history-repository-read-models`.
- [ ] 3.2 Implementar `m14-chat-history-api`.
- [ ] 3.3 Implementar `m14-chat-history-cli`.
- [ ] 3.4 Ejecutar `m14-quality-gate` y archivar el change cuando se complete.
