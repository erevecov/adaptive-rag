# Progreso de Adaptive RAG

## Milestone activo

Ninguno. No hay changes OpenSpec activos despues de archivar M26.

## Ultimo milestone completado

M26 V1 product quality gate cerrado el 2026-06-23.

M26 agrega el gate final de producto v1: `adaptive-rag v1 quality-gate` ejecuta
la primera corrida publica, valida criterios de release, emite evidencia JSON
con `release_decision = ready_for_v1_0` y documenta que el tag o GitHub release
siguen siendo acciones manuales. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m26-v1-product-quality-gate/` y actualiza
las specs canonicas `v1-product-completion` y `v1-release-readiness`.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec. Con
M26, la brecha de producto local-first single-user queda cerrada para review de
release manual.

## Ultimo slice completado

M26 `m26-v1-product-quality-gate`: completa el gate final de producto v1 por
CLI/docs, valida backend, frontend y OpenSpec, y archiva
`m26-v1-product-quality-gate`.

Comandos validados en el cierre M26:

```text
uv run pytest
uv run ruff check .
uv run mypy src
uv run alembic heads
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
pnpm --dir frontend run build
npx --yes @fission-ai/openspec validate m26-v1-product-quality-gate --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m26-v1-product-quality-gate/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/product-authoring-surface/spec.md`
- `openspec/specs/ingestion-ops-surface/spec.md`
- `openspec/specs/first-run-onboarding/spec.md`
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

- Mergear el PR de M26 y reejecutar `uv run adaptive-rag v1 quality-gate` desde
  `main`. Si el artefacto conserva `release_decision = ready_for_v1_0`, la
  siguiente decision es manual: cortar tag/GitHub release v1.0 o abrir un
  OpenSpec post-v1 si se decide agregar alcance nuevo.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
