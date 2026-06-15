# Adaptive RAG v1 Design

Date: 2026-06-15
Status: Approved design baseline

## Purpose

Adaptive RAG is a personal, public, portfolio-quality RAG project. It is
informed by prior experience with production RAG systems, but it is an
independent project with its own name, scope, architecture, repository, and
product direction. The v1 goal is to build a real, configurable,
project-scoped RAG system using modern but proven Python tools.

The product must support multiple projects in one installation. Each project
owns its own sources, documents, chunks, provider settings, retrieval
configuration, chat history, eval datasets, and audit trail. The v1 system is
single-user and local-first, but the schema leaves room for future multi-user
auth.

## Non-goals

The v1 will not implement a full frontend, OAuth/login, hosted SaaS
observability, graph RAG, multimodal retrieval, production-grade PDF/Office
ingestion as the default path, LangGraph agent mode, or learned sparse
retrieval. Those are deliberate follow-up phases.

The v1 will not depend on Redis, Celery, ARQ, Neo4j, OpenSearch, Langfuse, or
any required external database service beyond Postgres with pgvector.

## Core Principles

- Use OpenSpec for behavior and architecture changes.
- Use TDD for core RAG behavior and provider boundaries.
- Keep infrastructure minimal and local-first.
- Prefer explicit project isolation over hidden global state.
- Use LlamaIndex as the main RAG toolkit, but keep product orchestration owned
  by Adaptive RAG code.
- Make retrieval changes measurable through evals, not intuition.
- Keep providers replaceable through small capability interfaces.

## Technology Stack

- Backend API: FastAPI
- CLI: Typer and Rich
- Runtime: Python
- Database: Postgres with pgvector
- ORM and migrations: SQLAlchemy 2 and Alembic
- RAG toolkit: LlamaIndex
- Optional advanced document parsing: Unstructured OSS/local, with hosted
  Unstructured API available only when explicitly configured
- Eval framework: Ragas plus custom deterministic metrics
- Tests: pytest
- Package and local workflow: uv
- Deployment: Docker Compose with API, worker, and Postgres/pgvector

## AI Providers

Provider integration is capability-based. The RAG core must not depend directly
on vendor SDKs.

Default hosted providers:

- Chat default: DeepSeek direct, `deepseek-v4-flash`
- Chat stronger option: DeepSeek direct, `deepseek-v4-pro`
- Embeddings default: Voyage, `voyage-4-lite`, 1024 dimensions
- Rerank default: Voyage, `rerank-2.5-lite`
- Rerank quality option: Voyage, `rerank-2.5`

Optional local providers:

- Chat: Ollama or OpenAI-compatible local server
- Embeddings: local embedding server or future TEI-compatible provider
- Rerank: local BGE reranker, starting with `BAAI/bge-reranker-v2-m3`

The initial provider interfaces are:

- `ChatProvider`
- `EmbeddingProvider`
- `Reranker`
- `Contextualizer`

Each project stores provider configuration for chat, embeddings, rerank, and
indexing-time contextualization.

## LlamaIndex Boundary

LlamaIndex is the main toolkit for RAG primitives:

- readers and loaders for URLs, Markdown, and TXT
- conversion of optional Unstructured elements into LlamaIndex documents/nodes
- `Document` and `Node` abstractions where useful
- node parsing and chunking
- metadata handling during ingestion
- embedding and vector store integrations where they fit the schema
- BM25 or lexical retrieval baselines when useful for evals
- reranking integrations when they stay transparent
- optional RAG evaluation integrations

Adaptive RAG owns the product layer:

- domain models such as Project, Source, Document, Chunk, Job, EvalRun, and
  ChatSession
- project isolation
- API and CLI contracts
- provider registry
- DeepSeek tool-calling loop
- tool contracts
- citations and audit trail
- eval run persistence and deterministic metrics

This boundary keeps LlamaIndex valuable for learning and CV signal without
turning the project into an opaque framework wrapper.

## Data Model

The v1 schema includes these main tables.

`users`:

- `id`
- `email`
- `display_name`
- `created_at`

`projects`:

- `id`
- `owner_user_id`, nullable in v1
- `name`
- `slug`
- `description`
- `ai_config_json`
- `created_at`

`sources`:

