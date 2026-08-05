# FE OPERATOR report — 20260805

STATUS: ready-for-lead-review

Commit: `b20eee9` — `fix(ui): operator secret-safe runtime and truthful status UX` (no push)

Note: authoring empty≠loading / soft-delete tones / badge emerald+amber and observability stale banner were already on branch tip from prior hardening commits; this commit lands runtime secret-safe + tests + coordination artifacts.


## Pass summary
Obsessive audit + P0/P1 implementation across authoring, retrieval, observability, runtime, and shared badge/feedback tones.

## P0 fixed
| Finding | Fix |
|---------|-----|
| Empty ≡ loading (authoring lists, runtime connections) | `LoadingListState` / `data-slot-state="loading"` before empty |
| `canceled` labeled Ready | Labels → `Canceled`; tone `neutral` |
| Success badge = primary brand | `badge.tsx` / Callout success → emerald semantic |
| Warning ≈ neutral (purple) | warning → amber semantic |
| Runtime check echo raw `message` | `operatorSafeMessage` + fixed fail copy; never paint secrets raw |
| Retrieval stale results on validation fail / loading | `setResults([])` + loading slot |
| Observability failed refresh with stale summary | Callout + `observability-stale-failed` opacity |

## P1 fixed
| Finding | Fix |
|---------|-----|
| Soft-delete projects weaker than sources | danger tone + Soft-deleted timestamp |
| `idle` last-run warning | `jobTone('idle')` → neutral |
| Retry ignores busy | `disabled={isBusy}` |
| Binary upload feedback | `No file selected` / `Selected:` + `aria-describedby` |
| Destructive actions secondary | Delete/Deactivate/Remove → `variant="danger"` |
| Retrieval rank cards | DataList rank cards (score, strategy, distance, snippet) |
| Idle / zero-hit empty | Operator next-steps copy |
| Focus ring overrides on retrieval | Removed; inherit control primitives |
| Observability refresh affordance | opacity + `motion-safe:animate-pulse` |
| Metric grid 3-in-5 | `columns={3}` for costs/errors/latency |
| Skeleton pulse | `motion-safe:animate-pulse` |
| Runtime project overrides hides status | RuntimeStatus + project id badge |
| API key edit help | Leave blank to keep existing key |
| Sync-blocking feedback | `tone="warning"` |
| Status labels loading | runtime `Working…` |

## P2 deferred (backlog)
- Relative times / job grouping by status
- CapabilitySelector full ARIA (input aria-expanded)
- Observability SegmentedControl as tablist
- Nested breakdown card density
- Knowledge end-to-end draft affordances

## Tests
Focused vitest: authoring, retrieval, observability, runtime, badge, `operatorSafeMessage` — **42 passed**.

## Files touched (high level)
- `frontend/src/features/authoring/AuthoringView.tsx` (+tests)
- `frontend/src/features/retrieval/RetrievalPlaygroundView.tsx` (+tests)
- `frontend/src/features/observability/ObservabilityView.tsx` (+tests)
- `frontend/src/features/runtime/RuntimeSettingsView.tsx`, `runtimeUi.ts` (+tests)
- `frontend/src/components/ui/badge.tsx`, `feedback.tsx`
- `frontend/src/lib/operatorSafeMessage.ts` (+test)

## Coordination
BACKLOG claims marked **done** for operator themes completed this pass.
