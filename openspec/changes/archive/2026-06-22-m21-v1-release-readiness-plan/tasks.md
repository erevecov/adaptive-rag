# Tareas M21 de V1 release readiness

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #109 esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/v1-release-readiness` desde el `origin/main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M20.
- [x] 1.4 Revisar `docs/progress.md`, `docs/roadmap.md`,
  `docs/architecture/v1-design.md` y specs canonicas para ubicar brechas de
  v1.0.

## 2. Change OpenSpec de M21

- [x] 2.1 Agregar propuesta, diseno, tasks y deltas de spec para
  `m21-v1-release-readiness-plan`.
- [x] 2.2 Documentar que M21 es un milestone de readiness, no de runtime.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M21 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m21-v1-release-readiness-plan --strict`,
  `openspec validate --specs --strict`, `openspec list` y `git diff --check`.

## 3. Slices propuestos de M21

- [x] 3.1 Implementar `m21-v1-scope-reconciliation`.
- [x] 3.2 Implementar `m21-release-package-local-stack`.
- [x] 3.3 Implementar `m21-portfolio-demo-and-report`.
- [x] 3.4 Ejecutar `m21-release-quality-gate` y archivar el change cuando se
  complete.
