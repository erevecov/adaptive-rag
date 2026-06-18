# Tareas M2 de schema de dominio

## 1. Planificacion y setup

- [x] 1.1 Confirmar que este change OpenSpec esta aprobado para implementacion.
- [x] 1.2 Crear una branch de implementacion desde el `origin/main` actual.
- [x] 1.3 Ejecutar `uv sync --extra dev` y `uv run pytest` para confirmar el baseline.

## 2. Modelos SQLAlchemy

- [x] 2.1 Agregar tests que fallen para defaults de proyecto y constraints de `embedding_mode`.
- [x] 2.2 Agregar modelos SQLAlchemy para `projects`, `sources`, `documents` y `document_versions`.
- [x] 2.3 Agregar tests que fallen para offsets de citas de chunks y dimensiones de embeddings densos.
- [x] 2.4 Agregar modelos SQLAlchemy para `chunks` y `chunk_sparse_embeddings`.

## 3. Migracion Alembic

- [x] 3.1 Agregar una migracion que habilite la extension `vector` cuando sea necesario.
- [x] 3.2 Agregar tablas, foreign keys, uniqueness constraints y check constraints.
- [x] 3.3 Agregar indices para aislamiento por proyecto y metadata filtering.
- [x] 3.4 Mantener dense retrieval exacto; no agregar HNSW en este change.

## 4. Validacion de integracion

- [x] 4.1 Agregar tests de integracion Postgres/pgvector para aplicar la migracion.
- [x] 4.2 Verificar `chunks.embedding vector(1024)` con un container Postgres real.
- [x] 4.3 Verificar que filtros por project/source/document tengan columnas indexadas.

## 5. Quality gate y handoff

- [x] 5.1 Ejecutar `uv run pytest`.
- [x] 5.2 Ejecutar `uv run ruff check .`.
- [x] 5.3 Ejecutar `uv run mypy src`.
- [x] 5.4 Actualizar `docs/progress-log/` con una entrada nueva de cierre.
- [ ] 5.5 Abrir un PR y no empezar trabajo de repository layer hasta que el PR de schema este mergeado.
