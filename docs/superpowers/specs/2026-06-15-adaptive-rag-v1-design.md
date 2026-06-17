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
- Usar Pydantic AI como runtime del agente conversacional y tool calling, sin
  convertirlo en provider de IA ni en dueño del retrieval.
- Versionar prompts como artefactos del repositorio, no como strings anónimos
  pegados en el código.
- Medir y limitar usage/costos de providers desde el primer provider call.
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
- Runtime de agente y tool calling: Pydantic AI slim con soporte
  OpenAI-compatible
- Extracción HTML para URLs: Trafilatura
- Parsing de documentos v1: Trafilatura para URLs HTML; readers y node parsers
  de LlamaIndex para Markdown, TXT y texto ya extraído
- Framework de evals: Ragas más métricas determinísticas propias
- Prompts: archivos Markdown versionados en `prompts/`
- Tests: pytest
- Tests de integración con servicios reales: Testcontainers for Python
- Job queue v1: Postgres con `FOR UPDATE SKIP LOCKED`
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

Pydantic AI se usa como runtime de agente, no como provider de IA. La
integración de chat usa Qwen mediante una API OpenAI-compatible configurada con
`base_url` y API key de Qwen. Esto no agrega costos propios, servicios hosted ni
containers; solo agrega una dependencia Python para manejar tool calling,
dependencias tipadas y outputs estructurados.

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

## Budgets, rate limits y cost tracking

La v1 debe tratar las llamadas a Qwen como operaciones con costo y capacidad
limitada. Todo provider call pasa por una capa interna antes de tocar la API:

- `BudgetGuard`: valida límites del proyecto y de la operación antes de llamar
  al provider.
- `ProviderUsageTracker`: registra el uso real o estimado después de cada
  llamada.
- `ModelPriceCatalog`: resuelve precios versionados por provider, modelo,
  región y fecha efectiva.

Operaciones medidas:

- `chat`
- `contextualize`
- `embedding`
- `rerank`
- `eval_judge`

Límites configurables por proyecto:

- `daily_cost_limit`
- `monthly_cost_limit`
- `max_provider_requests_per_minute`
- `max_provider_tokens_per_minute`
- `max_tokens_per_request`
- `max_concurrent_ingestion_provider_calls`
- `evals_enabled`

Los límites son locales y defensivos. No reemplazan los rate limits del provider
hosted, pero evitan gastar de más o saturar Qwen por error de producto,
ingestion masiva o evals demasiado grandes. Si una operación supera un hard
limit, falla antes del provider call y registra el bloqueo. Si supera un soft
limit configurable, puede registrar warning sin bloquear.

El costo guardado por Adaptive RAG es estimado. La factura real sigue siendo la
del provider. Los precios no se hardcodean en lógica de negocio; se guardan como
snapshots versionados para poder reproducir costos históricos aunque Qwen cambie
precios o modelos.

El flujo esperado de una llamada a provider es:

1. Construir `ProviderCallPlan` con proyecto, operación, modelo, tokens
   estimados cuando existan y metadata no sensible.
2. `BudgetGuard` valida presupuesto, rate limits locales y tamaño máximo de
   request.
3. El provider adapter ejecuta la llamada a Qwen.
4. `ProviderUsageTracker` registra tokens reales devueltos por Qwen cuando estén
   disponibles, latencia, status, error y costo estimado con el price snapshot
   vigente.
5. Si el provider no entrega usage, se registra `usage_source = estimated` y el
   cálculo se corrige solo con datos futuros si existe evidencia confiable.

Defaults v1 conservadores:

- evals LLM-as-judge desactivados hasta habilitación explícita por proyecto
- concurrencia baja para contextualización durante ingestion
- rerank limitado a un top-N acotado
- batch size de embeddings limitado
- errores de rate limit hosted no cambian automáticamente de modelo porque v1
  mantiene un solo provider/modelo configurado por capability

Esta capa debe estar en el borde de providers, no dentro de handlers FastAPI ni
del worker. Así chat, ingestion, rerank y evals comparten la misma política.

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

## Estrategia de índices pgvector

La v1 usa pgvector con búsqueda exacta como baseline inicial de correctness. Las
consultas ordenan por distancia vectorial sobre `chunks.embedding vector(1024)`
después de aplicar filtros tipados como `project_id`, `source_id`, `document_id`,
`source_type`, `tags` y rangos de fecha.

