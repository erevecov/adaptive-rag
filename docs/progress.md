# Progreso de Adaptive RAG

## Milestone activo

No hay OpenSpec changes activos.

## Ultimo milestone completado

M32 Frontend polish cerrado el 2026-06-24.

M32 pule la UI de workspace local para project/source authoring, ingestion ops,
chat dense default, streaming, citations, historial y observability, con QA
responsive desktop/mobile. El cierre corrigio layout mobile de acciones y filas
operativas para evitar controles comprimidos.
El change quedo archivado en
`openspec/changes/archive/2026-06-24-m32-frontend-polish-plan/` y actualiza
las specs canonicas `chat-frontend`, `first-run-onboarding`,
`ingestion-ops-surface` y `product-authoring-surface`.

## Ultimo slice completado

M32 `m32-visual-qa-and-docs`: ejecuta QA visual con API mockeada sobre desktop
`1440x960` y mobile `390x844`, cubriendo chat, history, authoring,
observability y runtime settings; confirma sin overflow horizontal, controles
recortados ni errores de consola.

Comandos validados al cerrar M32:

```text
pnpm test
pnpm lint
pnpm typecheck
pnpm build
npx --yes @fission-ai/openspec validate m32-frontend-polish-plan --strict
npx --yes @fission-ai/openspec archive m32-frontend-polish-plan --yes
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-24-m32-frontend-polish-plan/`

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
  post-polish, validando el flujo local completo con project authoring,
  ingestion, runtime settings y chat citado antes de agregar nuevas features.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
