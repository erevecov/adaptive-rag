# Propuesta M22 de V1 product scope reset

## Why

M21 dejo un core local-first demostrable, empaquetado y validado, pero el
resultado todavia no es un producto real terminado. El enfoque anterior llamaba
v1.0 a una release de portafolio conservadora y diferia authoring,
onboarding, ingestion operativa desde UI/API/CLI, estados de jobs visibles y
errores user-facing. Ese corte es util como evidencia de core, pero no debe
convertirse en la definicion final de v1.

La nueva decision de producto es mas estricta: v1 significa producto terminado.
Para este repositorio, eso debe ser un producto local-first single-user que una
persona pueda instalar, configurar, alimentar con sus propios documentos,
consultar, auditar y operar sin scripts internos, fixtures ocultos ni pasos de
base de datos manuales fuera del runbook publico.

## What Changes

- Crear el change OpenSpec `m22-v1-product-scope-reset`.
- Agregar la capability `v1-product-completion`.
- Reinterpretar `v1-release-readiness`: M21 queda como core/pre-v1 readiness, no
  como autorizacion para tag o release final v1.0.
- Actualizar roadmap, progress, arquitectura y README para declarar que no se
  debe cortar v1.0 hasta completar el backlog de producto.
- Definir los bloques obligatorios para v1 terminada:
  - authoring de projects/sources desde superficies publicas;
  - ingestion end-to-end con estado visible y recuperacion de errores;
  - onboarding/setup local-first sin depender de fixtures internas;
  - experiencia principal de chat/retrieval sobre datos propios;
  - evidencia de demo con datos propios y docs de operacion.

## Capacidades

### Capacidades nuevas

- `v1-product-completion`

### Capacidades modificadas

- `v1-release-readiness`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Reemplaza la recomendacion de tag/manual release v1.0 por un roadmap de
  producto terminado.
- No cambia codigo Python, frontend, schema, Docker ni runtime en este PR.
- No reabre lexical/RRF, Qwen sparse, graph default, auth multi-user, voice,
  MCP o PDF/Office por inercia; esos siguen requiriendo evidencia y OpenSpec.
