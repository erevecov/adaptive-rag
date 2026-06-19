# Tareas M6 de evals

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #30 (`m5-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m6-evals-plan` desde el `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M5.
- [x] 1.4 Revisar specs canonicas M4/M5 y docs de progreso/roadmap.
- [x] 1.5 Revisar la superficie actual de retrieval, chat, API y CLI para
  definir limites de reutilizacion.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m6-evals-plan`.
- [x] 2.2 Validar `openspec validate m6-evals-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M6.

## 3. Slices futuros de M6

- [x] 3.1 Implementar `m6-evals-fixtures-contract`.
- [x] 3.2 Implementar `m6-retrieval-eval-runner`.
- [x] 3.3 Implementar `m6-chat-eval-runner`.
- [ ] 3.4 Implementar `m6-evals-cli-reporting`.
- [ ] 3.5 Ejecutar `m6-quality-gate` y archivar el change cuando M6 quede
  cerrado.
