# Propuesta M11 de decision de estrategia de retrieval

## Why

M10 cerro datasets representativos, metadata por caso, reportes A/B dense vs
rerank y decision gates. Eso evita implementar lexical/RRF, sparse retrieval o
tuning de parametros por intuicion, pero todavia falta elegir el primer
experimento medible.

La opcion recomendada para empezar M11 es tuning de `candidate_limit` y limites
relacionados de rerank. Reutiliza el pipeline dense/rerank existente, no agrega
indexes ni providers nuevos y permite medir el tradeoff calidad/costo con el
harness ya disponible. Lexical/RRF y Qwen sparse quedan en hold hasta que una
suite muestre fallos que candidate tuning/rerank no resuelven y hasta verificar
documentacion provider actualizada para sparse.

## What Changes

- Crear el change OpenSpec `m11-retrieval-strategy-decision`.
- Documentar la decision M11: ejecutar primero un experimento acotado de tuning
  de `candidate_limit`, manteniendo dense como default.
- Modificar la capacidad `retrieval-quality` para exigir una decision matrix
  antes de implementar nuevos algoritmos o indexes.
- Agregar una nota de arquitectura con estado `proceed`/`hold`/`no-go` para:
  tuning de candidate limits, lexical/RRF y Qwen sparse retrieval.
- Actualizar `docs/progress.md` y `docs/roadmap.md` con M11 activo y la
  secuencia recomendada.
- Mantener fuera de este PR cambios a runtime, DB schema, providers, API, CLI o
  fixtures de evals.

## Capacidades

### Capacidades nuevas

- Ninguna.

### Capacidades modificadas

- `retrieval-quality`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega `docs/architecture/retrieval-strategy-decision.md`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo.
- No requiere credenciales live para validar este PR de decision.

