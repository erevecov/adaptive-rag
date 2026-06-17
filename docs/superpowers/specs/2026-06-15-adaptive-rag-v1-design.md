# Diseño v1 de Adaptive RAG

Fecha: 2026-06-15
Estado: línea base de diseño aprobada

## Propósito

Adaptive RAG es un proyecto RAG personal, público y con calidad de portafolio.
Está informado por experiencia previa con sistemas RAG en producción, pero es
un proyecto independiente con su propio nombre, alcance, arquitectura,
repositorio y dirección de producto. El objetivo de v1 es construir un sistema
RAG real, configurable y aislado por proyecto, usando herramientas Python
modernas pero probadas.

El producto debe soportar múltiples proyectos en una misma instalación. Cada
proyecto es dueño de sus propias fuentes, documentos, chunks, configuración de
providers, configuración de retrieval, historial de chat, datasets de evals y
audit trail. El sistema v1 es single-user y local-first, pero el schema deja
espacio para auth multi-user en el futuro.

Los specs del repositorio se escriben en español. Se mantienen en inglés los
términos técnicos que sean más precisos o reconocibles, como `retrieval`,
`provider`, `chunk`, `tool calling`, `rerank` o `embedding`.

## Fuera de alcance

La v1 no implementará un frontend completo, OAuth/login, observabilidad SaaS
hosted, graph RAG, retrieval multimodal, ingestion de PDF/Office con calidad
productiva como ruta por defecto, modo agente con LangGraph, Okapi BM25 real,
SPLADE, learned sparse retrieval ni Unstructured como parser integrado. Esas son
decisiones deliberadas para llegar a producción con menos piezas móviles.

El stack por defecto de v1 no dependerá de Redis, Celery, ARQ, Neo4j,
OpenSearch, Langfuse, Qdrant ni ningún servicio externo obligatorio de base de
datos más allá de Postgres con pgvector. Docker Compose v1 no agrega motores de
retrieval ni parsers avanzados.

## Principios principales

- Usar OpenSpec para cambios de comportamiento y arquitectura.
- Usar TDD para el comportamiento core de RAG y los límites de providers.
- Mantener infraestructura mínima y local-first.
- Preferir aislamiento explícito por proyecto sobre estado global oculto.
- Usar LlamaIndex como toolkit RAG principal, pero mantener la orquestación de
  producto en código propio de Adaptive RAG.
- Medir cambios de retrieval con evals, no con intuición.
- Mantener interfaces pequeñas por capability, aunque la v1 implemente solo
  Qwen como provider de IA. No se prometen otros providers antes de producción.

## Stack tecnológico

- Backend API: FastAPI
- CLI: Typer y Rich
- Runtime: Python
- Base de datos: Postgres con pgvector
- Vector store v1: pgvector
- ORM y migraciones: SQLAlchemy 2 y Alembic
- Toolkit RAG: LlamaIndex
- Parsing de documentos v1: readers y node parsers de LlamaIndex para URLs,
  Markdown y TXT
- Framework de evals: Ragas más métricas determinísticas propias
- Tests: pytest
- Packaging y workflow local: uv
- Deployment: Docker Compose con API, worker y Postgres/pgvector

## Provider de IA

La v1 usa Qwen como único provider de IA hasta llegar a producción. Esto reduce
credenciales, costos mentales, documentación, smoke tests y superficie de
fallos. Otros providers, modelos locales no-Qwen o agregadores quedan fuera de
alcance y no se prometen como roadmap; solo podrán evaluarse después de
producción si una necesidad medible lo justifica.

La técnica de Contextual Retrieval de Anthropic se adopta como patrón de
indexing, no como dependencia de provider. Adaptive RAG genera el contexto de
cada chunk con Qwen y no llama a la API de Anthropic en v1.

Modelos Qwen configurados para v1:

- Chat rápido y contextualización: Qwen, `qwen3.5-flash`
- Chat de mayor calidad dentro de Qwen: `qwen3.7-plus`
- Chat fuerte opcional dentro de Qwen: `qwen3.7-max`
- Embeddings: Qwen `text-embedding-v4`, 1024 dimensiones
- Rerank: Qwen `qwen3-rerank`

