# Progreso de Adaptive RAG

## Milestone activo

M37 Project RBAC/chat knowledge activo en
`m37-project-rbac-chat-knowledge`.

Objetivo: convertir proyectos en espacios compartidos con usuarios,
membresias por proyecto, sesiones de chat privadas por usuario y flujo de
conocimiento propuesto desde chat. Todos los usuarios autenticados pueden ver
nombres de proyectos, pero solo `superadmin` o miembros asignados pueden
acceder. `superadmin` administra usuarios/proyectos globales; `admin`,
`contributor` y `viewer` operan por proyecto.

Estado de planificacion: disenio aprobado para auth local first-party,
`project_memberships`, `chat_sessions.user_id` y `knowledge_proposals`. El
OpenSpec M37 define el contrato antes de tocar schema, rutas o UI.

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

M36 Functional chat workspace: el chat quedo reorganizado como workspace
funcional de tres zonas: rail de sesiones, chat central e inspector derecho con
tabs Context/Minimap. La paleta ya no esta acoplada a Chat: Settings incluye
Appearance con temas globales Light, Dark y Purple, aplicados via `data-theme`,
`.dark` y `localStorage`. Session navigation, context/usage, minimap, action
stepper, source viewer desde citas actuales y chunks historicos, y STT browser
fallback quedaron implementados con tests. Qwen STT queda deferred porque la
documentacion actual de DashScope requiere ASR con `file_urls`/polling y no
existe contrato backend local de audio. Memory queda deferred tras verificar
que no hay tabla, repositorio ni ruta API durable.

Post-M35 final release gate/audit closeout (PR #142): re-ejecuto desde
`origin/main` el gate final local, confirmo `release_decision=ready_for_v1_0`,
valido el acceptance smoke post-runtime-settings y corrigio la exposicion de
secrets en `repr`.

Comandos validados al cerrar el gate/audit:

```text
uv run adaptive-rag v1 quality-gate --output artifacts\v1-quality-gate.json
uv run adaptive-rag acceptance runtime-settings-smoke --output artifacts\runtime-acceptance.json
uv run pytest
uv run ruff check .
uv run mypy src\adaptive_rag
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
uv tool run pip-audit --strict
pnpm --dir frontend audit --prod
uv tool run bandit -r src -q
git diff --check
```

Resultado: el producto queda listo segun el gate local (`ready_for_v1_0`), pero
no se creo tag ni GitHub release v1.0. La decision queda diferida
intencionalmente para permitir una feature pre-v1 adicional.

## Change OpenSpec activo

- `openspec/changes/m36-chat-functional-workspace/`
- `openspec/changes/m37-project-rbac-chat-knowledge/`

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

- Validar y revisar el OpenSpec M37. Si el contrato queda aprobado, el primer
  slice recomendado es `m37-auth-schema-repositories`, porque usuarios,
  membresias, ownership de sesiones y propuestas de conocimiento bloquean el
  resto del trabajo.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
