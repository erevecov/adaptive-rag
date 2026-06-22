# Diseno M18 de Neo4j graph DB decision

## Contexto

M17 dejo observability local-first para chat, costo, usage, latencia y errores.
El sistema ya tiene una base v1 razonable: ingestion, dense retrieval, chat,
audit trail, historial, frontend inicial, streaming y observability por API/CLI.

El backlog futuro propone Neo4j como graph DB routeable para retrieval graph.
Ese movimiento puede aportar consultas relacionales/estructurales, traversal y
mejor navegacion de relaciones entre documentos/chunks, pero tambien agrega un
segundo storage operativo, setup local/managed, indexacion derivada, health
checks, errores nuevos y potencial drift frente a Postgres.

Context7 se consulto para validar terminologia actual de Neo4j:

- el driver oficial de Python usa `GraphDatabase.driver(uri, auth=...)` y
  `verify_connectivity()` para comprobar conectividad;
- los drivers documentan URIs tipo `neo4j://localhost` para local y
  `neo4j+s://...databases.neo4j.io` para conexiones cifradas gestionadas;
- AuraDB requiere URI, username y password desde la instancia managed.

## Decision

La decision recomendada es `proceed` con M18 como decision y plan routeable,
sin implementacion live inicial:

- documentar una decision matrix Neo4j vs alternativas locales/managed;
- mantener Postgres como fuente durable de verdad;
- tratar cualquier graph DB como indice derivado y reconstruible;
- permitir que graph store este deshabilitado durante ingestion o updates sin
  perder la capacidad de reconstruir Neo4j mediante backfill posterior desde
  Postgres;
- mantener `graph_store=disabled` como default hasta que evals versionadas
  demuestren mejora;
- definir primero contrato `GraphStore`, settings, errores, health checks y
  fakes offline;
- introducir adapter Neo4j live solo en un slice posterior y opt-in;
- no cambiar retrieval defaults, API/CLI existentes ni provider runtime en el
  primer slice.

Esta decision mantiene la complejidad controlada y fuerza evidencia antes de
sumar una base de datos operacional.

Despues de completar `m18-graph-db-decision-matrix`, la decision concreta es:
Neo4j `proceed` como primer backend live opt-in; Memgraph y FalkorDB `hold`;
Kuzu `no-go` para el backend routeable de M18; no-op queda como fallback si las
evals posteriores no justifican graph retrieval. La matriz completa esta en
`docs/architecture/graph-db-decision-matrix-m18.md`.

## Objetivos

- Decidir si Neo4j merece avanzar frente a FalkorDB, Memgraph, Kuzu y no-op.
- Definir criterios de decision: setup local, managed, Python driver,
  operaciones, query language, index rebuild, licenciamiento, madurez,
  observability, costo y facilidad de tests.
- Definir `GraphStore` como contrato routeable, no como dependencia concreta.
- Mantener `graph_store=disabled` por default.
- Preservar Postgres como fuente durable y graph DB como indice derivado.
- Registrar readiness/backfill de la proyeccion graph en Postgres para que un
  proyecto pueda habilitar Neo4j despues de haber operado sin graph store.
- Requerir fakes deterministas para tests sin Neo4j live.
- Requerir gates de retrieval/evals antes de promover retrieval graph.

## No objetivos

- No agregar dependencia `graphdatascience` en M18.
- No agregar Docker Compose, Neo4j Desktop config ni Aura secrets.
- No agregar indexer ni reindex job antes de cerrar adapter/health.
- No cambiar dense retrieval, rerank, chat, streaming, history ni observability.
- No cambiar defaults de retrieval ni activar graph retrieval en v1 sin evals.
- No guardar datos primarios solo en graph DB.
- No agregar settings para Memgraph, FalkorDB ni Kuzu en M18.

## Alternativas a comparar

### Neo4j

Fortalezas esperadas:

- Ecosistema maduro y drivers oficiales.
- Ruta local y ruta managed Aura.
- Cypher ampliamente documentado.
- Buen encaje para graph traversal y relaciones explicitas.

Riesgos:

- Segundo servicio operativo.
- Setup y credenciales managed/local.
- Drift de indice derivado si no hay reindex idempotente.
- Costo/latencia adicionales si se usa en retrieval online.

### Memgraph

Fortalezas esperadas:

- Compatible con Cypher en varios casos.
- Enfoque operacional local viable.

Riesgos:

- Compatibilidad y managed story deben verificarse frente al caso de uso.
- Menor alineacion con docs Neo4j/Aura.

### FalkorDB

Fortalezas esperadas:

- Opcion ligera basada en Redis/graph.

Riesgos:

- Contrato, drivers, query semantics y deployment deben compararse con cuidado.

