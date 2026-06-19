# Tareas M7 de provider runtime

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #36 (`m6-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m7-provider-runtime-plan` desde el `main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M6.
- [x] 1.4 Revisar specs canonicas de embeddings, retrieval, chat y evals.
- [x] 1.5 Revisar factories actuales de providers, settings y dependencias
  API/CLI para definir puntos de inyeccion.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m7-provider-runtime-plan`.
- [x] 2.2 Validar `openspec validate m7-provider-runtime-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M7.

## 3. Slices futuros de M7

- [x] 3.1 Implementar `m7-provider-settings-contract`.
- [x] 3.2 Implementar `m7-live-embedding-provider`.
- [x] 3.3 Implementar `m7-live-chat-runner`.
- [x] 3.4 Implementar `m7-usage-cost-limits`.
- [x] 3.5 Ejecutar `m7-quality-gate` y archivar el change cuando M7 quede
  cerrado.
