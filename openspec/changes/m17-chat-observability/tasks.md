# Tareas M17 de observability de chat y costo-latencia

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M16 esta mergeado y archivado en `main`.
- [x] 1.2 Crear branch `codex/m17-chat-observability-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M16.
- [x] 1.4 Confirmar que M17 queda acotado a API/CLI read-only, sin dashboard
  avanzado, frontend, nuevas tablas ni OpenTelemetry.

## 2. Change OpenSpec de M17

- [x] 2.1 Agregar propuesta, diseno, tasks y spec nueva para
  `m17-chat-observability`.
- [x] 2.2 Documentar contrato de resumen por proyecto, filtros, agregados de
  sesiones, provider usage, latencias y errores.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M17 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m17-chat-observability --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M17

- [ ] 3.1 Implementar `m17-observability-read-models`.
- [ ] 3.2 Implementar `m17-observability-api`.
- [ ] 3.3 Implementar `m17-observability-cli`.
- [ ] 3.4 Ejecutar `m17-quality-gate` y archivar el change cuando se complete.
