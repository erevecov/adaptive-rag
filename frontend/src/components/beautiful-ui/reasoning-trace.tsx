import { type ReactNode, useId, useState } from 'react'
import { Check, ChevronDown, CircleAlert, LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type TraceStep = {
  collapsibleDetail?: boolean
  detail?: ReactNode
  elapsedLabel?: string
  elapsedMs?: number | null
  id: string
  label: string
  status: 'running' | 'completed' | 'failed'
}

export type ReasoningTraceProps = {
  children?: ReactNode
  defaultExpanded?: boolean
  empty?: ReactNode
  expanded?: boolean
  label: string
  onExpandedChange?(expanded: boolean): void
  steps: readonly TraceStep[]
  summary?: ReactNode
  toggleClassName?: string
  toggleLabel?: string
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
  children,
  defaultExpanded = false,
  empty,
  expanded: expandedProp,
  label,
  onExpandedChange,
  steps,
  summary,
  toggleClassName,
  toggleLabel,
}: ReasoningTraceProps) {
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded)
  const expanded = expandedProp ?? internalExpanded
  const detailsId = useId()

  function handleToggle() {
    const nextExpanded = !expanded
    if (expandedProp === undefined) {
      setInternalExpanded(nextExpanded)
    }
    onExpandedChange?.(nextExpanded)
  }

  return (
    <section aria-label={label} className="grid gap-1" data-slot="reasoning-trace">
      <Button
        aria-controls={detailsId}
        aria-expanded={expanded}
        aria-label={toggleLabel}
        className={cn(
          'h-auto min-h-8 justify-between border border-border bg-muted/20 px-3 py-2 text-left text-sm max-[680px]:min-h-11',
          toggleClassName,
        )}
        onClick={handleToggle}
        variant="ghost"
      >
        {summary ?? <span>{label}</span>}
        <ChevronDown
          aria-hidden="true"
          className={cn('size-4 transition-transform motion-reduce:transition-none', expanded && 'rotate-180')}
        />
      </Button>
      {expanded ? (
        <div className="grid gap-2" data-slot="reasoning-trace-detail" id={detailsId}>
          {steps.length > 0 ? (
            <ol
              className="grid gap-px overflow-hidden rounded-[2px] border border-border bg-border"
              data-slot="reasoning-trace-list"
            >
              {steps.map((step) => (
                <li
                  className="grid gap-2 bg-background p-3 text-sm max-[680px]:min-h-11"
                  data-slot="reasoning-trace-step"
                  data-status={step.status}
                  key={step.id}
                >
                  {step.collapsibleDetail && step.detail ? (
                    <details>
                      <summary className="cursor-pointer list-none marker:content-none [&::-webkit-details-marker]:hidden">
                        <TraceStepHeader step={step} />
                      </summary>
                      <TraceStepDetail>{step.detail}</TraceStepDetail>
                    </details>
                  ) : (
                    <>
                      <TraceStepHeader step={step} />
                      {step.detail ? (
                        <TraceStepDetail>{step.detail}</TraceStepDetail>
                      ) : null}
                    </>
                  )}
                </li>
              ))}
            </ol>
          ) : (
            empty
          )}
          {children}
        </div>
      ) : null}
    </section>
  )
}

function TraceStepHeader({ step }: { step: TraceStep }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <TraceStatusIcon status={step.status} />
      <span className="min-w-0 flex-1 truncate">{step.label}</span>
      {step.elapsedLabel || typeof step.elapsedMs === 'number' ? (
        <span className="text-xs tabular-nums text-muted-foreground">
          {step.elapsedLabel ?? formatElapsed(step.elapsedMs!)}
        </span>
      ) : null}
      <StatusBadge tone={statusTone[step.status]}>{step.status}</StatusBadge>
    </span>
  )
}

function TraceStepDetail({ children }: { children: ReactNode }) {
  return (
    <div className="mt-2 border-l-2 border-border pl-3 text-sm text-muted-foreground">
      {children}
    </div>
  )
}
