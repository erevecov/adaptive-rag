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
productiva como ruta por defecto, modo agente con LangGraph ni learned sparse
retrieval. Esas son fases posteriores deliberadas.

El stack por defecto de v1 no dependerá de Redis, Celery, ARQ, Neo4j,
OpenSearch, Langfuse, Qdrant ni ningún servicio externo obligatorio de base de
datos más allá de Postgres con pgvector. Los profiles opcionales de Docker
Compose pueden agregar servicios self-hosted como Qdrant o Unstructured para
experimentos explícitos.

## Principios principales

- Usar OpenSpec para cambios de comportamiento y arquitectura.
- Usar TDD para el comportamiento core de RAG y los límites de providers.
- Mantener infraestructura mínima y local-first.
- Preferir aislamiento explícito por proyecto sobre estado global oculto.
- Usar LlamaIndex como toolkit RAG principal, pero mantener la orquestación de
  producto en código propio de Adaptive RAG.
- Medir cambios de retrieval con evals, no con intuición.
- Mantener los providers reemplazables mediante interfaces pequeñas por
  capability.

## Stack tecnológico

- Backend API: FastAPI
- CLI: Typer y Rich
- Runtime: Python
- Base de datos: Postgres con pgvector
- Vector store por defecto: pgvector
- Profile opcional de vector store: Qdrant self-hosted
- ORM y migraciones: SQLAlchemy 2 y Alembic
- Toolkit RAG: LlamaIndex
- Parsing avanzado opcional de documentos: Unstructured OSS/local, con API
  hosted de Unstructured disponible solo cuando se configure explícitamente
- Framework de evals: Ragas más métricas determinísticas propias
- Tests: pytest
- Packaging y workflow local: uv
- Deployment: Docker Compose con API, worker y Postgres/pgvector por defecto;
  profiles opcionales pueden agregar Qdrant o Unstructured

## Providers de IA

La integración de providers se basa en capabilities. El core RAG no debe
depender directamente de SDKs de vendors.

Providers hosted por defecto:

- Chat por defecto: DeepSeek directo, `deepseek-v4-flash`
- Opción de chat más fuerte: DeepSeek directo, `deepseek-v4-pro`
- Embeddings por defecto: Voyage, `voyage-4-lite`, 1024 dimensiones
- Rerank por defecto: Voyage, `rerank-2.5-lite`
- Opción de rerank de mayor calidad: Voyage, `rerank-2.5`

Providers locales opcionales:

- Chat: Ollama o servidor local OpenAI-compatible
- Embeddings: servidor local de embeddings o futuro provider TEI-compatible
- Rerank: BGE reranker local, partiendo con `BAAI/bge-reranker-v2-m3`

Las interfaces iniciales de providers son:

- `ChatProvider`
- `EmbeddingProvider`
- `Reranker`
- `Contextualizer`

Cada proyecto almacena configuración de provider para chat, embeddings, rerank
y contextualización en tiempo de indexing.

## Límite de storage

Postgres siempre es la source of truth para datos de proyecto, ciclo de vida de
fuentes, documentos, chunks, jobs, historial de chat, evals, audit trail, usage
y costos. El vector store es reemplazable detrás de una pequeña interfaz
`VectorStore`.

Adaptadores iniciales de vector store:

- `PgVectorStoreAdapter`: adaptador por defecto de v1. Guarda embeddings en
  Postgres con pgvector y mantiene el stack local por defecto en un solo
  servicio de base de datos.
- `QdrantVectorStoreAdapter`: profile opcional self-hosted con Docker para
  aprender, benchmarkear y experimentar con filtering/search específicos de
  vector databases.

Cuando Qdrant está habilitado, Postgres sigue almacenando las filas canónicas de
chunks y metadata. Postgres también puede conservar el embedding del chunk para
portabilidad y fallback, mientras Qdrant actúa como índice activo de
vector-search. Qdrant almacena payloads de vector-search:

- `point_id`: `chunk_id`
- `vector`: embedding
- `payload.project_id`
- `payload.source_id`
- `payload.document_id`
- `payload.text_hash`
- metadata filtrable seleccionada

