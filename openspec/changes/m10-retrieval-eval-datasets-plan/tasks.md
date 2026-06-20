# Tareas M10 de datasets y decision gates de retrieval

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #56 (`m9-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m10-retrieval-quality-plan` desde el `main`
  actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M9.
- [x] 1.4 Revisar specs canonicas de retrieval quality, hosted evals y evals
  baseline.
- [x] 1.5 Revisar fixtures, runners de evals, reportes comparativos y
  `RetrievalService` para definir la frontera de M10.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m10-retrieval-eval-datasets-plan`.
- [x] 2.2 Validar `openspec validate m10-retrieval-eval-datasets-plan
  --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M10.

## 3. Slices futuros de M10

- [x] 3.1 Implementar `m10-eval-case-metrics`.
- [x] 3.2 Implementar `m10-retrieval-dataset-pack`.
- [ ] 3.3 Implementar `m10-rerank-ab-reporting`.
- [ ] 3.4 Implementar `m10-decision-gate-docs`.
- [ ] 3.5 Ejecutar `m10-quality-gate` y archivar el change cuando M10 quede
  cerrado.
