import { type ReactNode, useId, useState } from 'react'
import { Check, ChevronDown, CircleAlert, LoaderCircle } from 'lucide-react'

import { StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type ToolActivityItem = {
  detail?: ReactNode
  id: string
  label: string
  meta?: string
  status: 'running' | 'completed' | 'failed'
}

export type ToolActivityProps = {
  items: readonly ToolActivityItem[]
  label: string
}

const statusTone = {
  completed: 'success',
  failed: 'danger',
  running: 'primary',
} as const

function ToolStatusIcon({ status }: Pick<ToolActivityItem, 'status'>) {
  if (status === 'completed') {
    return <Check aria-hidden="true" className="size-3.5 shrink-0" />
  }
  if (status === 'failed') {
    return <CircleAlert aria-hidden="true" className="size-3.5 shrink-0" />
  }
  return <LoaderCircle aria-hidden="true" className="size-3.5 shrink-0 motion-safe:animate-spin" />
}

function ToolActivityRow({ item }: { item: ToolActivityItem }) {
  const [expanded, setExpanded] = useState(false)
  const detailId = useId()
  const canExpand = item.detail !== undefined && item.detail !== null

  const row = (
    <>
      <ToolStatusIcon status={item.status} />
      <span className="min-w-0 flex-1 truncate">{item.label}</span>
      {item.meta ? <span className="text-xs tabular-nums text-muted-foreground">{item.meta}</span> : null}
      <StatusBadge tone={statusTone[item.status]}>{item.status}</StatusBadge>
      {canExpand ? (
        <ChevronDown
          aria-hidden="true"
          className={cn('size-4 transition-transform motion-reduce:transition-none', expanded && 'rotate-180')}
        />
      ) : null}
    </>
  )

  return (
    <li className="border-b border-border last:border-b-0" data-slot="tool-activity-row" data-status={item.status}>
      {canExpand ? (
        <Button
          aria-controls={detailId}
          aria-expanded={expanded}
          className="h-auto min-h-9 w-full justify-start bg-transparent px-3 py-2 text-left text-sm hover:bg-muted/35 max-[680px]:min-h-11"
          onClick={() => setExpanded((value) => !value)}
          variant="ghost"
        >
          {row}
        </Button>
      ) : (
        <div className="flex min-h-9 items-center gap-2 px-3 py-2 text-sm max-[680px]:min-h-11">{row}</div>
      )}
      {canExpand && expanded ? (
        <div className="border-t border-border bg-muted/15 px-3 py-2 text-sm text-muted-foreground" id={detailId}>
          {item.detail}
        </div>
      ) : null}
    </li>
  )
}

export function ToolActivity({ items, label }: ToolActivityProps) {
  return (
    <section
      aria-label={label}
      className="overflow-hidden rounded-[2px] border border-border"
      data-slot="tool-activity"
    >
      <h2 className="border-b border-border bg-muted/20 px-3 py-2 text-sm font-medium">{label}</h2>
      <ul>
        {items.map((item) => (
          <ToolActivityRow item={item} key={item.id} />
        ))}
      </ul>
    </section>
  )
}
