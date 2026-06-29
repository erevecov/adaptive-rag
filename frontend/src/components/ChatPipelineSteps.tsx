import { useState } from 'react'

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
  isStreaming: boolean
  sourceCount: number
  steps: ChatStep[]
}

export function ChatPipelineSteps({
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
    return (
      <section
        aria-label="Chat pipeline steps"
        className="chat-pipeline-steps chat-pipeline-steps-streaming"
      >
        <div className="pipeline-ticker">
          <span className={`pipeline-status pipeline-status-${current.status}`} />
          <strong>{current.label}</strong>
          <small>{current.elapsed}</small>
          <button
            aria-label={expanded ? 'Collapse chat steps' : 'Expand chat steps'}
            className="pipeline-toggle"
            onClick={() => handleToggle(!expanded)}
            type="button"
          >
            {expanded ? 'Hide' : 'Show'}
          </button>
        </div>
        {expanded ? <StepList steps={steps} /> : null}
      </section>
    )
  }

  return (
    <section aria-label="Chat pipeline steps" className="chat-pipeline-steps">
      <details
        open={expanded}
        onToggle={(event) =>
          handleToggle((event.currentTarget as HTMLDetailsElement).open)
        }
      >
        <summary>
          {`details - ${formatStepDuration(totalStepElapsedMs(steps))} - ${formatSources(sourceCount)}`}
        </summary>
        <StepList steps={steps} />
      </details>
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
          <details open>
            <summary>
              <span className={`pipeline-status pipeline-status-${step.status}`} />
              <strong>{stepLabel(step.id)}</strong>
              <small>{formatStepDuration(step.elapsed_ms)}</small>
            </summary>
            <StepDetail step={step} />
          </details>
        </li>
      ))}
    </ol>
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
