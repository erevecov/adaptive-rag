# Progreso de Adaptive RAG

## Milestone activo

No hay OpenSpec changes activos.

## Ultimo milestone completado

M35 Acceptance e2e post-runtime-settings cerrado el 2026-06-24.

M35 agrega `adaptive-rag acceptance runtime-settings-smoke`, un gate local que
configura provider connections fake, sincroniza model catalog, setea slots
globales, crea un override por proyecto y ejecuta ingestion/indexing/chat citado
resolviendo providers desde runtime settings persistidos.
El change quedo archivado en
`openspec/changes/archive/2026-06-24-m35-acceptance-e2e-post-runtime-settings/`
y actualiza las specs canonicas `provider-runtime` y
`v1-product-completion`.

## Ultimo slice completado

M35 `m35-acceptance-e2e-post-runtime-settings`: agrega runner/CLI de acceptance,
runbook `docs/runtime-acceptance.md`, tests CLI/docs y evidencia JSON para
catalogo, slots efectivos, runtime resolution y first-run citado.

Comandos validados al cerrar M35:

```text
uv run pytest
uv run ruff check src tests
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend build
npx --yes @fission-ai/openspec validate m35-acceptance-e2e-post-runtime-settings --strict
npx --yes @fission-ai/openspec archive m35-acceptance-e2e-post-runtime-settings --yes
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-24-m35-acceptance-e2e-post-runtime-settings/`

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

- Ejecutar el nuevo acceptance smoke sobre una base local real desde `main`
  despues del merge. Si pasa, la siguiente decision recomendada es un change
  pequeno para hardening de UX/error states de Runtime settings con evidencia
  del smoke, no nuevas capacidades de provider.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