No se crea índice HNSW por defecto en las primeras migraciones. Exact search es
más simple de razonar, facilita tests determinísticos y evita confundir errores
de calidad del RAG con recall aproximado del índice mientras el volumen es bajo.

HNSW queda preparado como optimización posterior dentro de pgvector, no como
cambio de arquitectura ni migración a otro vector database. Solo se habilita si
hay evidencia de volumen o latencia:

- latencia de dense retrieval inaceptable con datos reales
- evals que comparen recall@k exacto versus HNSW
- pruebas de metadata filtering que demuestren que `project_id` y filtros
  opcionales siguen devolviendo suficientes candidatos
- configuración explícita de parámetros como `m`, `ef_construction`,
  `ef_search` e `iterative_scan` cuando aplique

El baseline de evals y contract tests siempre debe poder correr con exact
search, incluso si un deployment productivo activa HNSW.

## Límite con LlamaIndex

LlamaIndex es el toolkit principal para primitivas RAG:

- readers y loaders para Markdown y TXT
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
- orquestación de chat con Pydantic AI y Qwen
- contratos de tools
- citations y audit trail
- persistencia de eval runs y métricas determinísticas

Este límite mantiene a LlamaIndex valioso para aprendizaje y señal de CV sin
convertir el proyecto en un wrapper opaco de framework.

## Límite con Trafilatura

Trafilatura se adopta en v1 como extractor HTML por defecto para fuentes URL.
Su trabajo es convertir HTML público en texto principal y metadata útil antes
del chunking. Esto mejora la calidad de ingestion al reducir navegación,
footers, sidebars, banners y texto boilerplate que degradaría embeddings,
Postgres full-text y citations.

Uso esperado:

- `httpx` descarga la URL con timeouts, headers, límites de tamaño y manejo de
  errores propio de Adaptive RAG.
- Trafilatura recibe el HTML descargado y extrae texto principal más metadata
  como título, autor, fecha y URL canónica cuando estén disponibles.
- El texto limpio se convierte a documentos internos para chunking semántico y
  Contextual Retrieval.
- Markdown y TXT no pasan por Trafilatura.

Trafilatura no se usa en v1 como crawler general, scheduler de scraping,
browser automation, renderer JavaScript ni fuente de verdad de URLs. La fuente
de verdad sigue siendo Postgres y la orquestación de ingestion sigue viviendo en
Adaptive RAG.

## Límite con Pydantic AI

Pydantic AI se adopta en v1 para implementar la experiencia agentic de chat:

- tool calling
- dependencias tipadas por request, como `project_id`, configuración del
  proyecto, repositorios y retriever
- structured outputs para respuestas con citations
- integración con Qwen a través de un cliente OpenAI-compatible

La dependencia instalada debe ser `pydantic-ai-slim[openai]`, no el paquete
completo `pydantic-ai`, para evitar SDKs de providers que no usaremos. El extra
`openai` se usa solo porque Qwen expone una superficie compatible; el provider
real de IA sigue siendo Qwen.

Pydantic AI no es dueño de:

- ingestion
- parsing
- chunking
- embeddings
- Postgres full-text
- pgvector
- RRF
- reranking
- evals
- persistencia de chat, tool calls, retrieval runs o usage

Adaptive RAG debe envolverlo detrás de una interfaz propia, por ejemplo
`ChatAgentRuntime`, para mantener aisladas las decisiones de framework. Si en el
futuro Pydantic AI no encaja, el dominio, retrieval, storage y contratos de API
deben poder sobrevivir sin una reescritura completa.

## Prompt versioning

Los prompts son parte del comportamiento del sistema y se versionan como
artefactos del repositorio. No deben vivir como strings largos sin nombre dentro
de handlers, providers o tests.

Convención v1:

- Directorio: `prompts/`
- Formato: Markdown.
- Identificador de versión: nombre del archivo sin extensión, por ejemplo
  `answer_with_citations_v1`.
- Los prompts que ya fueron usados para datos persistidos no se editan en
  caliente. Un cambio semántico crea un archivo nuevo, por ejemplo
  `answer_with_citations_v2.md`.

Prompts previstos para v1:

