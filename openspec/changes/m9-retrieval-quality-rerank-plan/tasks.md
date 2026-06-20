# Tareas M9 de calidad de retrieval/rerank

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #49 (`m8-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m9-retrieval-quality-rerank-plan` desde el
  `main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M8.
- [x] 1.4 Revisar specs canonicas de retrieval, provider runtime y hosted
  evals.
- [x] 1.5 Revisar `RetrievalService`, `DenseRetriever`, evals hosted y
  `ProviderOperation` para definir la frontera de rerank.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m9-retrieval-quality-rerank-plan`.
- [x] 2.2 Validar `openspec validate m9-retrieval-quality-rerank-plan
  --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia inicial de M9.

## 3. Slices futuros de M9

- [x] 3.1 Implementar `m9-rerank-provider-contract`.
- [ ] 3.2 Implementar `m9-live-qwen-rerank-provider`.
- [ ] 3.3 Implementar `m9-retrieval-rerank-service`.
- [ ] 3.4 Implementar `m9-rerank-api-cli-surface`.
- [ ] 3.5 Implementar `m9-rerank-hosted-evals`.
- [ ] 3.6 Ejecutar `m9-quality-gate` y archivar el change cuando M9 quede
  cerrado.

