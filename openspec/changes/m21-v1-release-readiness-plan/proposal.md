# Propuesta M21 de V1 release readiness

## Why

M20 cerro el dashboard de observability y dejo el roadmap M1-M20 completo, sin
changes OpenSpec activos. El sistema ya tiene un core demostrable: dominio
multi-project, ingestion base, dense retrieval, chat con citations, evals,
providers Qwen opt-in, rerank, audit trail, historial, streaming, frontend y
observability.

La brecha ya no es construir otra capability de producto a ciegas. La brecha es
decidir con precision que significa v1.0 despues de M1-M20: que queda dentro,
que se difiere, que evidencia falta y que PRs finales convierten el core en una
release publicable de portafolio.

`docs/architecture/v1-design.md` aun incluye objetivos originales que hoy no
estan cerrados o quedaron en hold, como Qwen sparse/dense_sparse productivo,
Postgres full-text/RRF, Docker Compose completo, demo script y reporte final de
evals/costo/latencia. M10-M12 ya exigieron evidencia antes de abrir
lexical/RRF o sparse retrieval, y M19 mantuvo graph en `hold_default`. M21 debe
evitar que v1.0 se infle por inercia y convertir el 75-85% estimado en una
checklist ejecutable.

## What Changes

- Crear el change OpenSpec `m21-v1-release-readiness-plan`.
- Agregar la capability `v1-release-readiness` para declarar requisitos de
  scope, readiness audit, release package y evidencia final.
- Documentar la decision recomendada: recortar v1.0 a un vertical slice
  demostrable sobre el core M1-M20 y diferir lexical/RRF, Qwen sparse local o
  hosted sparse, graph rollout/defaults y voz salvo evidencia nueva.
- Definir una secuencia M21 para:
  - reconciliar `v1-design.md` contra M1-M20 y clasificar cada item como
    `in_v1`, `defer_post_v1` o `blocked`;
  - cerrar el contrato de release package local-first;
  - agregar demo script, README de portafolio y reporte reproducible;
  - ejecutar un quality gate final y archivar M21.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M21
  activo.

## Capacidades

### Capacidades nuevas

- `v1-release-readiness`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M21.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python ni frontend.
- No agrega Docker Compose, scripts de demo, sparse retrieval, lexical/RRF,
  providers nuevos, graph defaults ni cambios de runtime.
