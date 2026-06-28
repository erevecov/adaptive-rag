# Tasks M38 chat retrieval settings

- [x] 1. Planificacion
  - [x] 1.1 Crear branch `codex/chat-rerank-settings` desde `origin/main`.
  - [x] 1.2 Revisar runtime settings, project overrides, chat service,
    retrieval service, audit/history y evals.
  - [x] 1.3 Crear proposal, design, tasks y deltas OpenSpec.
  - [x] 1.4 Validar `npx --yes @fission-ai/openspec validate
    m38-chat-retrieval-settings --strict`.

- [x] 2. Settings persistidos
  - [x] 2.1 Agregar tests fallidos para modelos global/project chat retrieval
    settings con defaults y constraints.
  - [x] 2.2 Agregar migracion Alembic y modelos SQLAlchemy.
  - [x] 2.3 Agregar repository con resolucion efectiva global/proyecto.
  - [x] 2.4 Agregar API schemas/routes globales y por proyecto.
  - [x] 2.5 Agregar cobertura CLI o dependencia reutilizable si el chat CLI lo
    necesita para resolver settings efectivos.

- [x] 3. Chat retrieval flow
  - [x] 3.1 Agregar tests fallidos para `ChatService` usando settings efectivos
    de retrieval y rerank.
  - [x] 3.2 Extender `ChatRequest`/`ChatRunnerRequest`/`ChatRetrievalTool` para
    transportar strategy y rerank options internos.
  - [x] 3.3 Wirear API/CLI para resolver settings efectivos y crear
    `RetrievalService` con reranker lazy solo cuando corresponde.
  - [x] 3.4 Persistir configuracion efectiva en audit/tool call summary sin
    exponer secrets.

- [x] 4. Frontend y API client
  - [x] 4.1 Agregar tipos y cliente para chat retrieval settings globales y por
    proyecto.
  - [x] 4.2 Agregar controles en Runtime settings globales y project overrides.
  - [x] 4.3 Cubrir estados disabled, inherited/overridden, validacion max 50 y
    candidate limit menor que retrieval limit.

- [x] 5. Medicion y cierre
  - [x] 5.1 Agregar smoke offline para chat con rerank efectivo via tests
    API/CLI deterministas.
  - [x] 5.2 Ejecutar tests backend relevantes.
  - [x] 5.3 Ejecutar tests frontend relevantes.
  - [x] 5.4 Ejecutar `uv run ruff check src tests`, `uv run mypy
    src\adaptive_rag`, OpenSpec strict y `git diff --check`.
  - [x] 5.5 Actualizar docs/progress.md y docs/roadmap.md al cerrar el change.