El código de retrieval depende de `VectorStore`, no directamente de pgvector ni
de Qdrant. Qdrant no debe ser necesario para ejecutar la ruta de producto por
defecto de v1.

## Límite con LlamaIndex

LlamaIndex es el toolkit principal para primitivas RAG:

- readers y loaders para URLs, Markdown y TXT
- conversión de elementos opcionales de Unstructured a documentos/nodes de
  LlamaIndex
- abstracciones `Document` y `Node` cuando sean útiles
- node parsing y chunking
- manejo de metadata durante ingestion
- integraciones de embeddings y vector stores cuando encajen con el schema
- baselines de BM25 o lexical retrieval cuando sean útiles para evals
- integraciones de reranking cuando sigan siendo transparentes
- integraciones opcionales de evaluación RAG

Adaptive RAG es dueño de la capa de producto:

- modelos de dominio como Project, Source, Document, Chunk, Job, EvalRun y
  ChatSession
- aislamiento por proyecto
- contratos de API y CLI
- registry de providers
- loop de tool calling con DeepSeek
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
- `ordinal`
- `text`
- `text_hash`
- `contextual_text`
- `embedding_input_text`
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
y seguros.

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
6. El paso de contextual chunking agrega un contexto corto por chunk.
7. Voyage crea embeddings para el input contextualizado de embedding.
8. Chunks, embeddings, metadata y status se guardan en Postgres.
9. La fuente y el job terminan como `indexed`/`succeeded` o `failed`.

El worker es idempotente por hash de contenido de la fuente, configuración de
parser, configuración de chunker, configuración de contextualizer, modelo de
embedding y hash del texto del chunk. Estos inputs se combinan en un
`index_fingerprint`.

Los cambios de parser son forward-only por defecto. Cambiar un proyecto de
`LlamaIndexBasicParser` a `UnstructuredLocalParser` afecta solo nuevas
ingestions, salvo que el usuario inicie explícitamente un reindex job. Los
chunks existentes siguen siendo válidos y buscables porque cada documento y
chunk guarda la metadata de parser y el `index_fingerprint` que lo produjo.

Modos de reindex soportados:

- `none`: comportamiento forward-only por defecto; no tocar chunks existentes.
- `source`: reprocesar una fuente con la configuración actual de parser/index.
- `project`: reprocesar todas las fuentes de un proyecto con la configuración
  actual de parser/index.

Reindexar una fuente reemplaza o supersede los chunks anteriores de esa fuente
dentro del mismo proyecto. Backfills completos de proyecto son opt-in y deben
usarse solo para homogeneidad, comparaciones de evals o upgrades importantes de
indexing.

## Providers de document parsing

El document parsing está detrás de una pequeña interfaz `DocumentParser`, para
que el pipeline de ingestion soporte parsers simples y avanzados sin cambiar el
modelo de dominio.

Providers iniciales de parser:

- `LlamaIndexBasicParser`: parser por defecto de v1 para URLs, Markdown y TXT.
- `UnstructuredLocalParser`: parser opcional usando la librería open-source
  `unstructured` o una API de Unstructured alojada localmente.
- `UnstructuredApiParser`: adaptador opcional de API hosted, deshabilitado
  salvo que el usuario configure credenciales explícitamente.

Configuración por defecto:

```yaml
parsing:
  provider: llamaindex_basic
```

Configuración avanzada opcional:

```yaml
parsing:
  provider: unstructured_local
  strategy: fast
```

Unstructured es útil para HTML complejo, PDFs, documentos Office, emails y
documentos con muchas imágenes porque particiona archivos crudos en elementos
estructurados como títulos, narrative text y list items con metadata. En v1 es
una capability opcional para aprendizaje y experimentación. Se convierte en
default de producto solo si evals futuras muestran mejor calidad de retrieval y
el costo operacional se justifica.

Cuando se usa Unstructured, Adaptive RAG sigue siendo dueño del ciclo de vida de
fuentes, aislamiento por proyecto, content hashing, citations, contextual
chunking, embeddings y persistencia. Unstructured solo entrega elementos
parseados.

## Chunks contextuales

El contextual chunking está habilitado por defecto para proyectos nuevos.

Para cada chunk, el sistema almacena:

