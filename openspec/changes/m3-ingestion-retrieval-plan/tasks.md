# Tareas M3 de ingestion y retrieval

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #14 (`m2-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m3-ingestion-retrieval-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos antes de M3.
- [x] 1.4 Revisar `docs/architecture/v1-design.md`, specs canonicas M2 y docs
  de progreso/roadmap.

## 2. Change OpenSpec de plan

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m3-ingestion-retrieval-plan`.
- [x] 2.2 Validar `openspec validate m3-ingestion-retrieval-plan --strict`.
- [x] 2.3 Actualizar `docs/progress.md` y `docs/roadmap.md` con el change
  activo y la secuencia refinada de M3.

## 3. Slices futuros de M3

- [x] 3.1 Implementar `m3-ingestion-pipeline`.
- [x] 3.2 Implementar `m3-chunking-baseline`.
- [x] 3.3 Implementar `m3-embedding-baseline`.
- [ ] 3.4 Implementar `m3-retrieval-baseline`.
- [ ] 3.5 Ejecutar `m3-quality-gate` y archivar el change cuando M3 quede
  cerrado.
