# Progreso de Adaptive RAG

## Milestone activo

Ninguno. No hay changes OpenSpec activos despues de archivar M25.

## Ultimo milestone completado

M25 First-run onboarding cerrado el 2026-06-23.

M25 agrega el camino local reproducible de primera corrida: setup documentado,
`adaptive-rag first-run smoke`, datos sample/propios creados por superficies
publicas, ingestion, chunking, embeddings fake y chat con citations en un
reporte JSON. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m25-first-run-onboarding/` y publica la
spec canonica `first-run-onboarding`.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec.
La brecha principal ahora es el gate final de producto: demo final con datos
propios/sample, smokes documentados, evidencia de release y decision explicita
de v1.0.

## Ultimo slice completado

M25 `m25-quality-gate`: completa first-run onboarding por CLI/docs, valida
backend, frontend y OpenSpec, y archiva `m25-first-run-onboarding`.

Comandos validados en el cierre M25:

```text
uv run pytest
uv run ruff check .
uv run mypy src
uv run alembic heads
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
pnpm --dir frontend run build
npx --yes @fission-ai/openspec validate m25-first-run-onboarding --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m25-first-run-onboarding/`

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

- Abrir `m26-v1-product-quality-gate`. La opcion recomendada es cerrar el gate
  final de release real, porque M25 ya da una primera corrida reproducible y
  falta convertirla en evidencia completa de v1 con docs/smokes/demo final.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
