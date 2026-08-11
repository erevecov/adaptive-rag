import { Button } from '@/components/ui/button'

export type SelectionAction = { id: string; label: string }

export type SelectionToolbarProps = {
  actions: readonly SelectionAction[]
  disabled?: boolean
  onAction(id: string): void
}

export function SelectionToolbar({
  actions,
  disabled = false,
  onAction,
}: SelectionToolbarProps) {
  return (
    <div
      aria-label="Selection actions"
      className="flex flex-wrap gap-2 rounded-[2px] border border-border bg-card p-2 motion-safe:transition-colors max-[680px]:gap-1"
      data-slot="selection-toolbar"
      role="toolbar"
    >
      {actions.map((action) => (
        <Button disabled={disabled} key={action.id} onClick={() => onAction(action.id)} variant="secondary">
          {action.label}
        </Button>
      ))}
    </div>
  )
}