Después de salir a producción, evaluar la integración de modelos Multimodal
Embeddings de Qwen para mejorar retrieval de documentos con imágenes, tablas u
otros elementos no textuales.

Los nombres exactos de modelos son configuración de deployment, no constantes
de dominio. El código debe permitir cambiar snapshots Qwen sin migrar datos
históricos.

Las interfaces iniciales de capabilities son:

- `ChatProvider`
- `EmbeddingProvider`
- `Reranker`
- `Contextualizer`

Cada proyecto almacena configuración Qwen para chat, embeddings, rerank y
contextualización en tiempo de indexing. Aunque exista una capa de interfaces,
la única implementación v1 es Qwen.

## Límite de storage

Postgres siempre es la source of truth para datos de proyecto, ciclo de vida de
fuentes, documentos, chunks, jobs, historial de chat, evals, audit trail, usage
y costos. En v1, Postgres también es el único motor de retrieval persistente:
guarda embeddings densos con pgvector y mantiene la rama lexical con full-text
search.

Adaptador inicial de vector store:

- `PgVectorStoreAdapter`: adaptador v1. Guarda embeddings Qwen en Postgres con
  pgvector y mantiene el stack local en un solo servicio de base de datos.

El código de retrieval puede conservar una interfaz pequeña `VectorStore` para
evitar acoplamiento innecesario, pero no se implementa Qdrant en v1. Qdrant
queda como posible evaluación post-producción, no como compromiso de roadmap.

## Límite con LlamaIndex

LlamaIndex es el toolkit principal para primitivas RAG:

- readers y loaders para URLs, Markdown y TXT
- abstracciones `Document` y `Node` cuando sean útiles
- node parsing y chunking
- manejo de metadata durante ingestion
- integraciones de embeddings y vector stores cuando encajen con el schema
- baselines de lexical retrieval cuando sean útiles para evals
- integraciones de reranking cuando sigan siendo transparentes
- integraciones opcionales de evaluación RAG

Adaptive RAG es dueño de la capa de producto:

- modelos de dominio como Project, Source, Document, Chunk, Job, EvalRun y
  ChatSession
- aislamiento por proyecto
- contratos de API y CLI
- registry de providers
- loop de tool calling con Qwen
- contratos de tools
- citations y audit trail
- persistencia de eval runs y métricas determinísticas

Este límite mantiene a LlamaIndex valioso para aprendizaje y señal de CV sin
convertir el proyecto en un wrapper opaco de framework.

## Modelo de datos

El schema v1 incluye estas tablas principales.

`users`:

- `id`
- `email`
- `display_name`
- `created_at`

`projects`:

- `id`
- `owner_user_id`, nullable en v1
- `name`
- `slug`
- `description`
- `ai_config_json`
- `created_at`

`sources`:

- `id`
- `project_id`
- `type`, uno de `url` o `file`
- `uri`
- `title`
- `tags`, array de texto para filtros explícitos
- `status`, uno de `pending`, `indexing`, `indexed`, `failed`
- `content_hash`
- `metadata_json`
- `created_at`
- `updated_at`

`documents`:

- `id`
- `project_id`
- `source_id`
- `title`
- `tags`, array de texto heredable desde la fuente o asignable al documento
- `text_hash`
- `parser_provider`
- `parser_version`
- `parser_config_hash`
- `index_fingerprint`
- `metadata_json`
- `created_at`

`chunks`:

- `id`
- `project_id`
- `source_id`
- `document_id`
- `source_type`
- `tags`, array de texto denormalizado para filtros de retrieval
- `ordinal`
- `text`
- `text_hash`
- `contextual_text`
- `embedding_input_text`
- `lexical_input_text`
- `contextualized`
- `contextualizer_provider`
- `contextualizer_model`
- `contextualizer_version`
- `parser_provider`
- `parser_version`
- `parser_config_hash`
- `chunker_version`
- `index_fingerprint`
- `embedding`, `vector(1024)`
- `embedding_provider`
- `embedding_model`
- `embedding_dim`
- `metadata_json`
- `created_at`