### Kuzu

Fortalezas esperadas:

- Embeddable y local-first, potencialmente mas simple para demos.

Riesgos:

- No resuelve igual una ruta managed/externa.
- Puede no encajar si se necesita graph DB routeable como servicio.

### No-op / postergar graph DB

Fortalezas esperadas:

- Cero complejidad operacional adicional.
- Mantiene foco en dense/rerank/evals.

Riesgos:

- Puede limitar exploracion de relaciones estructurales si hay gaps medidos.

## Contrato recomendado

### Settings futuros

```text
graph_store=disabled
graph_store=neo4j
```

`disabled` debe ser el default. `neo4j` debe ser opt-in y fallar con errores
estables si faltan URI, usuario/password o conectividad.

### GraphStore futuro

El contrato debe cubrir al menos:

- `health_check()` o equivalente para conectividad.
- estado de proyeccion por proyecto: `disabled`, `pending_backfill`,
  `indexing`, `ready`, `stale` y `failed`.
- `upsert_project_graph(...)` o materializacion idempotente.
- `delete_project_graph(...)` o limpieza por proyecto.
- `backfill_project_graph(...)` o job equivalente para reconstruir Neo4j desde
  Postgres cuando se habilita despues de estar disabled.
- consultas de retrieval graph en modo opt-in.
- errores estables para unavailable, misconfigured y query failure.

### Data ownership

Postgres sigue siendo fuente durable. Graph DB solo contiene nodos/relaciones
derivados de proyectos, sources, documents, document versions, chunks y metadata.
El indice graph debe poder reconstruirse desde Postgres.

Postgres tambien debe conservar el estado operativo de la proyeccion graph por
proyecto: backend, status, watermark/source version, schema/extractor version,
`last_indexed_at` y error code estable. Mientras graph store este disabled, la
ingestion no debe intentar escribir en Neo4j. Al habilitar `graph_store=neo4j`,
el proyecto entra en `pending_backfill`/`indexing` hasta que un backfill
idempotente materialice la proyeccion y la marque `ready`.

No hace falta duplicar todos los nodos/aristas en Postgres si se derivan
deterministicamente de tablas canonicas. Si un slice posterior agrega extraccion
costosa de entidades o relaciones, esos graph facts deben persistirse en
Postgres con version/hash para que Neo4j pueda reconstruirse sin repetir trabajo
externo o no determinista.

### Retrieval contract

Retrieval graph debe preservar:

- aislamiento por proyecto;
- metadata filters;
- citations;
- audit trail de retrieval;
- fallback claro a dense retrieval cuando graph store este disabled o
  unavailable, o cuando la proyeccion del proyecto no este `ready`;
- no cambiar defaults hasta pasar evals versionadas.

## Secuencia recomendada de M18

### 1. `m18-neo4j-graph-db-decision`

Alcance:

- Crear el change OpenSpec M18.
- Documentar decision, alternativas, riesgos y secuencia.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo backend/frontend.
- Dependencias Neo4j.

### 2. `m18-graph-db-decision-matrix`

Estado: completo.

Alcance:

- Completar decision matrix con evidencia verificable.
- Decidir proceed/no-go para Neo4j como primera ruta graph DB.
- Confirmar local setup, managed setup, driver, licenciamiento y testability.

Fuera de alcance:

- Adapter live e indexer.

Resultado:

- Neo4j queda seleccionado como primer backend live opt-in.
- `m18-graph-store-contract` debe definir solo `disabled` y `neo4j` como
  backends iniciales.
- Memgraph y FalkorDB quedan como alternativas de contingencia.
- Kuzu queda fuera del backend routeable de M18 porque no cubre la ruta managed
  equivalente.

### 3. `m18-graph-store-contract`

Estado: completo.

Alcance:

- Definir contrato `GraphStore`, settings, errores estables y fakes offline.
- Definir readiness/backfill por proyecto en Postgres antes del adapter live.
- Mantener `graph_store=disabled` default.
- Agregar tests unitarios sin servicio live.

Resultado:

- Agrega `graph_store=disabled|neo4j` y credenciales Neo4j opcionales en
  settings sin construir clientes live.
- Agrega contrato `GraphStore`, `DisabledGraphStore`, `FakeGraphStore`, health
  check, resultado de backfill, errores estables y helper de fallback dense.
- Agrega tabla/modelo/repository `graph_projections` para readiness/backfill por
  proyecto con estados `disabled`, `pending_backfill`, `indexing`, `ready`,
  `stale` y `failed`.

Fuera de alcance:

- Conectividad Neo4j live.

### 4. `m18-neo4j-adapter-and-health`

Estado: completo.

