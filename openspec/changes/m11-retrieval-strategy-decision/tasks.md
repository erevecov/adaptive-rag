# Tareas M11 de decision de estrategia de retrieval

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #62 (`m10-quality-gate`) esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m11-retrieval-strategy-decision` desde el
  `main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M10.
- [x] 1.4 Revisar `retrieval-quality`, decision gates y roadmap/progress.
- [x] 1.5 Intentar resolver docs actuales Model Studio/DashScope con `ctx7`
  antes de mencionar Qwen sparse retrieval.

## 2. Change OpenSpec de decision

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m11-retrieval-strategy-decision`.
- [x] 2.2 Documentar decision matrix de candidate tuning, lexical/RRF y Qwen
  sparse retrieval.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M11 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m11-retrieval-strategy-decision --strict`.

## 3. Slices futuros de M11

- [x] 3.1 Implementar `m11-candidate-limit-eval-matrix`.
- [x] 3.2 Implementar `m11-candidate-limit-ab-runner`.
- [ ] 3.3 Implementar `m11-candidate-limit-api-cli-surface` si la evidencia lo
  justifica.
- [ ] 3.4 Ejecutar `m11-quality-gate` y archivar el change cuando M11 quede
  cerrado.