- `text`: texto original del chunk usado para citations y contexto de respuesta
- `contextual_text`: contexto corto generado para retrieval
- `embedding_input_text`: `contextual_text` más `text`

El texto contextual mejora retrieval, pero no se trata como evidencia factual.
Las citations y snippets visibles para el usuario usan el texto original de la
fuente.

Contextualizer por defecto:

- Provider: DeepSeek directo
- Modelo: `deepseek-v4-flash`
- Objetivo máximo de contexto: 120 tokens

El contextualizer es provider-agnostic y más adelante puede usar Anthropic,
providers OpenAI-compatible o modelos locales.

## Retrieval

La tool principal de retrieval en v1 es `search_project_knowledge`.

La estrategia de retrieval por defecto es:

1. Dense retrieval con embeddings Voyage y el adaptador de vector store
   configurado, por defecto pgvector.
2. Lexical retrieval con Postgres full-text para la ruta de producto.
3. Fusión con reciprocal rank fusion.
4. Reranking con Voyage `rerank-2.5-lite`.
5. Retornar chunks rankeados con metadata de fuente y payloads de citation.

La API pública debe llamar a la rama lexical como lexical retrieval, no BM25,
porque la implementación de producto por defecto es Postgres full-text y no
Okapi BM25. Un verdadero BM25 retriever puede usarse mediante LlamaIndex como
baseline de evals y puede convertirse en implementación futura si soporta
retrieval limpio scoped por proyecto y supera al default en evals.

La interfaz de retrieval debe soportar implementaciones futuras:

- dense-only
- lexical-only
- hybrid RRF
- hybrid RRF más rerank
- dense retrieval respaldado por Qdrant
- learned sparse retrieval con
  `opensearch-project/opensearch-neural-sparse-encoding-multilingual-v1`

Learned sparse retrieval queda diferido a fase 2 y debe justificarse con
resultados de eval antes de convertirse en default.

## Chat y tool calling

La experiencia de chat v1 es agentic pero con guardrails.

El flujo de orquestación es:

1. El usuario envía una pregunta a un endpoint de chat de proyecto o comando
   CLI.
2. `ChatOrchestrator` llama a DeepSeek con las tools disponibles.
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

Profiles opcionales de Docker Compose pueden agregar:

- `qdrant` para benchmark de vector stores y dense retrieval opcional.
- un servicio de Unstructured API para document parsing avanzado.

El stack local por defecto debe correr sin Qdrant ni Unstructured.

El schema incluye `users` y `projects.owner_user_id` para auth multi-user
futura, pero v1 no implementa registro, login, sesiones ni OAuth.

## Estrategia de testing

La cobertura TDD empieza con comportamiento core:

- aislamiento por proyecto
- creación de sources y content hashing
- claim de ingestion jobs con `FOR UPDATE SKIP LOCKED`
- creación de chunks y preservación de metadata
- comportamiento de storage para contextual chunks
- tracking de metadata de embeddings
- comportamiento del provider registry con fakes
- comportamiento del document parser registry con fakes
- contract tests de Unstructured parser con archivos fixture representativos
- contract tests de vector store adapter compartidos por pgvector y Qdrant
- filtros de retrieval por proyecto
- fusión RRF
- generación de citation payload
- orquestación de tool calls con providers fake
- cálculo de métricas de eval

Las llamadas a SDKs de providers usan fakes y contract tests primero. Los smoke
tests con providers hosted son explícitos, opt-in y se saltan cuando faltan API
keys.

## Fases posteriores

Candidatos para fase 2:

- promover Qdrant desde profile opcional de vector store a default si los
  benchmarks contra pgvector lo justifican en latencia, filtros, costo
  operacional y calidad de retrieval
- BM25 real u OpenSearch lexical retrieval si los evals justifican el servicio
  adicional
- learned sparse retrieval con
  `opensearch-project/opensearch-neural-sparse-encoding-multilingual-v1`
- modo agente experimental con LangGraph
- ingestion de PDF
- frontend construido con un agente contra contratos de API estables
- profiles de modelos locales para chat, embeddings y rerank
- export a OpenTelemetry o Langfuse
- auth multi-user
