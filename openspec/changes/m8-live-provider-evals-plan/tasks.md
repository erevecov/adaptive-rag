# Tareas M8 de hosted evals

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #43 (`m7-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m8-live-provider-evals-plan` desde el `main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M7.
- [x] 1.4 Revisar specs canonicas de evals y provider runtime.
- [x] 1.5 Revisar runners actuales de evals, fixtures, CLI y usage/cost para
  definir puntos de extension hosted.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m8-live-provider-evals-plan`.
- [x] 2.2 Validar `openspec validate m8-live-provider-evals-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M8.

## 3. Slices futuros de M8

- [ ] 3.1 Implementar `m8-hosted-eval-contract`.
- [ ] 3.2 Implementar `m8-live-retrieval-eval-runner`.
- [ ] 3.3 Implementar `m8-live-chat-eval-runner`.
- [ ] 3.4 Implementar `m8-evals-cli-hosted-mode`.
- [ ] 3.5 Ejecutar `m8-quality-gate` y archivar el change cuando M8 quede
  cerrado.