`ingestion_jobs`:

- `id`
- `project_id`
- `source_id`
- `status`, uno de `queued`, `running`, `succeeded`, `failed`
- `attempts`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`

El aislamiento por proyecto debe aplicarse con filtros directos de `project_id`
en todas las lecturas y escrituras scoped a proyecto. `chunks.project_id` está
desnormalizado intencionalmente para que los filtros de retrieval sean simples
y seguros. `chunks.source_type` y `chunks.tags` también se desnormalizan para
que dense retrieval y lexical retrieval apliquen los mismos filtros sin depender
de joins complejos en la ruta caliente.

## Pipeline de ingestion

La ruta de producto por defecto de v1 soporta URLs públicas, archivos Markdown y
archivos TXT. Parsers avanzados pueden soportar formatos adicionales como
profiles opt-in, pero esos formatos no son requeridos para la línea base de v1.

El flujo de ingestion es:

1. La API o CLI crea una Source dentro de un Project.
2. La API o CLI encola una fila en `ingestion_jobs`.
3. Un worker respaldado por Postgres reclama jobs encolados con
   `SELECT ... FOR UPDATE SKIP LOCKED`.
4. El worker carga el contenido de la fuente con readers de LlamaIndex.
5. El document parser seleccionado produce unidades de texto estructuradas.
6. El paso de Contextual Retrieval agrega un contexto corto por chunk usando
   Qwen.
7. Qwen crea embeddings para el input contextualizado de embedding.
8. Postgres full-text indexa el input contextualizado para la rama lexical.
9. Chunks, embeddings, metadata y status se guardan en Postgres.
10. La fuente y el job terminan como `indexed`/`succeeded` o `failed`.

El worker es idempotente por hash de contenido de la fuente, configuración de
parser, configuración de chunker, configuración de contextualizer, modelo de
embedding y hash del texto del chunk. Estos inputs se combinan en un
`index_fingerprint`.

Los cambios de parser son forward-only por defecto. Cambiar un proyecto desde
`LlamaIndexBasicParser` a un parser futuro afecta solo nuevas ingestions, salvo
que el usuario inicie explícitamente un reindex job. Los chunks existentes
siguen siendo válidos y buscables porque cada documento y chunk guarda la
metadata de parser y el `index_fingerprint` que lo produjo.

Modos de reindex soportados:

- `none`: comportamiento forward-only por defecto; no tocar chunks existentes.
- `source`: reprocesar una fuente con la configuración actual de parser/index.
- `project`: reprocesar todas las fuentes de un proyecto con la configuración
  actual de parser/index.

Reindexar una fuente reemplaza o supersede los chunks anteriores de esa fuente
dentro del mismo proyecto. Backfills completos de proyecto son opt-in y deben
usarse solo para homogeneidad, comparaciones de evals o upgrades importantes de
indexing.

## Document parsing

El document parsing está detrás de una pequeña interfaz `DocumentParser`, para
que el pipeline de ingestion soporte parsers simples y avanzados sin cambiar el
modelo de dominio.

Parser v1:

- `LlamaIndexBasicParser`: parser por defecto de v1 para URLs, Markdown y TXT.

Configuración por defecto:

```yaml
parsing:
  provider: llamaindex_basic
