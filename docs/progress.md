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

Post-M35 `runtime-settings-ux-hardening` (PR #139): bloquea guardar global
slots, chat default y overrides por proyecto cuando la provider connection
seleccionada no tiene modelos compatibles sincronizados. La UI muestra un hint
de sync de modelos y deja los controles de save deshabilitados hasta que exista
catalogo compatible.

Comandos validados al cerrar el hardening:

```text
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
git diff --check
Browser QA Runtime settings: missing synced model hint visible, model select disabled, save disabled y consola limpia.
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

- Re-ejecutar desde `origin/main` el gate final de release/v1.0: acceptance
  smoke `adaptive-rag acceptance runtime-settings-smoke` sobre una base local
  real, suite backend/frontend minima y revision de docs de release. La opcion
  recomendada es decidir tag/GitHub release solo despues de ese gate; abrir un
  nuevo OpenSpec solo si aparece una capacidad nueva concreta.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