- `contextual_chunk_v1.md`: genera `contextual_text` para Contextual Retrieval.
- `answer_with_citations_v1.md`: responde usando chunks recuperados y citations.
- `tool_selection_v1.md`: guía cuándo usar `search_project_knowledge`.
- `eval_judge_v1.md`: guía evaluaciones LLM-as-judge cuando Ragas use Qwen.

Persistencia esperada:

- Chunks contextualizados guardan la versión del prompt de contextualización.
- Sesiones de chat guardan la versión del prompt principal de respuesta.
- Eval runs guardan un mapa de versiones de prompts usados durante el run.

Los cambios de prompts se tratan como cambios medibles. Antes de promover un
prompt nuevo como default, se comparan al menos con evals determinísticos,
métricas Ragas relevantes, costo y latencia.

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
- `budget_config_json`
- `created_at`

`model_price_snapshots`:

- `id`
- `provider`, por ejemplo `qwen`
- `model`
- `region`
- `operation`, por ejemplo `chat`, `embedding`, `rerank` o `eval_judge`
- `input_price_per_million_tokens`
- `output_price_per_million_tokens`, nullable para operaciones sin output
- `request_price`, nullable para modelos cobrados por request
- `currency`
- `effective_from`
- `effective_to`, nullable
- `metadata_json`
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
- `section_path`
- `heading`
- `char_start`
- `char_end`
- `token_count`
- `prev_chunk_id`
- `next_chunk_id`
- `contextual_text`
- `embedding_input_text`
- `lexical_input_text`
- `contextualized`
- `contextualizer_provider`
- `contextualizer_model`
- `contextualizer_version`
- `contextualizer_prompt_version`
- `parser_provider`
- `parser_version`
- `parser_config_hash`
- `chunker_version`
- `chunker_config_hash`
- `index_fingerprint`
- `embedding`, `vector(1024)`
- `embedding_provider`
- `embedding_model`
- `embedding_dim`
- `metadata_json`
- `created_at`

`jobs`:

- `id`
- `project_id`
- `queue_name`, default `default`
- `job_type`, uno de `ingest_source`, `reindex_source`, `reindex_project` o
  `eval_run`
- `status`, uno de `queued`, `running`, `blocked`, `succeeded`, `failed`,
  `dead_letter` o `cancelled`
- `priority`
- `run_after`
- `attempts`
- `max_attempts`
- `locked_by`
- `locked_at`
- `heartbeat_at`
- `lease_expires_at`
- `idempotency_key`
- `source_id`, nullable
- `document_id`, nullable
- `eval_run_id`, nullable
- `payload_json`
- `result_json`
- `last_error_code`
- `last_error_message`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

`job_events`:

- `id`
- `job_id`
- `event_type`
- `from_status`
- `to_status`
- `message`
- `metadata_json`
- `created_at`

El aislamiento por proyecto debe aplicarse con filtros directos de `project_id`
en todas las lecturas y escrituras scoped a proyecto. `chunks.project_id` está
desnormalizado intencionalmente para que los filtros de retrieval sean simples
y seguros. `chunks.source_type` y `chunks.tags` también se desnormalizan para
que dense retrieval y lexical retrieval apliquen los mismos filtros sin depender
de joins complejos en la ruta caliente.

## Cola de jobs en Postgres

La v1 usa Postgres como job queue. No se agrega Redis, Celery, ARQ, Temporal ni
otro broker. La tabla `jobs` es genérica aunque el primer uso productivo sea
ingestion. Esto evita duplicar lógica cuando aparezcan reindex, evals u otras
operaciones async.

Endpoints semánticos como `POST /projects/{project_id}/ingestion-jobs` pueden
seguir existiendo en la API, pero por debajo crean un job `job_type =
ingest_source`. El CLI `adaptive-rag jobs run-worker` consume la tabla genérica.

Estados:

- `queued`: listo para ejecutarse cuando `run_after <= now()`.
- `running`: reclamado por un worker con lease vigente.
- `blocked`: no debe reintentarse automáticamente porque falta una condición
  externa, por ejemplo API key, presupuesto, proyecto pausado o configuración
  inválida.
- `succeeded`: terminó correctamente.
- `failed`: error final no retryable.
- `dead_letter`: agotó `max_attempts`.
- `cancelled`: cancelado explícitamente por usuario o sistema.

Claim de jobs:

