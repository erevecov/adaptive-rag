# Tareas M12 de expansion de evidencia de retrieval

## 1. Planificacion y setup

- [x] 1.1 Confirmar que M11 esta mergeado en `main`.
- [x] 1.2 Crear branch `codex/m12-retrieval-evidence-plan` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M11.
- [x] 1.4 Revisar `retrieval-quality`, decision gates, evidencia A/B de M11 y
  roadmap/progress.

## 2. Change OpenSpec de M12

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para
  `m12-retrieval-evidence-expansion`.
- [x] 2.2 Documentar que M12 mide distractors/lexical misses antes de abrir
  lexical/RRF, sparse retrieval o nuevos defaults.
- [x] 2.3 Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con
  M12 activo y la siguiente secuencia recomendada.
- [x] 2.4 Validar `openspec validate m12-retrieval-evidence-expansion --strict`
  y `openspec validate --specs --strict`.

## 3. Slices futuros de M12

- [x] 3.1 Implementar `m12-evidence-case-taxonomy`.
- [x] 3.2 Implementar `m12-distractor-lexical-dataset-pack`.
- [x] 3.3 Implementar `m12-evidence-gap-reporting`.
- [x] 3.4 Implementar `m12-strategy-decision-refresh`.
- [x] 3.5 Ejecutar `m12-quality-gate` y archivar el change cuando M12 quede
  cerrado.
