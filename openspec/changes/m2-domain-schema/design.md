# M2 Domain Schema Design

## Context

Adaptive RAG v1 sera local-first y aislado por proyecto. El almacenamiento principal es Postgres con pgvector. M1 ya agrego settings, SQLAlchemy base, Alembic, FastAPI health y CLI.

## Goals

- Crear un schema relacional suficiente para persistir proyectos, sources, documents, document_versions, chunks y sparse embeddings.
- Mantener el retrieval denso exacto como baseline de correctness.
- Guardar datos suficientes para citas reproducibles: `normalized_text`, offsets y fingerprints.
- Preparar metadata filtering sin depender de joins ambiguos o estado global.

## Non-Goals

- No implementar ingestion.
- No implementar repositories.
- No crear jobs ni workers en este change.
- No agregar HNSW hasta tener evals de recall/latencia.
- No implementar contextual retrieval; solo reservar campos para datos posteriores.

## Decisions

### D1. Schema primero, repositories despues

La migracion y los modelos deben mergearse antes de los repositories. Esto evita conflictos entre worktrees sobre `alembic/versions` y permite que los tests de repositories dependan de un schema estable.

### D2. Exact dense baseline primero

`chunks.embedding` usara `vector(1024)` sin HNSW inicial. La primera implementacion de retrieval debe poder probar correctness con escaneo exacto antes de optimizar.

### D3. Versiones de documento son el ancla de citas

`document_versions.normalized_text` es el texto fuente para offsets de citas. `chunks.document_version_id`, `char_start` y `char_end` apuntan a esa version, no al HTML original ni a texto mutable.

### D4. Sparse experimental aislado

`chunk_sparse_embeddings` se modela como tabla separada. El proyecto controla el modo con `projects.embedding_mode` (`dense` o `dense_sparse`) para que el camino estable no pague complejidad sparse si no se usa.

## Risks and Mitigations

- Riesgo: una migracion grande puede generar conflictos. Mitigacion: solo un PR activo debe tocar Alembic/modelos durante este change.
- Riesgo: modelar campos antes de ingestion puede sobredisenar. Mitigacion: incluir solo campos ya requeridos por el spec v1 y dejar comportamiento en changes posteriores.
- Riesgo: pgvector no se valida con SQLite. Mitigacion: agregar tests de integracion con Postgres/pgvector en el plan de implementacion.

## Rollout

1. Agregar modelos SQLAlchemy.
2. Agregar migracion Alembic.
3. Validar migracion en Postgres/pgvector.
4. Cerrar el change y continuar con repositories en otro branch.