```sql
UPDATE jobs
SET status = 'running',
    locked_by = :worker_id,
    locked_at = now(),
    heartbeat_at = now(),
    lease_expires_at = now() + :lease_duration,
    attempts = attempts + 1,
    started_at = coalesce(started_at, now()),
    updated_at = now()
WHERE id = (
  SELECT id
  FROM jobs
  WHERE status = 'queued'
    AND queue_name = :queue_name
    AND run_after <= now()
  ORDER BY priority DESC, run_after ASC, created_at ASC
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
RETURNING *;
```

La transacción de claim debe ser corta: reclamar y hacer commit. El
procesamiento pesado ocurre fuera de esa transacción. Nunca mantener locks de
Postgres mientras se descarga una URL, se parsea contenido o se llama a Qwen.

Retries y backoff:

- Errores transitorios vuelven a `queued` con `run_after` futuro.
- Backoff exponencial con jitter.
- Si `attempts >= max_attempts`, el job pasa a `dead_letter`.
- Errores no retryable pasan a `failed`.
- Faltas externas recuperables pasan a `blocked` sin consumir intentos
  adicionales hasta que el usuario o sistema desbloquee la condición.

Leases:

- Cada job `running` tiene `lease_expires_at`.
- El worker actualiza `heartbeat_at` y extiende el lease mientras trabaja.
- Un sweeper reencola jobs `running` con lease vencido si aún tienen intentos
  disponibles.
- Si un worker recibe shutdown, termina el job actual si puede y deja de
  reclamar nuevos jobs.

Idempotencia:

- Todo job tiene `idempotency_key`.
- Enqueue debe devolver un job activo o ya exitoso si existe el mismo
  `project_id`, `job_type` e `idempotency_key`.
- Ingestion construye la key con `project_id`, `source_id`, `content_hash`,
  `parser_config_hash`, `chunker_config_hash`, configuración de
  contextualizer, modelo de embedding y `index_fingerprint`.
- Un reindex forzado debe cambiar explícitamente la key o el payload para no
  confundirse con una ingestion ya resuelta.
- Los writes del worker también deben ser idempotentes: chunks se reemplazan o
  superseden por `index_fingerprint`, no por suposición de que el job corre una
  sola vez.

Índices mínimos:

- índice para claim por `queue_name`, `status`, `run_after`, `priority` y
  `created_at`
- índice para sweeper por `status` y `lease_expires_at`
- índice por `project_id` y `status` para vistas de proyecto
- índice por `job_type`, `project_id` e `idempotency_key`

La unicidad de idempotencia debe impedir duplicados activos. Para jobs ya
exitosos con la misma key, enqueue puede devolver el job existente como no-op;
un reindex intencional debe usar una key diferente.

Observabilidad:

- Cada transición relevante crea un `job_events`.
- `last_error_code` debe ser estable y testeable; `last_error_message` es para
  diagnóstico humano.
- Los eventos no guardan API keys, texto completo de documentos ni prompts
  completos.

## Pipeline de ingestion

La ruta de producto por defecto de v1 soporta URLs públicas HTML, archivos
Markdown y archivos TXT. Parsers avanzados pueden soportar formatos adicionales
como profiles opt-in, pero esos formatos no son requeridos para la línea base de
v1.

El flujo de ingestion es:

1. La API o CLI crea una Source dentro de un Project.
2. La API o CLI encola un job `ingest_source`.
3. Un worker respaldado por Postgres reclama jobs encolados con
   `FOR UPDATE SKIP LOCKED` a través de la tabla `jobs`.
4. El worker carga el contenido de la fuente. Para URLs HTML descarga con
   `httpx` y extrae texto principal con Trafilatura; para Markdown y TXT usa el
   parser básico del proyecto apoyado en LlamaIndex cuando sea útil.
5. El document parser seleccionado produce unidades de texto estructuradas.
6. El paso de Contextual Retrieval agrega un contexto corto por chunk usando
   Qwen.
7. Qwen crea embeddings para el input contextualizado de embedding.
8. Postgres full-text indexa el input contextualizado para la rama lexical.
9. Chunks, embeddings, metadata y status se guardan en Postgres.
10. La fuente y el job terminan como `indexed`/`succeeded` o `failed`.

