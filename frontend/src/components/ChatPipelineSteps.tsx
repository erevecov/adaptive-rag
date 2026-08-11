import {
  type ReactNode,
  useId,
  useSyncExternalStore,
} from 'react'

import {
  ReasoningTrace,
  type TraceStep,
} from './beautiful-ui'
import {
  formatStepDuration,
  stepLabel,
  summarizeCurrentStep,
  type ChatStep,
  type ChatStepUsage,
} from '../lib/chatSteps'
import {
  getOpenDetailsInstanceId,
  setOpenDetailsInstanceId,
  subscribeOpenDetailsInstance,
} from '../lib/detailsAccordion'

type ChatPipelineStepsProps = {
  children?: ReactNode
  /**
   * Stable id for exclusive expand (accordion). When omitted, a React useId
   * is used so multiple steppers still collapse each other when one opens.
   */
  instanceId?: string
  isStreaming: boolean
  sourceCount: number
  steps: ChatStep[]
}

/** Subtle clickable summary — text link feel, no chrome. */
const PIPELINE_SUMMARY_TEXT_CLASS =
  'h-auto min-h-0 w-auto min-w-0 justify-start gap-1.5 rounded-none border-0 bg-transparent px-0 py-0.5 text-left text-xs font-normal text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground active:bg-transparent max-[680px]:min-h-11 max-[680px]:text-xs'

export function ChatPipelineSteps({
  children,
  instanceId: instanceIdProp,
  isStreaming,
  sourceCount,
  steps,
}: ChatPipelineStepsProps) {
  const reactId = useId()
  const instanceId = instanceIdProp ?? reactId
  const openId = useSyncExternalStore(
    subscribeOpenDetailsInstance,
    getOpenDetailsInstanceId,
    () => null,
  )
  const expanded = openId === instanceId

  if (!isStreaming && steps.length === 0) {
    return null
  }

  const handleExpandedChange = (nextExpanded: boolean) => {
    if (nextExpanded) {
      setOpenDetailsInstanceId(instanceId)
      return
    }
    if (getOpenDetailsInstanceId() === instanceId) {
      setOpenDetailsInstanceId(null)
    }
  }

  const sources = formatSources(sourceCount)
  let summary: ReactNode
  let toggleLabel: string

  if (isStreaming) {
    const current = summarizeCurrentStep(steps)
    const expandedSummary = `Steps · ${current.elapsed} · ${sources}`
    summary = expanded ? expandedSummary : (
      <>
        <strong className="min-w-0 flex-1 truncate font-medium">
          {current.label}
        </strong>
        <small className="min-w-[4.5ch] text-right tabular-nums">
          {current.elapsed}
        </small>
      </>
    )
    toggleLabel = expanded
      ? `Collapse Chat Steps, ${expandedSummary}`
      : `Expand Chat Steps, ${current.label}, ${statusAccessibleName(current.status)}, ${current.elapsed}`
  } else {
    const elapsed = formatStepDuration(totalStepElapsedMs(steps))
    const label = `${elapsed}, ${sources}`
    summary = `Details · ${elapsed} · ${sources}`
    toggleLabel = expanded
      ? `Collapse Chat Steps, ${label}`
      : `Expand Chat Steps, ${label}`
  }

  return (
    <ReasoningTrace
      empty={
        <p
          className="px-0 py-0.5 text-xs text-muted-foreground max-[680px]:text-xs"
          data-slot="chat-pipeline-empty"
          role="status"
        >
          Waiting For Pipeline Steps.
        </p>
      }
      expanded={expanded}
      label="Chat Pipeline Steps"
      onExpandedChange={handleExpandedChange}
      steps={steps.map(toTraceStep)}
      summary={summary}
      toggleClassName={PIPELINE_SUMMARY_TEXT_CLASS}
      toggleLabel={toggleLabel}
    >
      {children ? (
        <div
          className="grid gap-1.5 max-[680px]:gap-1"
          data-slot="chat-pipeline-extra-detail"
        >
          {children}
        </div>
      ) : null}
    </ReasoningTrace>
  )
}

function toTraceStep(step: ChatStep, index: number): TraceStep {
  const hasDetail =
    detailChips(step).length > 0 ||
    (step.usage !== undefined && usageDetailParts(step.usage).length > 0)
  return {
    collapsibleDetail: step.usage !== undefined && hasDetail,
    detail: hasDetail ? <StepDetail step={step} /> : undefined,
    elapsedLabel:
      step.elapsed_ms === undefined
        ? undefined
        : formatStepDuration(step.elapsed_ms),
    id: `${step.id}-${index}`,
    label: stepLabel(step.id),
    status: traceStatus(step.status),
  }
}

function StepDetail({ step }: { step: ChatStep }) {
  const chips = detailChips(step)
  const usage = step.usage === undefined ? [] : usageDetailParts(step.usage)
  if (chips.length === 0 && usage.length === 0) {
    return null
  }

  return (
    <div className="grid gap-1" data-slot="chat-pipeline-step-detail">
      {chips.length > 0 ? (
        <span className="flex min-w-0 flex-wrap items-center gap-1">
          {chips.map((chip) => (
            <span
              className="inline-flex max-w-[12rem] truncate rounded-[2px] bg-muted px-1 py-px text-[10px] font-medium text-muted-foreground"
              data-slot="chat-pipeline-detail-chip"
              key={chip}
            >
              {chip}
            </span>
          ))}
        </span>
      ) : null}
      {usage.length > 0 ? (
        <span className="flex flex-wrap items-center gap-1 text-[11px] leading-snug text-muted-foreground">
          {usage.map((part) => (
            <span key={part}>{part}</span>
          ))}
        </span>
      ) : null}
    </div>
  )
}

function detailChips(step: ChatStep): string[] {
  const chips: string[] = []
  const detail = step.detail ?? {}
  const preferred = [
    'result_count',
    'limit',
    'strategy',
    'tool_calls',
    'sources',
    'query',
  ]

  for (const key of preferred) {
    const value = detail[key]
    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      chips.push(String(value))
    }
  }
  for (const [key, value] of Object.entries(detail)) {
    if (preferred.includes(key)) {
      continue
    }
    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      const text = String(value)
      if (text.length > 0 && text.length <= 48 && !chips.includes(text)) {
        chips.push(text)
      }
    }
  }
  if (step.usage?.model && !chips.includes(step.usage.model)) {
    chips.push(step.usage.model)
  }
  return chips.slice(0, 4)
}

function traceStatus(status: ChatStep['status']): TraceStep['status'] {
  if (status === 'error') {
    return 'failed'
  }
  if (status === 'done') {
    return 'completed'
  }
  return 'running'
}

function usageDetailParts(usage: ChatStepUsage): string[] {
  const parts: string[] = []
  if (usage.model) {
    parts.push(usage.model)
  }
  if (usage.provider) {
    parts.push(usage.provider)
  }
  if (usage.input_tokens !== undefined) {
    parts.push(`${usage.input_tokens.toLocaleString()} in`)
  }
  if (usage.output_tokens !== undefined) {
    parts.push(`${usage.output_tokens.toLocaleString()} out`)
  }
  if (usage.total_tokens !== undefined) {
    parts.push(formatTokens(usage.total_tokens))
  }
  if (usage.estimated_cost_usd !== undefined) {
    parts.push(formatCost(usage.estimated_cost_usd))
  }
  return parts
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

function formatTokens(value: number | undefined): string {
  return value === undefined ? 'Unknown Tokens' : `${value.toLocaleString()} Tokens`
}

function formatCost(value: number | undefined): string {
  return value === undefined ? 'Unknown Cost' : `$${value.toFixed(4)}`
}
