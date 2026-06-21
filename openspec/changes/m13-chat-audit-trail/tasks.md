# Tareas M13 de audit trail de chat

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M12 esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m13-chat-audit-trail-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M12.
- [x] 1.4 Revisar specs canonicas de chat, provider runtime, schema y la linea
  base de arquitectura v1.

## 2. Change OpenSpec de M13

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m13-chat-audit-trail`.
- [x] 2.2 Documentar que M13 persiste audit trail durable sin agregar streaming,
  historial, dashboards ni cambios de ranking.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M13 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m13-chat-audit-trail --strict` y
  `openspec validate --specs --strict`.

## 3. Slices implementados de M13

- [x] 3.1 Implementar `m13-audit-schema`.
- [x] 3.2 Implementar `m13-audit-repositories`.
- [x] 3.3 Implementar `m13-chat-service-audit-wiring`.
- [x] 3.4 Implementar `m13-api-cli-audit-surface`.
- [x] 3.5 Implementar `m13-provider-usage-linking`.
- [x] 3.6 Ejecutar `m13-quality-gate` y dejar el change activo hasta que se
  solicite archive explicito.