El worker de ingestion es idempotente por hash de contenido de la fuente,
configuración de parser, configuración de chunker, configuración de
contextualizer, modelo de embedding y hash del texto del chunk. Estos inputs se
combinan en un `index_fingerprint`.

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

- `TrafilaturaHtmlExtractor`: extractor por defecto para URLs HTML públicas.
- `LlamaIndexBasicParser`: parser por defecto de v1 para Markdown, TXT y texto
  ya extraído desde HTML.

Configuración por defecto:

```yaml
parsing:
  url_html_extractor: trafilatura
  text_parser: llamaindex_basic
```

Unstructured no se instala ni se implementa en v1. Puede mejorar documentos
complejos como PDFs, Office, HTML ruidoso, emails, tablas o documentos con OCR,
pero agrega dependencias pesadas, modos de parsing, latencia, edge cases de
Docker y decisiones de calidad que no son necesarias para el alcance inicial.

El schema mantiene `parser_provider`, `parser_version`, `parser_config_hash` e
`index_fingerprint` para que un parser futuro pueda convivir con datos ya
indexados sin exigir backfill obligatorio.

## Chunking semántico

El chunking v1 debe minimizar cortes erróneos antes de aplicar Contextual
Retrieval. La estrategia es estructura primero y tokens solo como fallback:

1. El parser produce texto normalizado y, cuando sea posible, bloques
   estructurales: headings, párrafos, listas, tablas Markdown y code fences.
2. El chunker agrupa bloques respetando límites semánticos.
3. Si un bloque excede `max_chunk_tokens`, se parte con una regla específica
   para su tipo.
4. Si no hay estructura suficiente, se usa fallback por frases/párrafos.
5. El corte puramente por tokens se usa solo como último recurso.

Reglas de corte:

- No cortar dentro de code fences salvo que el bloque supere `max_chunk_tokens`.
- No cortar dentro de tablas Markdown salvo que la tabla supere
  `max_chunk_tokens`; si se parte, repetir el header de tabla en cada chunk
  derivado.
- No cortar en medio de una lista si el grupo completo cabe dentro de
  `max_chunk_tokens`.
- Preferir cortes por heading, luego párrafo, luego frase, luego tokens.
- Mantener overlap pequeño entre chunks vecinos para conservar continuidad.
- Preservar `section_path` y `heading` para mejorar context generation,
  metadata filtering y citations.

Defaults v1:

```yaml
chunking:
  strategy: semantic_markdown_v1
  target_chunk_tokens: 500
  max_chunk_tokens: 800
  overlap_tokens: 80
```

Cada chunk guarda `char_start`, `char_end`, `token_count`, `prev_chunk_id`,
`next_chunk_id`, `chunker_version` y `chunker_config_hash`. Los offsets se
refieren al texto normalizado del documento, no al texto contextual generado.

Invariantes:

- Reconstruir los chunks por `ordinal` debe preservar el contenido original
  normalizado, ignorando solo el overlap explícito.
- `text` nunca incluye `contextual_text`.
- Citations usan `text`, `char_start`, `char_end`, `section_path` y `heading`.
- Cambios de estrategia o configuración de chunking cambian el
  `index_fingerprint`.

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
2. `ChatOrchestrator` construye un agente Pydantic AI con modelo Qwen
   OpenAI-compatible, dependencias del proyecto y tools disponibles.
3. El modelo puede llamar a `search_project_knowledge` mediante tool calling de
   Pydantic AI.
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

El tool loop vive en una capa propia de Adaptive RAG respaldada por Pydantic AI.
LlamaIndex se usa por debajo para primitivas RAG, no como dueño de la
orquestación del chat.

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
- `prompt_versions_json`
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

- `project_id`
- `session_id`, nullable
- `job_id`, nullable
- `eval_run_id`, nullable
- `operation`, uno de `chat`, `contextualize`, `embedding`, `rerank` o
  `eval_judge`
- `provider`
- `model`
- `provider_request_id`, nullable
- `price_snapshot_id`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `usage_source`, uno de `provider_reported` o `estimated`
- `estimated_cost`
- `currency`
- `latency_ms`
- `status`
- `error_message`
- `created_at`

Adaptadores futuros pueden exportar a OpenTelemetry o Langfuse, pero v1 no
depende de ellos.

## Preparación para OpenTelemetry

