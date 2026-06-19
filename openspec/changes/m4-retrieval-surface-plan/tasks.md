# Tareas M4 de superficie de retrieval

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #20 (`m3-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m4-planning` desde el `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de M3.
- [x] 1.4 Revisar specs canonicas M3 y docs de progreso/roadmap.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m4-retrieval-surface-plan`.
- [x] 2.2 Validar `openspec validate m4-retrieval-surface-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M4.

## 3. Slices futuros de M4

- [x] 3.1 Implementar `m4-retrieval-service-contract`.
- [x] 3.2 Implementar `m4-retrieval-api-endpoint`.
- [ ] 3.3 Implementar `m4-retrieval-cli-command`.
- [ ] 3.4 Ejecutar `m4-quality-gate` y archivar el change cuando M4 quede
  cerrado.
