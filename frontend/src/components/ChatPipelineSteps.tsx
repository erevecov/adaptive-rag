import {
  type ComponentType,
  createElement,
  type ReactNode,
  type SVGProps,
  useId,
  useSyncExternalStore,
} from 'react'
import {
  ArrowUpDown,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Database,
  Layers,
  LoaderCircle,
  MessageSquare,
  Search,
} from 'lucide-react'

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
import { Button } from './ui/button'
import { cn } from '../lib/utils'

type IconType = ComponentType<SVGProps<SVGSVGElement>>

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

const STEP_ICONS: Record<string, IconType> = {
  retrieval: Search,
  rerank: ArrowUpDown,
  answer: MessageSquare,
  context: Layers,
  embedding: Search,
}

function iconForStep(id: string): IconType {
  if (STEP_ICONS[id] !== undefined) {
    return STEP_ICONS[id]
  }
  const root = id.includes('.') ? id.split('.')[0]! : id
  return STEP_ICONS[root] ?? Database
}

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
  // Closed by default; only the matching instance stays open (accordion).
  const expanded = openId === instanceId

  if (!isStreaming && steps.length === 0) {
    return null
  }

  const handleToggle = (nextExpanded: boolean) => {
    if (nextExpanded) {
      setOpenDetailsInstanceId(instanceId)
      return
    }
    if (getOpenDetailsInstanceId() === instanceId) {
      setOpenDetailsInstanceId(null)
    }
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
          className="min-w-0"
          data-slot="chat-pipeline-steps"
        >
          <Button
            aria-expanded={false}
            aria-label={`Expand Chat Steps, ${current.label}, ${statusLabel}, ${current.elapsed}`}
            className={PIPELINE_SUMMARY_TEXT_CLASS}
            onClick={() => handleToggle(true)}
            type="button"
            variant="ghost"
          >
            <StatusIcon status={current.status} />
            <strong className="min-w-0 flex-1 truncate font-medium">
              {current.label}
            </strong>
            <small className="min-w-[4.5ch] text-right tabular-nums">
              {current.elapsed}
            </small>
            <ChevronRight
              aria-hidden="true"
              className="ml-auto size-3.5 opacity-70"
            />
          </Button>
        </section>
      )
    }

    return (
      <section
        aria-label="Chat Pipeline Steps"
        className="grid min-w-0 gap-1.5 max-[680px]:gap-1"
        data-slot="chat-pipeline-steps"
      >
        <Button
          aria-expanded={true}
          aria-label={`Collapse Chat Steps, ${summary}`}
          className={PIPELINE_SUMMARY_TEXT_CLASS}
          onClick={() => handleToggle(false)}
          type="button"
          variant="ghost"
        >
          <ChevronDown aria-hidden="true" className="size-3.5 opacity-70" />
          <span>{summary}</span>
        </Button>
        <StepList steps={steps} />
        {children ? (
          <div
            className="grid gap-1.5 max-[680px]:gap-1"
            data-slot="chat-pipeline-extra-detail"
          >
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
        className="min-w-0"
        data-slot="chat-pipeline-steps"
      >
        <Button
          aria-expanded={false}
          aria-label={`Expand Chat Steps, ${label}`}
          className={PIPELINE_SUMMARY_TEXT_CLASS}
          onClick={() => handleToggle(true)}
          type="button"
          variant="ghost"
        >
          <ChevronRight aria-hidden="true" className="size-3.5 opacity-70" />
          <span>{summary}</span>
        </Button>
      </section>
    )
  }

  return (
    <section
      aria-label="Chat Pipeline Steps"
      className="grid min-w-0 gap-1.5 max-[680px]:gap-1"
      data-slot="chat-pipeline-steps"
    >
      <Button
        aria-expanded={true}
        aria-label={`Collapse Chat Steps, ${label}`}
        className={PIPELINE_SUMMARY_TEXT_CLASS}
        onClick={() => handleToggle(false)}
        type="button"
        variant="ghost"
      >
        <ChevronDown aria-hidden="true" className="size-3.5 opacity-70" />
        <span>{summary}</span>
      </Button>
      <StepList steps={steps} />
      {children ? (
        <div
          className="grid gap-1.5 max-[680px]:gap-1"
          data-slot="chat-pipeline-extra-detail"
        >
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
        className="px-0 py-0.5 text-xs text-muted-foreground max-[680px]:text-xs"
        data-slot="chat-pipeline-empty"
        role="status"
      >
        Waiting For Pipeline Steps.
      </p>
    )
  }
  return (
    <ol
      className="grid gap-0.5 text-xs max-[680px]:gap-0.5"
      data-slot="chat-pipeline-step-list"
    >
      {steps.map((step, index) => (
        <li key={`${step.id}-${index}`}>
          <StepRow step={step} />
        </li>
      ))}
    </ol>
  )
}

function StepRow({ step }: { step: ChatStep }) {
  const indented = step.id.includes('.')
  const Icon = iconForStep(step.id)
  const label = stepLabel(step.id)
  const hasUsage = step.usage !== undefined
  const rowClass = cn(
    'flex min-w-0 items-center gap-1.5 py-0.5',
    indented && 'ml-3 border-l-2 border-primary/30 pl-2',
  )

  const main = (
    <>
      <StatusIcon status={step.status} />
      {createElement(Icon, {
        'aria-hidden': true,
        className: 'size-3.5 shrink-0 text-muted-foreground',
      })}
      <span
        className={cn(
          'shrink-0 text-foreground',
          hasUsage &&
            'underline decoration-dotted decoration-muted-foreground/50 underline-offset-2',
        )}
      >
        {label}
      </span>
      <InlineDetailChips step={step} />
      {step.elapsed_ms !== undefined ? (
        <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
          {formatStepDuration(step.elapsed_ms)}
        </span>
      ) : (
        <span className="ml-auto" />
      )}
    </>
  )

  if (!hasUsage) {
    return (
      <div
        aria-busy={step.status === 'start' || undefined}
        className={rowClass}
        data-slot="chat-pipeline-step-row"
      >
        {main}
      </div>
    )
  }

  return (
    <details
      className={cn(indented && 'ml-3 border-l-2 border-primary/30 pl-2')}
      data-slot="chat-pipeline-step-row"
    >
      <summary
        className={cn(
          'flex min-w-0 cursor-pointer list-none items-center gap-1.5 py-0.5 marker:content-none',
          '[&::-webkit-details-marker]:hidden',
        )}
      >
        {main}
      </summary>
      <div
        className="ml-6 flex flex-wrap items-center gap-1 border-l-2 border-primary/25 py-0.5 pl-2 text-[11px] leading-snug text-muted-foreground"
        data-slot="chat-pipeline-step-detail"
      >
        {usageDetailParts(step.usage!).map((part) => (
          <span key={part}>{part}</span>
        ))}
      </div>
    </details>
  )
}

function InlineDetailChips({ step }: { step: ChatStep }) {
  const chips: string[] = []
  const detail = step.detail ?? {}
  // Prefer operator-facing scalars first, then any other short primitives.
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
  // Show model as a compact chip on the row when usage exists (beflow-style).
  if (step.usage?.model && !chips.includes(step.usage.model)) {
    chips.push(step.usage.model)
  }
  if (chips.length === 0) {
    return null
  }
  return (
    <span className="flex min-w-0 flex-wrap items-center gap-1">
      {chips.slice(0, 4).map((chip) => (
        <span
          className="inline-flex max-w-[12rem] truncate rounded-sm bg-muted px-1 py-px text-[10px] font-medium text-muted-foreground"
          data-slot="chat-pipeline-detail-chip"
          key={chip}
        >
          {chip}
        </span>
      ))}
    </span>
  )
}

function StatusIcon({ status }: { status: ChatStep['status'] }) {
  if (status === 'error') {
    return (
      <span className="inline-flex shrink-0" data-slot="chat-pipeline-status">
        <CircleAlert
          aria-hidden="true"
          className="size-3.5 text-destructive"
          data-status={status}
        />
        <span className="sr-only">{statusAccessibleName(status)}</span>
      </span>
    )
  }
  if (status === 'done') {
    return (
      <span className="inline-flex shrink-0" data-slot="chat-pipeline-status">
        <CircleCheck
          aria-hidden="true"
          className="size-3.5 text-emerald-500"
          data-status={status}
        />
        <span className="sr-only">{statusAccessibleName(status)}</span>
      </span>
    )
  }
  return (
    <span className="inline-flex shrink-0" data-slot="chat-pipeline-status">
      <LoaderCircle
        aria-hidden="true"
        className="size-3.5 animate-spin text-muted-foreground"
        data-status={status}
      />
      <span className="sr-only">{statusAccessibleName(status)}</span>
    </span>
  )
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
