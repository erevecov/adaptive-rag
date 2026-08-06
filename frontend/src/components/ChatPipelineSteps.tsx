import { type ReactNode, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

import {
  formatStepDuration,
  stepLabel,
  summarizeCurrentStep,
  type ChatStep,
} from '../lib/chatSteps'
import {
  readStepperExpandedPreference,
  writeStepperExpandedPreference,
} from '../lib/stepperPreference'
import { Button } from './ui/button'

type ChatPipelineStepsProps = {
  children?: ReactNode
  isStreaming: boolean
  sourceCount: number
  steps: ChatStep[]
}

export function ChatPipelineSteps({
  children,
  isStreaming,
  sourceCount,
  steps,
}: ChatPipelineStepsProps) {
  const [expanded, setExpanded] = useState(readStepperExpandedPreference)

  if (!isStreaming && steps.length === 0) {
    return null
  }

  const handleToggle = (nextExpanded: boolean) => {
    setExpanded(nextExpanded)
    writeStepperExpandedPreference(nextExpanded)
  }

  if (isStreaming) {
    const current = summarizeCurrentStep(steps)
    const sources = formatSources(sourceCount)
    const summary = `Steps · ${current.elapsed} · ${sources}`
    const statusLabel = statusAccessibleName(current.status)
    if (!expanded) {
      return (
        <section
          aria-label="Chat Pipeline Steps"
          className="rounded-md border border-border bg-muted/15 p-3 max-[680px]:rounded-sm max-[680px]:p-1"
          data-slot="chat-pipeline-steps"
        >
          <Button
            aria-expanded={false}
            aria-label={`Expand Chat Steps, ${current.label}, ${statusLabel}, ${current.elapsed}`}
            className="h-auto w-full min-w-0 justify-start px-2 py-2 text-left"
            onClick={() => handleToggle(true)}
            type="button"
            variant="secondary"
          >
            <StatusDot status={current.status} />
            <strong className="min-w-0 flex-1 truncate">{current.label}</strong>
            <small className="min-w-[4.5ch] text-right text-muted-foreground tabular-nums">
              {current.elapsed}
            </small>
            <ChevronRight
              aria-hidden="true"
              className="ml-auto size-4 text-muted-foreground"
            />
          </Button>
        </section>
      )
    }

    return (
      <section
        aria-label="Chat Pipeline Steps"
        className="grid gap-3 rounded-md border border-border bg-muted/15 p-3 max-[680px]:gap-1.5 max-[680px]:rounded-sm max-[680px]:p-1"
        data-slot="chat-pipeline-steps"
      >
        <Button
          aria-expanded={true}
          aria-label={`Collapse Chat Steps, ${summary}`}
          className="h-auto min-w-0 justify-start text-left"
          onClick={() => handleToggle(false)}
          type="button"
          variant="secondary"
        >
          <ChevronDown aria-hidden="true" className="size-4" />
          <span>{summary}</span>
        </Button>
        <StepList steps={steps} />
        {children ? (
          <div className="grid gap-3" data-slot="chat-pipeline-extra-detail">
            {children}
          </div>
        ) : null}
      </section>
    )
  }

  const elapsed = formatStepDuration(totalStepElapsedMs(steps))
  const sources = formatSources(sourceCount)
  const label = `${elapsed}, ${sources}`
  const summary = `Details · ${elapsed} · ${sources}`

  if (!expanded) {
    return (
      <section
        aria-label="Chat Pipeline Steps"
        className="rounded-md border border-border bg-muted/15 p-3 max-[680px]:rounded-sm max-[680px]:p-1"
        data-slot="chat-pipeline-steps"
      >
        <Button
          aria-expanded={false}
          aria-label={`Expand Chat Steps, ${label}`}
          className="h-auto min-w-0 justify-start text-left"
          onClick={() => handleToggle(true)}
          type="button"
          variant="secondary"
        >
          <ChevronRight aria-hidden="true" className="size-4" />
          <span>{summary}</span>
        </Button>
      </section>
    )
  }

  return (
    <section
      aria-label="Chat Pipeline Steps"
      className="grid gap-3 rounded-md border border-border bg-muted/15 p-3 max-[680px]:gap-1.5 max-[680px]:rounded-sm max-[680px]:p-1"
      data-slot="chat-pipeline-steps"
    >
      <Button
        aria-expanded={true}
        aria-label={`Collapse Chat Steps, ${label}`}
        className="h-auto min-w-0 justify-start text-left"
        onClick={() => handleToggle(false)}
        type="button"
        variant="secondary"
      >
        <ChevronDown aria-hidden="true" className="size-4" />
        <span>{summary}</span>
      </Button>
      <StepList steps={steps} />
      {children ? (
        <div className="grid gap-3" data-slot="chat-pipeline-extra-detail">
          {children}
        </div>
      ) : null}
    </section>
  )
}

function StepList({ steps }: { steps: ChatStep[] }) {
  if (steps.length === 0) {
    return (
      <p
        className="rounded-md border border-dashed border-border bg-background/60 p-2 text-xs text-muted-foreground max-[680px]:p-1 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug"
        data-slot="chat-pipeline-empty"
        role="status"
      >
        Waiting For Pipeline Steps.
      </p>
    )
  }
  return (
    <ol className="grid gap-2 max-[680px]:gap-1" data-slot="chat-pipeline-step-list">
      {steps.map((step, index) => (
        <li key={`${step.id}-${index}`}>
          <StepRow step={step} />
        </li>
      ))}
    </ol>
  )
}

function StepRow({ step }: { step: ChatStep }) {
  const hasDetail =
    Object.keys(step.detail ?? {}).length > 0 || step.usage !== undefined
  const content = (
    <>
      {hasDetail ? (
        <ChevronRight
          aria-hidden="true"
          className="size-3.5 shrink-0 text-muted-foreground motion-safe:transition-transform group-open:rotate-90"
        />
      ) : (
        <span aria-hidden="true" className="size-3.5 shrink-0" />
      )}
      <StatusDot status={step.status} />
      <span className="grid min-w-0 flex-1 gap-1">
        <strong className="text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">{stepLabel(step.id)}</strong>
        <InlineDetailChips step={step} />
      </span>
      <small className="text-xs text-muted-foreground tabular-nums max-[680px]:text-[0.5625rem]">
        {formatStepDuration(step.elapsed_ms)}
      </small>
    </>
  )

  if (!hasDetail) {
    return (
      <div
        className="flex min-w-0 items-center gap-2 rounded-md border border-border bg-card p-3 max-[680px]:gap-1 max-[680px]:rounded-sm max-[680px]:p-1"
        data-slot="chat-pipeline-step-row"
      >
        {content}
      </div>
    )
  }

  return (
    <details
      className="group rounded-md border border-border bg-card"
      data-slot="chat-pipeline-step-row"
    >
      <summary className="flex min-h-11 min-w-0 cursor-pointer list-none items-center gap-2 rounded-md p-3 marker:content-none hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background max-[680px]:min-h-11 max-[680px]:gap-1 max-[680px]:p-1">
        {content}
      </summary>
      <StepDetail step={step} />
    </details>
  )
}

function InlineDetailChips({ step }: { step: ChatStep }) {
  const chips: string[] = []
  const detail = step.detail ?? {}
  for (const key of ['result_count', 'limit', 'strategy', 'tool_calls']) {
    const value = detail[key]
    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      chips.push(`${formatDetailKey(key)} ${String(value)}`)
    }
  }
  if (step.usage !== undefined) {
    chips.push(step.usage.model)
  }
  if (chips.length === 0) {
    return null
  }
  return (
    <span className="flex flex-wrap gap-1.5 max-[680px]:gap-1">
      {chips.slice(0, 3).map((chip) => (
        <span
          className="inline-flex w-fit rounded-md border border-border bg-muted/15 px-2 py-0.5 text-xs font-medium text-muted-foreground max-[680px]:px-1 max-[680px]:text-[0.5625rem]"
          data-slot="chat-pipeline-detail-chip"
          key={chip}
        >
          {chip}
        </span>
      ))}
    </span>
  )
}