Alcance:

- Agregar adapter Neo4j opt-in.
- Validar `GraphDatabase.driver(...)`, auth y `verify_connectivity()` en health
  checks.
- Documentar local Docker/Desktop y Aura `neo4j+s://...`.

Resultado:

- Agrega dependencia runtime `neo4j>=6.0` resuelta en lockfile como
  `neo4j==6.2.0`.
- Agrega `Neo4jGraphStore` y factory `get_graph_store(...)` con
  `graph_store=disabled` como default y `graph_store=neo4j` opt-in.
- El factory valida URI, username y password desde settings, crea el driver con
  `GraphDatabase.driver(uri, auth=(username, password))` y no ejecuta
  conectividad hasta `health_check()`.
- `health_check()` llama `verify_connectivity()` y mapea `AuthError`,
  `ServiceUnavailable`, `DriverError`, `Neo4jError` y errores desconocidos a
  `GraphStoreHealth` con error codes estables sin exponer secretos.
- `backfill_project_graph(...)` y `delete_project_graph(...)` quedan
  explicitamente fuera de alcance y fallan con `GraphStoreQueryError` hasta el
  slice de indexer.

Fuera de alcance:

- Indexer, reindex jobs, route de retrieval graph y cambios de defaults.

### 5. `m18-neo4j-indexer`

Estado: completo.

Alcance:

- Materializar grafo derivado desde Postgres.
- Reindex idempotente por proyecto.
- Preservar aislamiento y metadata.

Resultado:

- Agrega `Neo4jProjectGraph` y `load_project_graph(session, project_id)` para
  construir un payload determinista desde Project, Source, Document,
  DocumentVersion y Chunk.
- Serializa metadata JSON como strings estables para propiedades Neo4j y
  conserva anchors de citations por version/chunk/offset sin copiar embeddings
  ni `normalized_text` completo.
- `Neo4jGraphStore.backfill_project_graph(...)` elimina el scope
  `AdaptiveRagGraph` del proyecto y luego ejecuta `MERGE` de nodos y relaciones
  project/source/document/version/chunk.
- `delete_project_graph(...)` queda implementado como borrado scoped por
  `project_id`.
- `get_graph_store(...)` inyecta el loader Postgres por default para runtime
  Neo4j, con loader inyectable en tests.

Fuera de alcance:

- Worker/CLI de reindex, retrieval graph online y cambios de default.

### 6. `m18-graph-retrieval-route`

Estado: completo.

Alcance:

- Agregar ruta retrieval graph opt-in.
- Fallback a dense retrieval.
- Audit trail de estrategia graph.

Resultado:

- Agrega `strategy=dense|graph` en la request compartida de retrieval, API y
  CLI, manteniendo `dense` como default.
- La ruta graph sigue ejecutando dense retrieval primero para obtener seeds y
  solo consulta graph DB cuando existe `GraphRetriever` y la proyeccion del
  proyecto esta `ready`.
- `Neo4jGraphStore.expand_project_chunks(...)` expande chunks seed con
  `NEXT_CHUNK*0..1` dentro del `project_id` y devuelve hits para rehidratar
  citations desde Postgres.
- El fallback devuelve resultados dense con `fallback_reason` estable cuando no
  hay retriever, la proyeccion no esta ready o graph store falla con errores
  estables.
- Los payloads de retrieval exponen `strategy` y, cuando aplica,
  `fallback_reason`; chat audit resume estrategia y razon de fallback en el
  `ToolCall`.

Fuera de alcance:

- Promover default sin evals.

### 7. `m18-evals-quality-gate`

Alcance:

- Comparar dense baseline vs graph-enabled retrieval en suites versionadas.
- Evaluar calidad, costo, latencia, filtros y citations.
- Archivar M18 si el milestone queda cerrado.

## Riesgos y mitigaciones

- Riesgo: agregar Neo4j antes de justificar valor.
  Mitigacion: M18 empieza por decision matrix y eval gates.
- Riesgo: duplicar fuente de verdad.
  Mitigacion: Postgres es durable; graph DB es indice derivado.
- Riesgo: tests dependan de servicio live.
  Mitigacion: contrato y fakes offline antes de adapter.
- Riesgo: defaults cambien sin evidencia.
  Mitigacion: `graph_store=disabled` y retrieval graph opt-in.
- Riesgo: Aura/local diverjan.
  Mitigacion: documentar ambos setups y health checks con errores estables.

## Validacion esperada por slice

Planificacion:

```text
pnpm dlx @fission-ai/openspec validate m18-neo4j-graph-db-decision --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

Implementacion posterior:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
```

Si un slice posterior toca frontend, tambien debe validar:

```text
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```