```

Unstructured no se instala ni se implementa en v1. Puede mejorar documentos
complejos como PDFs, Office, HTML ruidoso, emails, tablas o documentos con OCR,
pero agrega dependencias pesadas, modos de parsing, latencia, edge cases de
Docker y decisiones de calidad que no son necesarias para el alcance inicial.

El schema mantiene `parser_provider`, `parser_version`, `parser_config_hash` e
`index_fingerprint` para que un parser futuro pueda convivir con datos ya
indexados sin exigir backfill obligatorio.

## Contextual Retrieval

El Contextual Retrieval está habilitado por defecto para proyectos nuevos. Esta
técnica está inspirada en el patrón publicado por Anthropic: antes de indexar un
chunk, el sistema usa un LLM para generar una descripción breve que sitúa ese
chunk dentro de su documento completo. En Adaptive RAG, ese LLM es Qwen.

Para cada chunk, el sistema almacena:

- `text`: texto original del chunk usado para citations y contexto de respuesta
- `contextual_text`: contexto corto generado para retrieval
- `embedding_input_text`: `contextual_text` más `text`
- `lexical_input_text`: `contextual_text` más `text`, usado por Postgres
  full-text

El texto contextual mejora dense retrieval y lexical retrieval, pero no se trata
como evidencia factual. Las citations y snippets visibles para el usuario usan
el texto original de la fuente.

Contextualizer por defecto:

- Provider: Qwen
- Modelo: `qwen3.5-flash`
- Objetivo máximo de contexto: 120 tokens

El contextualizer usa la misma integración Qwen que chat para mantener un solo
provider de IA en producción.

La implementación v1 adopta dos variantes del patrón:

- Contextual embeddings: `embedding_input_text` se envía a Qwen
  `text-embedding-v4`.
- Contextual full-text: `lexical_input_text` se indexa con Postgres full-text.

No se implementa Contextual BM25 literal porque v1 no usa Okapi BM25.

## Retrieval

La tool principal de retrieval en v1 es `search_project_knowledge`.

La estrategia de retrieval por defecto es:

1. Dense retrieval con embeddings Qwen `text-embedding-v4` y pgvector.
2. Lexical retrieval local con Postgres full-text search sobre
   `lexical_input_text` (`tsvector`, `tsquery`, GIN y ranking con
   `ts_rank_cd`).
3. Fusión con reciprocal rank fusion.
4. Reranking con Qwen `qwen3-rerank`.
5. Retornar chunks rankeados con metadata de fuente y payloads de citation.

La API pública debe llamar a la segunda rama como lexical retrieval o Postgres
full-text, no BM25, porque la implementación de producto no es Okapi BM25. Esta
rama no usa un provider de IA: es infraestructura local de Postgres para mejorar
recall en nombres propios, rutas de API, errores exactos, siglas y términos
raros.

Okapi BM25 real, SPLADE y otros learned sparse retrievers quedan fuera de v1.
No se implementan ni se prometen como roadmap. Después de producción pueden
evaluarse si las métricas muestran que dense retrieval + Postgres full-text +
Qwen rerank no alcanzan.

La interfaz de retrieval v1 debe soportar:

- dense-only
- lexical-only
- hybrid RRF
- hybrid RRF más rerank

Estas variantes existen para evals y debugging, no para prometer múltiples
motores de search.

## Metadata filtering

Metadata filtering es parte de v1 porque el sistema es multi-project y el
usuario necesita controlar sobre qué subconjunto de conocimiento pregunta. Los
filtros se aplican antes de rankear candidatos y deben comportarse igual en
dense retrieval y lexical retrieval.

El filtro obligatorio de toda operación scoped a proyecto es:

- `project_id`

Filtros opcionales v1:

- `source_ids`
- `document_ids`
- `source_types`, por ejemplo `url` o `file`
- `tags`
- `created_from`
- `created_to`

La API expone estos filtros como un objeto `metadata_filter` en retrieval y
chat. El CLI los expone como flags simples, por ejemplo `--source-id`,
`--document-id`, `--source-type`, `--tag`, `--created-from` y `--created-to`.

En v1 no se implementa un lenguaje arbitrario de filtros sobre `metadata_json`.
`metadata_json` existe para conservar información original de parsers, fuentes y
documentos, pero solo los campos promovidos a columnas tipadas participan en el
filtro de retrieval. Esto mantiene los índices, tests y contratos de API
simples.

Implementación esperada:

- dense retrieval usa `WHERE project_id = :project_id` más los filtros
  opcionales antes de ordenar por distancia vectorial.
- lexical retrieval usa los mismos filtros antes de ordenar por `ts_rank_cd`.
- RRF fusiona listas que ya respetan el mismo filtro.
- Qwen rerank solo recibe candidatos ya filtrados.
- citations deben incluir los filtros aplicados en el audit trail del
  `retrieval_run`.

## Chat y tool calling

La experiencia de chat v1 es agentic pero con guardrails.

El flujo de orquestación es:

1. El usuario envía una pregunta a un endpoint de chat de proyecto o comando
   CLI.
2. `ChatOrchestrator` llama a Qwen con las tools disponibles.
3. El modelo puede llamar a `search_project_knowledge`.
4. La tool ejecuta retrieval determinístico y retorna chunks rankeados con
   citations.
5. El modelo responde usando el contexto recuperado.
6. Tool calls, retrieval runs, citations, mensajes, usage y costos se guardan.

Regla para preguntas factuales de proyecto:

Si un chat está asociado a un proyecto que tiene datos indexados, el assistant
debe llamar a `search_project_knowledge` antes de responder preguntas factuales
sobre ese proyecto. Puede saltarse retrieval para saludos, ayuda de la app,
configuración o preguntas generales no relacionadas con la knowledge base del
proyecto.

Tools futuras planificadas, pero fuera del alcance de implementación de v1:

- `self_knowledge`
- `add_knowledge`
- `add_to_memory`

El tool loop vive en código de Adaptive RAG. LlamaIndex se usa por debajo para
primitivas RAG, no como dueño de la orquestación del chat.

## Citations

Cada chunk recuperado retorna un payload de citation:

- `source_id`
- `source_title`
- `source_uri`
- `document_id`
- `chunk_id`
- `snippet`
- `rank`
- `retrieval_method`
- dense score, cuando exista
- lexical score, cuando exista
- RRF score, cuando exista
- rerank score, cuando exista

Las citations de una respuesta deben apuntar al texto original de la fuente y a
su metadata. Los prefijos contextuales generados no son evidencia visible para
el usuario.

## Eval harness

Los evals son parte de v1 y pueden ejecutarse desde CLI y API sin frontend.

Tablas:

`eval_questions`:

- `id`
- `project_id`
- `question`
- `expected_answer`
- `expected_source_ids`
- `tags`
- `created_at`

`eval_runs`:

- `id`
- `project_id`
- `retrieval_strategy`
- `model_config_json`
- `metrics_json`
- `created_at`

`eval_results`:

- `id`
- `eval_run_id`
- `question_id`
- `retrieved_chunk_ids`
- `answer`
- `citations`
- `metrics_json`

Ragas aporta métricas LLM-as-judge:

- faithfulness
- response relevancy
- context precision
- context recall

Métricas determinísticas propias:

- recall@k
- MRR
- source_hit_rate
- citation_coverage
- costo por run
- latencia por estrategia

La primera matriz de estrategias es:

- dense-only
- lexical-only
- hybrid RRF
- hybrid RRF más rerank
- hybrid RRF más rerank más contextual chunks

El eval harness persiste suficientes datos para reproducir por qué una
estrategia superó a otra.

## Observabilidad y audit trail

La v1 usa observabilidad local-first mediante Postgres y logs JSON
estructurados. No se requiere ningún provider SaaS de observabilidad.

Tablas:

`chat_sessions`:

- `project_id`
- `user_input`
- `final_answer`
- `model_config_json`
- `prompt_version`
- `created_at`

`chat_messages`:

- `session_id`
- `role`
- `content`
- `metadata_json`

`tool_calls`:

- `session_id`
- `tool_name`
- `arguments_json`
- `result_summary_json`
- `status`
- `latency_ms`
- `error_message`

`retrieval_runs`:

- `session_id`
- `query`
- `strategy`
- `top_k`
- `used_rerank`
- `latency_ms`

`retrieved_chunks`:

- `retrieval_run_id`
- `chunk_id`
- `dense_score`
- `lexical_score`
- `rrf_score`
- `rerank_score`
- `rank`
- `citation_json`

`provider_usage`:

- `session_id`
- `provider`
- `model`
- `input_tokens`
- `output_tokens`
- `estimated_cost`
- `latency_ms`

Adaptadores futuros pueden exportar a OpenTelemetry o Langfuse, pero v1 no
depende de ellos.

## Superficie de API

Endpoints FastAPI iniciales:

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/sources`
- `GET /projects/{project_id}/sources`
- `GET /projects/{project_id}/sources/{source_id}`
- `POST /projects/{project_id}/ingestion-jobs`
- `GET /projects/{project_id}/ingestion-jobs/{job_id}`
- `POST /projects/{project_id}/chat`
- `GET /projects/{project_id}/chat-sessions/{session_id}`
- `POST /projects/{project_id}/retrieval/search`
- `POST /projects/{project_id}/eval-runs`
- `GET /projects/{project_id}/eval-runs/{run_id}`

