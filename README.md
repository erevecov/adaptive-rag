# Adaptive RAG

Sistema RAG personal, aislado por proyecto, pensado para aprendizaje y
portafolio.

## Desarrollo local

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
```

## Smoke Neo4j opt-in

Neo4j no forma parte del stack obligatorio. Para validar un entorno live local o
managed, configura `graph_store=neo4j` por variables `ADAPTIVE_RAG_*` y ejecuta
el smoke de conectividad:

```bash
uv run adaptive-rag graph neo4j-smoke
```

Ruta local esperada: Neo4j Desktop o Docker exponiendo Bolt en `7687`, por
ejemplo `ADAPTIVE_RAG_NEO4J_URI=neo4j://localhost:7687`.

Ruta managed esperada: URI cifrada tipo `neo4j+s://...` con username/password
desde env. El smoke serializa solo scheme/clasificacion de URI, status y error
code; no imprime host completo ni password.

## Backfill/reindex Neo4j opt-in

Con `graph_store=neo4j` configurado, la proyeccion graph derivada se reconstruye
por proyecto:

```bash
uv run adaptive-rag graph backfill <project-id> --source-watermark chunks:v1
uv run adaptive-rag graph reindex <project-id> --source-watermark chunks:v2
```

Los comandos imprimen un reporte JSON con status, duracion, conteos y error
code. Salen con codigo `0` solo cuando la proyeccion termina en `ready`.

## Documentación

La documentación del repositorio se escribe en español. Se mantienen en inglés
los nombres de comandos, APIs, paquetes y términos técnicos cuando eso evita
ambigüedad.
