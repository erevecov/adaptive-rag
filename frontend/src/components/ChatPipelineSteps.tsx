import { type ReactNode, useState } from 'react'

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
    const summary = `steps · ${current.elapsed} · ${sources}`
    if (!expanded) {
      return (
        <section
          aria-label="Chat pipeline steps"
          className="rounded-md border border-border bg-muted/40 p-3"
          data-slot="chat-pipeline-steps"
        >
          <button
            aria-label="Expand chat steps"
            className="flex w-full min-w-0 items-center gap-2 rounded-md px-2 py-2 text-left text-sm text-foreground transition-colors hover:bg-background"
            onClick={() => handleToggle(true)}
            type="button"
          >
            <StatusDot status={current.status} />
            <strong className="min-w-0 truncate">{current.label}</strong>
            <small className="text-muted-foreground">{current.elapsed}</small>
            <span aria-hidden="true" className="ml-auto text-muted-foreground">
              &gt;
            </span>
          </button>
        </section>
      )
    }

    return (
      <section
        aria-label="Chat pipeline steps"
        className="grid gap-3 rounded-md border border-border bg-muted/40 p-3"
        data-slot="chat-pipeline-steps"
      >
        <button
          aria-label="Collapse chat steps"
          className="inline-flex min-w-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          onClick={() => handleToggle(false)}
          type="button"
        >
          v {summary}
        </button>
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
  const summary = `details · ${elapsed} · ${sources}`

  if (!expanded) {
    return (
      <section
        aria-label="Chat pipeline steps"
        className="rounded-md border border-border bg-muted/40 p-3"
        data-slot="chat-pipeline-steps"
      >
        <button
          aria-label={`Expand chat steps, ${label}`}
          className="inline-flex min-w-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          onClick={() => handleToggle(true)}
          type="button"
        >
          &gt; {summary}
        </button>
      </section>
    )
  }

  return (
    <section
      aria-label="Chat pipeline steps"
      className="grid gap-3 rounded-md border border-border bg-muted/40 p-3"
      data-slot="chat-pipeline-steps"
    >
      <button
        aria-label={`Collapse chat steps, ${label}`}
        className="inline-flex min-w-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        onClick={() => handleToggle(false)}
        type="button"
      >
        v {summary}
      </button>
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
        className="rounded-md border border-dashed border-border bg-background/60 p-3 text-sm text-muted-foreground"
        data-slot="chat-pipeline-empty"
      >
        Waiting for pipeline steps.
      </p>
    )
  }
  return (
    <ol className="grid gap-2" data-slot="chat-pipeline-step-list">
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
      <span
        aria-hidden="true"
        className="w-3 shrink-0 text-muted-foreground group-open:rotate-90"
      >
        {hasDetail ? '>' : ''}
      </span>
      <StatusDot status={step.status} />
      <span className="grid min-w-0 flex-1 gap-1">
        <strong className="text-sm text-foreground">{stepLabel(step.id)}</strong>
        <InlineDetailChips step={step} />
      </span>
      <small className="text-xs text-muted-foreground">
        {formatStepDuration(step.elapsed_ms)}
      </small>
    </>
  )

  if (!hasDetail) {
    return (
      <div
        className="flex min-w-0 items-center gap-2 rounded-md border border-border bg-card p-3"
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
      <summary className="flex min-w-0 cursor-pointer list-none items-center gap-2 p-3 marker:content-none">
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
  return (
    <>
      {chips.slice(0, 3).map((chip) => (
        <span
          className="inline-flex w-fit rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
          data-slot="chat-pipeline-detail-chip"
          key={chip}
        >
          {chip}
        </span>
      ))}
    </>
  )
}

function StepDetail({ step }: { step: ChatStep }) {
  const detailEntries = Object.entries(step.detail ?? {})
  const usage = step.usage
  if (detailEntries.length === 0 && usage === undefined) {
    return (
      <p
        className="px-3 pb-3 text-sm text-muted-foreground"
        data-slot="chat-pipeline-empty"
      >
        No step detail recorded.
      </p>
    )
  }
  return (
    <dl
      className="grid gap-2 border-t border-border p-3"
      data-slot="chat-pipeline-step-detail"
    >
      {detailEntries.map(([key, value]) => (
        <div className="grid gap-1 rounded-md bg-muted/50 p-2" key={key}>
          <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            {formatDetailKey(key)}
          </dt>
          <dd className="break-words text-sm text-foreground">
            {formatDetailValue(value)}
          </dd>
        </div>
      ))}
      {usage !== undefined ? (
        <>
          <div className="grid gap-1 rounded-md bg-muted/50 p-2">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              model
            </dt>
            <dd className="break-words text-sm text-foreground">{usage.model}</dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/50 p-2">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              provider
            </dt>
            <dd className="break-words text-sm text-foreground">{usage.provider}</dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/50 p-2">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              tokens
            </dt>
            <dd className="break-words text-sm text-foreground">
              {formatTokens(usage.total_tokens)}
            </dd>
          </div>
          <div className="grid gap-1 rounded-md bg-muted/50 p-2">
            <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
              cost
            </dt>
            <dd className="break-words text-sm text-foreground">
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
        ? 'bg-primary'
        : 'bg-muted-foreground'
  return (
    <span
      aria-hidden="true"
      className={`size-2 shrink-0 rounded-full ${toneClassName}`}
      data-status={status}
      data-slot="chat-pipeline-status"
    />
  )
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
  return value === 1 ? '1 source' : `${value} sources`
}

function formatDetailKey(value: string): string {
  return value.replace(/_/g, ' ')
}

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'unknown'
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
  return value === undefined ? 'unknown tokens' : `${value.toLocaleString()} tokens`
}

function formatCost(value: number | undefined): string {
  return value === undefined ? 'unknown cost' : `$${value.toFixed(4)}`
}