- `id`
- `project_id`
- `type`, one of `url` or `file`
- `uri`
- `title`
- `status`, one of `pending`, `indexing`, `indexed`, `failed`
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
- `status`, one of `queued`, `running`, `succeeded`, `failed`
- `attempts`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`

Project isolation must be enforced by direct `project_id` filters on all
project-scoped reads and writes. `chunks.project_id` is intentionally
denormalized to make retrieval filters simple and safe.

## Ingestion Pipeline

The default v1 product path supports public URLs, Markdown files, and TXT files.
Advanced parsers may support additional formats as opt-in profiles, but those
formats are not required for the v1 baseline.

The ingestion flow is:

1. API or CLI creates a Source under a Project.
2. API or CLI enqueues an `ingestion_jobs` row.
3. A Postgres-backed worker claims queued jobs with
   `SELECT ... FOR UPDATE SKIP LOCKED`.
4. The worker loads source content with LlamaIndex readers.
5. The selected document parser produces structured text units.
6. The contextual chunking step adds a short per-chunk context.
7. Voyage creates embeddings for the contextualized embedding input.
8. Chunks, embeddings, metadata, and status are stored in Postgres.
9. The source and job finish as `indexed`/`succeeded` or `failed`.

The worker is idempotent by source content hash and chunk text hash. Reindexing
a source replaces or supersedes previous chunks for that source under the same
project.

## Document Parsing Providers

Document parsing is behind a small `DocumentParser` interface so the ingestion
pipeline can support simple and advanced parsers without changing the domain
model.

Initial parser providers:

- `LlamaIndexBasicParser`: default v1 parser for URLs, Markdown, and TXT.
- `UnstructuredLocalParser`: optional parser using the open-source
  `unstructured` library or a locally hosted Unstructured API.
- `UnstructuredApiParser`: optional hosted API adapter, disabled unless the
  user explicitly configures credentials.

Default configuration:

```yaml
parsing:
  provider: llamaindex_basic
```

Optional advanced configuration:

```yaml
parsing:
  provider: unstructured_local
  strategy: fast