La v1 no instala ni inicializa OpenTelemetry todavía. El camino queda preparado
con nombres estables de spans y atributos para que, cuando existan flujos reales
de API, ingestion, retrieval, chat y evals, se pueda agregar instrumentación sin
renombrar conceptos ni cambiar contratos de audit trail.

Spans reservados:

- `api.request`
- `ingestion.source.fetch`
- `ingestion.document.parse`
- `ingestion.chunk.create`
- `ingestion.chunk.contextualize`
- `embedding.create`
- `retrieval.dense.search`
- `retrieval.lexical.search`
- `retrieval.rrf.fuse`
- `rerank.qwen`
- `chat.agent.run`
- `chat.tool.search_project_knowledge`
- `eval.run`

Atributos comunes:

- `adaptive_rag.project_id`
- `adaptive_rag.source_id`
- `adaptive_rag.document_id`
- `adaptive_rag.chunk_id`
- `adaptive_rag.session_id`
- `adaptive_rag.eval_run_id`
- `adaptive_rag.provider`
- `adaptive_rag.model`
- `adaptive_rag.prompt_version`
- `adaptive_rag.retrieval_strategy`

Reglas:

- No registrar contenido sensible, texto completo de chunks, prompts completos,
  API keys ni respuestas completas en spans.
- Usar spans para latencia, errores, conteos y correlación; usar Postgres como
  audit trail durable.
- Mantener logs JSON y tablas de auditoría como observabilidad principal de v1.
- Agregar dependencias `opentelemetry-*` solo cuando implementemos
  instrumentación real o un exporter concreto.

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

Los endpoints de `ingestion-jobs` son una superficie semántica de producto. En
la base de datos crean y leen filas de `jobs` con `job_type = ingest_source`.

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
- claim de jobs con `FOR UPDATE SKIP LOCKED`
- leases, heartbeat y reencolado de jobs `running` expirados
- retries con backoff, `blocked`, `failed` y `dead_letter`
- enqueue idempotente por `idempotency_key`
- `job_events` para transiciones relevantes
- extracción de HTML con Trafilatura usando HTML descargado por el sistema
- creación de chunks y preservación de metadata
- chunking semántico de Markdown con headings, listas, tablas y code fences
- fallback por frases/párrafos/tokens para bloques largos
- reconstrucción de contenido normalizado desde chunks ordenados por `ordinal`
- offsets `char_start`/`char_end` válidos para citations
- comportamiento de storage para contextual chunks
- construcción de `embedding_input_text` y `lexical_input_text`
- tracking de metadata de embeddings
- comportamiento del provider registry con fakes
- `BudgetGuard` bloquea provider calls que superan presupuesto, rate limits
  locales o tamaño máximo de request
- `ProviderUsageTracker` registra usage/costo para chat, contextualización,
  embeddings, rerank y evals con provider fakes
- comportamiento del document parser registry con fakes
- resolución y tracking de versiones de prompts
- contract tests del adapter pgvector
- dense retrieval exacto como baseline de correctness
- pruebas comparativas para HNSW solo si se habilita como optimización
- filtros de retrieval por proyecto
- metadata filtering por `source_id`, `document_id`, `source_type`, `tags` y
  rango de fechas
- paridad de filtros entre dense retrieval y lexical retrieval
- paridad de Contextual Retrieval entre dense retrieval y lexical retrieval
- fusión RRF
- generación de citation payload
- orquestación de tool calls con Pydantic AI usando modelos y tools fake
- cálculo de métricas de eval

Las llamadas a SDKs de providers usan fakes y contract tests primero. Los smoke
tests con providers hosted son explícitos, opt-in y se saltan cuando faltan API
keys.

Los tests de integración contra infraestructura usan Testcontainers for Python
como dependencia de desarrollo. Se usa para levantar Postgres/pgvector efímero
durante pruebas de migraciones, constraints, full-text search, pgvector,
`FOR UPDATE SKIP LOCKED`, leases de jobs y comportamiento real de transacciones.
Testcontainers no forma parte del runtime productivo, no agrega servicios a
Docker Compose y requiere Docker disponible solo en el entorno que ejecute esos
tests.
Los tests deben generar URLs SQLAlchemy usando el driver `psycopg`, coherente
con el stack del proyecto, en vez de introducir `psycopg2`.

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