`POST /projects/{project_id}/chat` y
`POST /projects/{project_id}/retrieval/search` aceptan `metadata_filter` con los
campos tipados de v1. El backend rechaza filtros con campos desconocidos en vez
de ignorarlos silenciosamente.

## Superficie de CLI

Comandos Typer iniciales:

- `adaptive-rag projects create`
- `adaptive-rag sources add-url`
- `adaptive-rag sources add-file`
- `adaptive-rag jobs run-worker`
- `adaptive-rag chat ask`
- `adaptive-rag retrieval search`
- `adaptive-rag eval run`

La CLI es una superficie de desarrollo y aprendizaje de primera clase mientras
el frontend queda diferido.

`adaptive-rag chat ask` y `adaptive-rag retrieval search` aceptan flags de
filtro como `--source-id`, `--document-id`, `--source-type`, `--tag`,
`--created-from` y `--created-to`.

## Auth y deployment

La v1 es single-user y local-first.

Auth opcional con API key:

- Si `ADAPTIVE_RAG_API_KEY` está seteada, los endpoints mutables requieren
  `Authorization: Bearer <key>`.
- Si no está seteada, la app corre en modo desarrollo local sin auth.

Servicios de Docker Compose:

- `api`
- `worker`
- `postgres` con pgvector

El stack local de v1 no requiere profiles adicionales para document parsing.

