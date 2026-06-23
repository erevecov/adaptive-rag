# Progreso de Adaptive RAG

## Milestone activo

M23 Product authoring surface.

M23 abre la superficie publica minima para crear/listar/ver projects y sources
por API, CLI y frontend. Este milestone no ejecuta ingestion ni expone job
state; eso queda para M24.

## Ultimo milestone completado

M22 V1 product scope reset cerrado el 2026-06-23.

M22 redefine v1 como producto local-first single-user terminado y archiva la
spec canonica `v1-product-completion`. M21 queda como evidencia de
core/pre-v1 y no como autorizacion para cortar tag o release v1.0.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec.
La brecha principal ahora es producto: authoring de projects/sources, ingestion
end-to-end desde superficies publicas, job state visible, onboarding local y
demo con datos propios.

## Ultimo slice completado

M23 `m23-authoring-api-contract`: agrega `ProjectRepository.list()` y endpoints
HTTP publicos para crear/listar/ver projects y sources, sin encolar ingestion ni
crear jobs.

Comandos validados en el slice M23 API:

```text
uv run pytest tests/unit/db/repositories/test_repositories.py::test_project_repository_lists_projects_in_deterministic_order -q
uv run pytest tests/integration/api/test_authoring.py -q
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m23-product-authoring-surface --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m23-product-authoring-surface/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m22-v1-product-scope-reset/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`
- `openspec/specs/ingestion-retrieval-plan/spec.md`
- `openspec/specs/ingestion-pipeline/spec.md`
- `openspec/specs/chunking-baseline/spec.md`
- `openspec/specs/embedding-baseline/spec.md`
- `openspec/specs/retrieval-baseline/spec.md`
- `openspec/specs/retrieval-surface/spec.md`
- `openspec/specs/chat-tool-calling/spec.md`
- `openspec/specs/evals-baseline/spec.md`
- `openspec/specs/provider-runtime/spec.md`
- `openspec/specs/hosted-evals/spec.md`
- `openspec/specs/retrieval-quality/spec.md`
- `openspec/specs/chat-audit-trail/spec.md`
- `openspec/specs/chat-history/spec.md`
- `openspec/specs/chat-frontend/spec.md`
- `openspec/specs/chat-streaming/spec.md`
- `openspec/specs/chat-observability/spec.md`
- `openspec/specs/graph-store/spec.md`
- `openspec/specs/v1-release-readiness/spec.md`
- `openspec/specs/v1-product-completion/spec.md`

## Siguiente tarea recomendada

- Abrir `m23-authoring-cli`. La opcion recomendada es implementar la CLI antes
  del frontend porque entrega un flujo local scriptable y reutiliza el contrato
  API/repository ya fijado por `m23-authoring-api-contract`.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
