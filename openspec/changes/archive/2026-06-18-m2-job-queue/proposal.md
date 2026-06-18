# Propuesta M2 de job queue

## Why

Adaptive RAG ya tiene schema de dominio y repositories, pero ingestion todavia no puede persistir trabajo asincronico ni recuperarse de fallos. Antes de conectar URL fetching, parsing o chunking, el sistema necesita jobs, eventos auditables, retries y leasing basico de workers.

## What Changes

- Agregar tablas `jobs` y `job_events` con aislamiento por `project_id`.
- Agregar modelos SQLAlchemy para jobs y eventos.
- Agregar un `JobRepository` sincronico con `Session` inyectada y sin `commit()` interno.
- Implementar creacion de jobs, leasing, completion, retry, blocked/dead-letter y liberacion de leases vencidos.
- Agregar tests unitarios e integracion de migracion Postgres.

No se implementan workers reales, ingestion pipeline, URL fetch policy, scheduling externo ni procesamiento de payloads.

## Capacidades

### Capacidades nuevas

- `job-queue`

### Capacidades modificadas

- Ninguna. `domain-schema` y `repositories` quedan como dependencias canonicas ya archivadas.

## Impacto

- Afectara modelos SQLAlchemy bajo `src/adaptive_rag/db/models/`.
- Afectara repositories bajo `src/adaptive_rag/db/repositories/`.
- Agregara una migracion Alembic bajo `alembic/versions/`.
- Agregara tests unitarios y de integracion DB.

