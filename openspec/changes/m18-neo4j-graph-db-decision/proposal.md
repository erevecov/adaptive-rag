# Propuesta M18 de Neo4j graph DB decision

## Why

M17 cerro observability de chat/costo-latencia y dejo el sistema con chat,
historial, streaming, audit trail y resumen operativo por API/CLI. El siguiente
riesgo de producto no es agregar complejidad de retrieval sin evidencia: el
backlog ya identifica Neo4j como graph DB opcional, pero todavia falta una
decision tecnica verificable antes de introducir un segundo storage operativo.

Adaptive RAG usa Postgres como fuente durable principal y dense retrieval como
baseline. M18 debe decidir si conviene abrir la ruta graph DB, bajo que
condiciones, con que alternativa, y con que gates de calidad. La opcion
recomendada es comenzar con una decision matrix y un contrato routeable, no con
un adapter Neo4j live. Esto evita acoplar storage, retrieval, setup local y evals
antes de confirmar el valor esperado.

## What Changes

- Crear el change OpenSpec `m18-neo4j-graph-db-decision`.
- Agregar la capacidad `graph-store` para definir:
  - decision matrix de Neo4j vs alternativas locales/managed;
  - alcance routeable con `graph_store=disabled` como default;
  - grafo como indice derivado y reconstruible desde Postgres;
  - criterios de local setup, managed setup, health checks y errores estables;
  - gates de retrieval/evals antes de promover cualquier default.
- Definir una secuencia M18 para:
  - documentar decision matrix;
  - definir contrato `GraphStore` y fakes offline;
  - agregar adapter/indexer solo despues de validar el contrato;
  - agregar ruta retrieval graph opt-in;
  - cerrar con evals comparativas y archive.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M18
  activo.

## Capacidades

### Capacidades nuevas

- `graph-store`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M18.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python, frontend,
  settings, dependencias, migrations ni infraestructura.
- No agrega Neo4j driver, Docker Compose, adapter live, indexer, retrieval
  graph, nuevas tablas ni cambios de defaults.
