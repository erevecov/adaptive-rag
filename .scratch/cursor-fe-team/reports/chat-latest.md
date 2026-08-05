# Chat+Shell FE report — pass 2

**Role:** FE CHAT+SHELL (`fe-chat`)  
**Branch:** `feat/ui-obsessional-polish`  
**STATUS:** ready-for-lead-review

## This commit

| Severity | Fix |
|----------|-----|
| P0 | Primary button focus ring: solid `ring-primary-foreground` (purple ≥3:1) |
| P0 | Knowledge draft textarea: drop `ring-ring/40` / offset-1 → DS ring tokens |
| P1 | Session rename: blur saves when dirty; unchanged blur still cancels |

## Already on tip (prior commits)

Overlay `isBackgroundInert` (sidebar/topline/skip), soft-delete `Deleted` / `source removed`, minimap aria truncate, speech mobile wrap, history `motion-safe` pulses, AppShell motion-safe width transition.

## Verify

```
pnpm --dir frontend exec vitest run \
  src/components/ui/button.test.tsx \
  src/features/chat/ChatWorkspaceView.test.tsx \
  src/features/history/HistoryInspectorView.test.tsx
```
→ **34 passed**

## Next pass candidates

- Escape on inline inspector (gate to overlay)
- Locale consistency pass (rail ES vs chrome EN)
- Hostile re-read of composer ≤680 + purple theme live

No push from this agent; Grok merges.
