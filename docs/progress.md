# Progreso de Adaptive RAG

## Milestone activo

No hay OpenSpec changes activos.

## Ultimo milestone completado

M34 Runtime model catalog cerrado el 2026-06-24.

M34 elimina los IDs manuales de runtime settings para conexiones creadas desde
la UI, agrega un catalogo global de modelos por provider connection y permite
sincronizar IDs reales desde endpoints `/models` compatibles con Qwen/DashScope,
locales y fakes. La UI consume ese catalogo mediante selectors para defaults
globales, pool/default de chat y overrides por proyecto, preservando pricing o
metadata solo cuando el provider la entrega.
El change quedo archivado en
`openspec/changes/archive/2026-06-24-m34-runtime-model-catalog/` y actualiza
las specs canonicas `provider-runtime` y `chat-frontend`.

## Ultimo slice completado

M34 `m34-runtime-model-catalog`: agrega catalogo persistido de modelos por
conexion, sync de modelos Qwen/local/fake, IDs de conexiones generados por el
backend y selectors en Runtime settings/proyecto para usar IDs reales sin
memorizarlos.

Comandos validados al cerrar M34:

```text
uv run pytest
uv run ruff check src tests
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend build
npx --yes @fission-ai/openspec validate m34-runtime-model-catalog --strict
npx --yes @fission-ai/openspec archive m34-runtime-model-catalog --yes
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-24-m34-runtime-model-catalog/`

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

- Abrir un nuevo change OpenSpec para un milestone de acceptance end-to-end
  post-runtime-settings, validando el flujo local completo con project
  authoring, ingestion, sync/catalogo de modelos, runtime settings y chat citado
  antes de agregar nuevas features.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
