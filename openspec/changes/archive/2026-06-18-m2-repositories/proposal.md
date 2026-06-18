# Propuesta M2 de repositories

## Why

El schema de dominio ya esta mergeado y archivado, pero Adaptive RAG todavia no tiene una capa de acceso a datos que haga obligatorio el aislamiento por `project_id`. Antes de ingestion, retrieval o chat, las operaciones sobre proyectos, sources, documents, versions y chunks necesitan un contrato pequeno y testeado.

## What Changes

- Agregar repositories SQLAlchemy sincronicos sobre la `Session` existente.
- Hacer que toda lectura o busqueda multi-tenant reciba `project_id`.
- Agregar filtros tipados para sources y documents usando columnas ya indexadas.
- Agregar helpers para crear versiones y chunks sin mezclar ingestion policy ni retrieval ranking.
- Mantener commits controlados por el caller; los repositories agregan/leen objetos, pero no llaman `commit()`.

No se implementan endpoints, ingestion workers, job queue, URL fetch policy, retrieval vectorial ni chat. Esos quedan como changes separados.

## Capacidades

### Capacidades nuevas

- `repositories`

### Capacidades modificadas

- Ninguna. `domain-schema` queda como dependencia canonica ya archivada.

## Impacto

- Agregara codigo bajo `src/adaptive_rag/db/repositories/`.
- Agregara tests unitarios sobre SQLite in-memory para el contrato repository.
- Actualizara `docs/progress.md` para reflejar el change activo.
- No agregara migraciones Alembic.

