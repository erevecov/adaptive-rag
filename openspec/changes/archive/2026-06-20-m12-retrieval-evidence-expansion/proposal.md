# Propuesta M12 de expansion de evidencia de retrieval

## Why

M11 cerro el tuning de `candidate_limit` sin promover presets ni nueva
superficie API/CLI. La evidencia offline mostro que `candidate_limit=8` mejora
el hit rate agregado, pero mantiene una regresion en
`distractor-alpha-release-notes`; el smoke hosted Qwen paso la suite actual,
pero no elimina la brecha de cobertura.

Antes de abrir lexical/RRF, sparse retrieval o nuevos providers, el proyecto
necesita evidencia versionada mas amplia sobre distractors y lexical misses. La
opcion recomendada para M12 es ampliar el dataset y el reporte de gaps, no
implementar otro algoritmo.

## What Changes

- Crear el change OpenSpec `m12-retrieval-evidence-expansion`.
- Modificar la capacidad `retrieval-quality` para exigir una expansion de
  evidencia antes de proponer nuevas estrategias de retrieval.
- Definir una secuencia M12 para:
  - formalizar taxonomia de casos de riesgo;
  - ampliar suites con distractors y lexical misses versionados;
  - reportar gaps/regresiones por caso antes que agregados;
  - refrescar la decision sobre lexical/RRF, sparse retrieval y candidate
    tuning con evidencia nueva.
- Agregar una nota de arquitectura con el alcance y los criterios de no-go de
  M12.
- Actualizar `docs/progress.md` y `docs/roadmap.md` con M12 activo.
- Mantener fuera de este PR cambios a runtime, ranking productivo, DB schema,
  providers, API, CLI o defaults de retrieval.

## Capacidades

### Capacidades nuevas

- Ninguna.

### Capacidades modificadas

- `retrieval-quality`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega `docs/architecture/retrieval-evidence-expansion.md`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo.
- No requiere credenciales live para validar este PR de planificacion.
