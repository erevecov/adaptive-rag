# FE OPERATOR report — 20260805 pass-2 (post-#206)

STATUS: ready-for-lead-review

Branch: `feat/ui-obsessional-polish` (= origin/main tip post PR #206 merge)

## This pass
Closed remaining P0/P1 after merge tip already contained knowledge Working status, job grouping, observability tablist/stale banner.

### P0 fixed
| Finding | Fix |
|---------|-----|
| CapabilitySelector combobox ARIA on non-focusable shell | Moved `role=combobox` / `aria-expanded` / `aria-controls` to filter `Input`; stopPropagation so Trigger does not toggle-close |
| Catalog empty ≡ loading | `ProviderModelCatalogView` loading slot when `isLoading && length===0` |

### P1 fixed
| Finding | Fix |
|---------|-----|
| Capabilities label without htmlFor | `htmlFor="runtime-capability-filter"` |
| Listbox empty as EmptyState inside listbox | `role="status"` text instead |
| Option `aria-selected` missing | `aria-selected={false}` on options |
| Chip remove steals tab stops | `tabIndex={-1}` on remove chips |
| Retrieval orphan `aria-describedby` | Only when rerank off |
| Error breakdown nested cards | Flat `DataListItem` (`border-0 bg-transparent`) |

### Tests
Focused vitest authoring/runtime/retrieval/observability — **41 passed**.

## Coordination
BACKLOG operator claims → done for this pass.
