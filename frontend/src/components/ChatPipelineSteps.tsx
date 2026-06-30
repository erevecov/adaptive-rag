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
          className="chat-pipeline-steps chat-pipeline-steps-streaming"
        >
          <button
            aria-label="Expand chat steps"
            className="pipeline-ticker pipeline-ticker-button"
            onClick={() => handleToggle(true)}
            type="button"
          >
            <span className={`pipeline-status pipeline-status-${current.status}`} />
            <strong>{current.label}</strong>
            <small>{current.elapsed}</small>
            <span aria-hidden="true" className="pipeline-chevron">
              ▸
            </span>
          </button>
        </section>
      )
    }

    return (
      <section
        aria-label="Chat pipeline steps"
        className="chat-pipeline-steps chat-pipeline-steps-streaming"
      >
        <button
          aria-label="Collapse chat steps"
          className="pipeline-summary-button"
          onClick={() => handleToggle(false)}
          type="button"
        >
          ▾ {summary}
        </button>
        <StepList steps={steps} />
        {children ? <div className="pipeline-extra-detail">{children}</div> : null}
      </section>
    )
  }

  const elapsed = formatStepDuration(totalStepElapsedMs(steps))
  const sources = formatSources(sourceCount)
  const label = `${elapsed}, ${sources}`
  const summary = `details · ${elapsed} · ${sources}`

  if (!expanded) {
    return (
      <section aria-label="Chat pipeline steps" className="chat-pipeline-steps">
        <button
          aria-label={`Expand chat steps, ${label}`}
          className="pipeline-summary-button"
          onClick={() => handleToggle(true)}
          type="button"
        >
          ▸ {summary}
        </button>
      </section>
    )
  }

  return (
    <section aria-label="Chat pipeline steps" className="chat-pipeline-steps">
      <button
        aria-label={`Collapse chat steps, ${label}`}
        className="pipeline-summary-button"
        onClick={() => handleToggle(false)}
        type="button"
      >
        ▾ {summary}
      </button>
      <StepList steps={steps} />
      {children ? <div className="pipeline-extra-detail">{children}</div> : null}
    </section>
  )
}

function StepList({ steps }: { steps: ChatStep[] }) {
  if (steps.length === 0) {
    return <p className="empty-copy">Waiting for pipeline steps.</p>
  }
  return (
    <ol className="pipeline-step-list">
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
      <span aria-hidden="true" className="pipeline-row-caret">
        {hasDetail ? '▸' : ''}
      </span>
      <span className={`pipeline-status pipeline-status-${step.status}`} />
      <span className="pipeline-step-main">
        <strong>{stepLabel(step.id)}</strong>
        <InlineDetailChips step={step} />
      </span>
      <small>{formatStepDuration(step.elapsed_ms)}</small>
    </>
  )

  if (!hasDetail) {
    return <div className="pipeline-step-row-static">{content}</div>
  }

  return (
    <details className="pipeline-step-row">
      <summary>{content}</summary>
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
        <span className="pipeline-detail-chip" key={chip}>
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
    return <p className="empty-copy">No step detail recorded.</p>
  }
  return (
    <dl className="pipeline-step-detail">
      {detailEntries.map(([key, value]) => (
        <div key={key}>
          <dt>{formatDetailKey(key)}</dt>
          <dd>{formatDetailValue(value)}</dd>
        </div>
      ))}
      {usage !== undefined ? (
        <>
          <div>
            <dt>model</dt>
            <dd>{usage.model}</dd>
          </div>
          <div>
            <dt>provider</dt>
            <dd>{usage.provider}</dd>
          </div>
          <div>
            <dt>tokens</dt>
            <dd>{formatTokens(usage.total_tokens)}</dd>
          </div>
          <div>
            <dt>cost</dt>
            <dd>{formatCost(usage.estimated_cost_usd)}</dd>
          </div>
        </>
      ) : null}
    </dl>
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
