# Propuesta M2 de schema de dominio

## Por que

M1 dejo la base de proyecto lista, pero Adaptive RAG todavia no tiene un modelo persistente para proyectos, fuentes, documentos, versiones normalizadas, chunks ni embeddings. M2 necesita fijar ese contrato antes de implementar ingestion, retrieval o chat.

## Que cambia

- Agregar el contrato de schema para entidades core de RAG.
- Definir la persistencia de texto normalizado, huellas, metadatos de parsing y offsets de citas.
- Definir columnas necesarias para metadata filtering por proyecto, fuente, documento, tipo, tags y fechas.
- Definir el baseline de embeddings densos con `vector(1024)` sin indice HNSW inicial.
- Preparar el modo experimental `dense_sparse` sin convertirlo en camino obligatorio de v1.

No se implementan todavia repositories, ingestion workers, URL fetch policy, jobs ni chat. Esos quedan como changes separados de M2 para reducir conflictos.

## Capacidades

### Capacidades nuevas

- `domain-schema`

### Capacidades modificadas

- Ninguna. No habia specs canonicas de OpenSpec antes de este change.

## Impacto

- Afectara modelos SQLAlchemy bajo `src/adaptive_rag/db`.
- Afectara migraciones Alembic bajo `alembic/versions`.
- Agregara tests de schema/migracion.
- Bloquea trabajos posteriores de repositories, ingestion y retrieval hasta que el schema base este mergeado.