El schema incluye `users` y `projects.owner_user_id` para auth multi-user
futura, pero v1 no implementa registro, login, sesiones ni OAuth.

## Estrategia de testing

La cobertura TDD empieza con comportamiento core:

- aislamiento por proyecto
- creación de sources y content hashing
- claim de ingestion jobs con `FOR UPDATE SKIP LOCKED`
- creación de chunks y preservación de metadata
- comportamiento de storage para contextual chunks
- construcción de `embedding_input_text` y `lexical_input_text`
- tracking de metadata de embeddings
- comportamiento del provider registry con fakes
- comportamiento del document parser registry con fakes
- contract tests del adapter pgvector
- filtros de retrieval por proyecto
- metadata filtering por `source_id`, `document_id`, `source_type`, `tags` y
  rango de fechas
- paridad de filtros entre dense retrieval y lexical retrieval
- paridad de Contextual Retrieval entre dense retrieval y lexical retrieval
- fusión RRF
- generación de citation payload
- orquestación de tool calls con providers fake
- cálculo de métricas de eval

Las llamadas a SDKs de providers usan fakes y contract tests primero. Los smoke
tests con providers hosted son explícitos, opt-in y se saltan cuando faltan API
keys.

## Fases posteriores

Candidatos para después de producción:

- evaluar Okapi BM25 real, SPLADE o learned sparse retrieval solo si los evals
  muestran que Postgres full-text limita el recall o la calidad final
- evaluar Qdrant u otro vector database solo si pgvector limita latencia,
  filtros, costo operacional o calidad de retrieval
- evaluar Unstructured solo si el producto necesita PDF, Office, HTML complejo,
  emails, tablas u OCR; la promoción debe justificarse con parse_success_rate,
  text_coverage, retrieval recall@k, citation_coverage y costo/latencia de
  ingestion
- modo agente experimental con LangGraph
- ingestion de PDF
- frontend construido con un agente contra contratos de API estables
- export a OpenTelemetry o Langfuse
- auth multi-user