```

Unstructured is useful for complex HTML, PDFs, Office documents, emails, and
image-heavy documents because it partitions raw files into structured elements
such as titles, narrative text, and list items with metadata. In v1, it is an
optional capability for learning and experimentation. It becomes a product
default only if future evals show better retrieval quality and the operational
cost is justified.

When Unstructured is used, Adaptive RAG still owns source lifecycle,
project isolation, content hashing, citations, contextual chunking, embeddings,
and persistence. Unstructured only provides parsed elements.

## Contextual Chunks

Contextual chunking is enabled by default for new projects.

For each chunk, the system stores:

- `text`: the original chunk text used for citations and answer context
- `contextual_text`: the generated short context for retrieval
- `embedding_input_text`: `contextual_text` plus `text`

The contextual text improves retrieval, but it is not treated as factual
evidence. Citations and user-facing source snippets use original source text.

Default contextualizer:

- Provider: DeepSeek direct
- Model: `deepseek-v4-flash`
- Maximum context target: 120 tokens

The contextualizer is provider-agnostic and can later use Anthropic, OpenAI-
compatible providers, or local models.

## Retrieval

The main v1 retrieval tool is `search_project_knowledge`.

The default retrieval strategy is:

1. Dense retrieval with Voyage embeddings and pgvector.
2. Lexical retrieval with Postgres full-text for the product path.
3. Fusion with reciprocal rank fusion.
4. Reranking with Voyage `rerank-2.5-lite`.
5. Return ranked chunks with source metadata and citation payloads.

The public API must name the lexical leg as lexical retrieval, not BM25,
because the default product implementation is Postgres full-text rather than
Okapi BM25. A true BM25 retriever can be used through LlamaIndex as an eval
baseline and can become a future implementation if it supports clean
project-scoped retrieval and beats the default in evals.

The retrieval interface must support future implementations:

- dense-only
- lexical-only
- hybrid RRF
- hybrid RRF plus rerank
- learned sparse retrieval with
  `opensearch-project/opensearch-neural-sparse-encoding-multilingual-v1`

Learned sparse retrieval is deferred to phase 2 and must be justified with eval
results before becoming default.

## Chat and Tool Calling

The v1 chat experience is agentic but guarded.

The orchestration flow is:

1. User sends a question to a project chat endpoint or CLI command.
2. `ChatOrchestrator` calls DeepSeek with available tools.
3. The model can call `search_project_knowledge`.
4. The tool executes deterministic retrieval and returns ranked, cited chunks.
5. The model answers using retrieved context.
6. Tool calls, retrieval runs, citations, messages, usage, and costs are stored.

Rule for factual project questions:

If a chat is associated with a project that has indexed data, the assistant
must call `search_project_knowledge` before answering factual questions about
that project. It may skip retrieval for greetings, app help, configuration, or
general questions unrelated to the project knowledge base.

Future tools are planned but out of v1 implementation scope:

- `self_knowledge`
- `add_knowledge`
- `add_to_memory`

The tool loop stays in Adaptive RAG code. LlamaIndex is used underneath for RAG
primitives, not as the owner of chat orchestration.

## Citations

Each retrieved chunk returns a citation payload:

- `source_id`
- `source_title`
- `source_uri`
- `document_id`
- `chunk_id`
- `snippet`
- `rank`
- `retrieval_method`
- dense score, when available
- lexical score, when available
- RRF score, when available
- rerank score, when available

Answer citations must point back to original source text and source metadata.
Generated contextual prefixes are not user-facing evidence.

## Eval Harness

Evals are part of v1 and can be run from the CLI and API without a frontend.

Tables:

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

Ragas provides LLM-judge metrics:

- faithfulness
- response relevancy
- context precision
- context recall

Custom deterministic metrics provide:

- recall@k
- MRR
- source_hit_rate
- citation_coverage
- cost per run
- latency per strategy

The first strategy matrix is:

- dense-only
- lexical-only
- hybrid RRF
- hybrid RRF plus rerank
- hybrid RRF plus rerank plus contextual chunks

The eval harness persists enough data to reproduce why one strategy beat
another.

## Observability and Audit Trail

The v1 uses local-first observability through Postgres and structured JSON logs.
No SaaS observability provider is required.

Tables:

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

Future adapters may export to OpenTelemetry or Langfuse, but v1 does not depend
on them.

## API Surface

Initial FastAPI endpoints:

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

## CLI Surface

Initial Typer commands:

- `adaptive-rag projects create`
- `adaptive-rag sources add-url`
- `adaptive-rag sources add-file`
- `adaptive-rag jobs run-worker`
- `adaptive-rag chat ask`
- `adaptive-rag retrieval search`
- `adaptive-rag eval run`

The CLI is a first-class development and learning surface while the frontend is
deferred.

## Auth and Deployment

The v1 is single-user and local-first.

Optional API key auth:

- If `ADAPTIVE_RAG_API_KEY` is set, mutable endpoints require
  `Authorization: Bearer <key>`.
- If it is not set, the app runs in local development mode without auth.

Docker Compose services:

- `api`
- `worker`
- `postgres` with pgvector

Optional Docker Compose profiles may add an Unstructured API service later, but
the default local stack must run without it.

The schema includes `users` and `projects.owner_user_id` for future multi-user
auth, but v1 does not implement registration, login, sessions, or OAuth.

## Testing Strategy

TDD coverage starts with core behavior:

- project isolation
- source creation and content hashing
- ingestion job claiming with `FOR UPDATE SKIP LOCKED`
- chunk creation and metadata preservation
- contextual chunk storage behavior
- embedding metadata tracking
- provider registry behavior with fakes
- document parser registry behavior with fakes
- Unstructured parser contract tests with representative fixture files
- retrieval filters by project
- RRF fusion
- citation payload generation
- tool-call orchestration with fake providers
- eval metric calculations

Provider SDK calls use fakes and contract tests first. Hosted provider smoke
tests are explicit, opt-in, and skipped when API keys are absent.

## Follow-up Phases

Phase 2 candidates:

- true BM25 or OpenSearch lexical retrieval if evals justify the added service
- learned sparse retrieval with
  `opensearch-project/opensearch-neural-sparse-encoding-multilingual-v1`
- LangGraph experimental agent mode
- PDF ingestion
- frontend built with an agent against stable API contracts
- local model profiles for chat, embeddings, and rerank
- OpenTelemetry or Langfuse export
- multi-user auth
