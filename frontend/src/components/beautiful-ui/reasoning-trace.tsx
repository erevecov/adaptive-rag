import { type ReactNode, useId, useState } from 'react'
import { Check, ChevronDown, CircleAlert, LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type TraceStep = {
  detail?: ReactNode
  elapsedMs?: number | null
  id: string
  label: string
  status: 'running' | 'completed' | 'failed'
}

export type ReasoningTraceProps = {
  defaultExpanded?: boolean
  label: string
  steps: readonly TraceStep[]
}

const statusTone = {
  completed: 'success',
  failed: 'danger',
  running: 'primary',
} as const

function formatElapsed(elapsedMs: number): string {
  return `${(Math.max(0, elapsedMs) / 1_000).toFixed(1)}s`
}

function TraceStatusIcon({ status }: Pick<TraceStep, 'status'>) {
  const className = 'size-3.5 shrink-0'

  if (status === 'completed') {
    return <Check aria-hidden="true" className={className} />
  }
  if (status === 'failed') {
    return <CircleAlert aria-hidden="true" className={className} />
  }
  return <LoaderCircle aria-hidden="true" className={cn(className, 'motion-safe:animate-spin')} />
}

export function ReasoningTrace({
  defaultExpanded = false,
  label,
  steps,
}: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const detailsId = useId()

  return (
    <section aria-label={label} className="grid gap-1" data-slot="reasoning-trace">
      <Button
        aria-controls={detailsId}
        aria-expanded={expanded}
        className="h-auto min-h-8 justify-between border border-border bg-muted/20 px-3 py-2 text-left text-sm max-[680px]:min-h-11"
        onClick={() => setExpanded((value) => !value)}
        variant="ghost"
      >
        <span>{label}</span>
        <ChevronDown
          aria-hidden="true"
          className={cn('size-4 transition-transform motion-reduce:transition-none', expanded && 'rotate-180')}
        />
      </Button>
      {expanded ? (
        <ol
          className="grid gap-px overflow-hidden rounded-[2px] border border-border bg-border"
          data-slot="reasoning-trace-list"
          id={detailsId}
        >
          {steps.map((step) => (
            <li
              className="grid gap-2 bg-background p-3 text-sm max-[680px]:min-h-11"
              data-slot="reasoning-trace-step"
              data-status={step.status}
              key={step.id}
            >
              <div className="flex min-w-0 items-center gap-2">
                <TraceStatusIcon status={step.status} />
                <span className="min-w-0 flex-1 truncate">{step.label}</span>
                {typeof step.elapsedMs === 'number' ? (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {formatElapsed(step.elapsedMs)}
                  </span>
                ) : null}
                <StatusBadge tone={statusTone[step.status]}>{step.status}</StatusBadge>
              </div>
              {step.detail ? (
                <div className="border-l-2 border-border pl-3 text-sm text-muted-foreground">
                  {step.detail}
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  )
}