function StepDetail({ step }: { step: ChatStep }) {
  const detailEntries = Object.entries(step.detail ?? {})
  const usage = step.usage
  if (detailEntries.length === 0 && usage === undefined) {
    return (
      <p
        className="px-3 pb-3 text-sm text-muted-foreground max-[680px]:px-1.5 max-[680px]:pb-1.5 max-[680px]:text-[0.625rem] max-[680px]:leading-snug"
        data-slot="chat-pipeline-empty"
      >
        No Step Detail Recorded.
      </p>
    )
  }
  return (
    <dl
      className="grid gap-2 border-t border-border p-3 max-[680px]:gap-1 max-[680px]:p-1"
      data-slot="chat-pipeline-step-detail"
    >
      {detailEntries.map(([key, value]) => (
        <div className="grid gap-1 rounded-md bg-muted/15 p-2 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:p-1" key={key}>
          <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
            {formatDetailKey(key)}
          </dt>
          <dd className="break-words text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">
            {formatDetailValue(value)}
          </dd>
        </div>
      ))}
      {usage !== undefined ? (
        <>
          <div className="grid gap-1 rounded-md bg-muted/15 p-2 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:p-1">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
              Model
            </dt>
            <dd className="break-words text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">{usage.model}</dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/15 p-2 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:p-1">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
              Provider
            </dt>
            <dd className="break-words text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">{usage.provider}</dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/15 p-2 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:p-1">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
              Tokens
            </dt>
            <dd className="break-words text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">
              {formatTokens(usage.total_tokens)}
            </dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/15 p-2 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:p-1">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
              Cost
            </dt>
            <dd className="break-words text-sm text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">
              {formatCost(usage.estimated_cost_usd)}
            </dd>
          </div>
        </>
      ) : null}
    </dl>
  )
}

