# Tareas M2 de schema de dominio

## 1. Planificacion y setup

- [ ] 1.1 Confirmar que este change OpenSpec esta aprobado para implementacion.
- [ ] 1.2 Crear una branch de implementacion desde el `origin/main` actual.
- [ ] 1.3 Ejecutar `uv sync --extra dev` y `uv run pytest` para confirmar el baseline.

## 2. Modelos SQLAlchemy

- [ ] 2.1 Agregar tests que fallen para defaults de proyecto y constraints de `embedding_mode`.
- [ ] 2.2 Agregar modelos SQLAlchemy para `projects`, `sources`, `documents` y `document_versions`.
- [ ] 2.3 Agregar tests que fallen para offsets de citas de chunks y dimensiones de embeddings densos.
- [ ] 2.4 Agregar modelos SQLAlchemy para `chunks` y `chunk_sparse_embeddings`.

## 3. Migracion Alembic

- [ ] 3.1 Agregar una migracion que habilite la extension `vector` cuando sea necesario.
- [ ] 3.2 Agregar tablas, foreign keys, uniqueness constraints y check constraints.
- [ ] 3.3 Agregar indices para aislamiento por proyecto y metadata filtering.
- [ ] 3.4 Mantener dense retrieval exacto; no agregar HNSW en este change.

## 4. Validacion de integracion

- [ ] 4.1 Agregar tests de integracion Postgres/pgvector para aplicar la migracion.
- [ ] 4.2 Verificar `chunks.embedding vector(1024)` con un container Postgres real.
- [ ] 4.3 Verificar que filtros por project/source/document tengan columnas indexadas.

## 5. Quality gate y handoff

- [ ] 5.1 Ejecutar `uv run pytest`.
- [ ] 5.2 Ejecutar `uv run ruff check .`.
- [ ] 5.3 Ejecutar `uv run mypy src`.
- [ ] 5.4 Actualizar `docs/progress-log/` con una entrada nueva de cierre.
- [ ] 5.5 Abrir un PR y no empezar trabajo de repository layer hasta que el PR de schema este mergeado.