function StatusDot({ status }: { status: ChatStep['status'] }) {
  const toneClassName =
    status === 'error'
      ? 'bg-destructive'
      : status === 'done'
        ? 'bg-emerald-500'
        : 'bg-muted-foreground motion-safe:animate-pulse'
  return (
    <span className="inline-flex shrink-0 items-center" data-slot="chat-pipeline-status">
      <span
        aria-hidden="true"
        className={`size-2 rounded-full ${toneClassName}`}
        data-status={status}
      />
      <span className="sr-only">{statusAccessibleName(status)}</span>
    </span>
  )
}

function statusAccessibleName(status: ChatStep['status']): string {
  if (status === 'error') {
    return 'error'
  }
  if (status === 'done') {
    return 'done'
  }
  return 'running'
}

function totalStepElapsedMs(steps: ChatStep[]): number | null {
  const answer = [...steps]
    .reverse()
    .find((step) => step.id === 'answer' && step.elapsed_ms !== undefined)
  if (answer?.elapsed_ms !== undefined) {
    return answer.elapsed_ms
  }
  const lastTimed = [...steps]
    .reverse()
    .find((step) => step.elapsed_ms !== undefined)
  return lastTimed?.elapsed_ms ?? null
}

function formatSources(value: number): string {
  return value === 1 ? '1 Source' : `${value} Sources`
}

function formatDetailKey(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'Unknown'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

function formatTokens(value: number | undefined): string {
  return value === undefined ? 'Unknown Tokens' : `${value.toLocaleString()} Tokens`
}

function formatCost(value: number | undefined): string {
  return value === undefined ? 'Unknown Cost' : `$${value.toFixed(4)}`
}
