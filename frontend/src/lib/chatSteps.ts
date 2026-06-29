export type ChatStepStatus = 'start' | 'done' | 'error'

export type ChatStepUsage = {
  slot: string
  provider: string
  model: string
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  estimated_cost_usd?: number
  cost_source?: string
}

export type ChatStep = {
  id: string
  status: ChatStepStatus
  elapsed_ms?: number
  detail?: Record<string, unknown>
  usage?: ChatStepUsage
}

export type ChatStepEvent = ChatStep

export function applyChatStepEvent(
  steps: ChatStep[],
  event: ChatStepEvent,
): ChatStep[] {
  if (event.status === 'start') {
    return [...steps, { ...event }]
  }

  const nextSteps = [...steps]
  const activeIndex = findLastMatchingStart(nextSteps, event.id)
  if (activeIndex === -1) {
    return [...nextSteps, { ...event }]
  }
  nextSteps[activeIndex] = {
    ...nextSteps[activeIndex],
    ...event,
  }
  return nextSteps
}

export function parseChatStepsFromMetadata(
  metadata: Record<string, unknown> | null,
): ChatStep[] {
  if (metadata === null || !Array.isArray(metadata.steps)) {
    return []
  }
  return metadata.steps
    .map(parseChatStep)
    .filter((step): step is ChatStep => step !== null)
}

export function summarizeCurrentStep(steps: ChatStep[]): {
  elapsed: string
  label: string
  status: ChatStepStatus
} {
  const current =
    [...steps].reverse().find((step) => step.status === 'start') ??
    steps[steps.length - 1]
  if (current === undefined) {
    return {
      elapsed: 'starting',
      label: 'answer',
      status: 'start',
    }
  }
  return {
    elapsed: formatStepDuration(current.elapsed_ms ?? null),
    label: stepLabel(current.id),
    status: current.status,
  }
}

export function formatStepDuration(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'running'
  }
  if (value < 1000) {
    return `${value} ms`
  }
  if (value < 60_000) {
    return `${(value / 1000).toFixed(1)} s`
  }
  const minutes = Math.floor(value / 60_000)
  const seconds = Math.round((value % 60_000) / 1000)
  return `${minutes}m ${seconds}s`
}

export function stepLabel(id: string): string {
  return id.replace(/\./g, ' - ')
}

function findLastMatchingStart(steps: ChatStep[], id: string): number {
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    if (steps[index].id === id && steps[index].status === 'start') {
      return index
    }
  }
  return -1
}

function parseChatStep(value: unknown): ChatStep | null {
  if (!isRecord(value)) {
    return null
  }
  const id = readRequiredString(value, 'id')
  const status = readStepStatus(value.status)
  if (id === null || status === null) {
    return null
  }
  const step: ChatStep = { id, status }
  const elapsedMs = readOptionalNumber(value, 'elapsed_ms')
  if (elapsedMs !== null) {
    step.elapsed_ms = elapsedMs
  }
  const detail = readOptionalRecord(value, 'detail')
  if (detail !== null) {
    step.detail = detail
  }
  const usage = parseChatStepUsage(value.usage)
  if (usage !== null) {
    step.usage = usage
  }
  return step
}

function parseChatStepUsage(value: unknown): ChatStepUsage | null {
  if (!isRecord(value)) {
    return null
  }
  const slot = readRequiredString(value, 'slot')
  const provider = readRequiredString(value, 'provider')
  const model = readRequiredString(value, 'model')
  if (slot === null || provider === null || model === null) {
    return null
  }
  const usage: ChatStepUsage = { model, provider, slot }
  const inputTokens = readOptionalNumber(value, 'input_tokens')
  if (inputTokens !== null) {
    usage.input_tokens = inputTokens
  }
  const outputTokens = readOptionalNumber(value, 'output_tokens')
  if (outputTokens !== null) {
    usage.output_tokens = outputTokens
  }
  const totalTokens = readOptionalNumber(value, 'total_tokens')
  if (totalTokens !== null) {
    usage.total_tokens = totalTokens
  }
  const estimatedCostUsd = readOptionalNumber(value, 'estimated_cost_usd')
  if (estimatedCostUsd !== null) {
    usage.estimated_cost_usd = estimatedCostUsd
  }
  const costSource = readOptionalString(value, 'cost_source')
  if (costSource !== null) {
    usage.cost_source = costSource
  }
  return usage
}

function readStepStatus(value: unknown): ChatStepStatus | null {
  return value === 'start' || value === 'done' || value === 'error'
    ? value
    : null
}

function readRequiredString(
  value: Record<string, unknown>,
  key: string,
): string | null {
  const field = value[key]
  return typeof field === 'string' && field.trim().length > 0 ? field : null
}

function readOptionalString(
  value: Record<string, unknown>,
  key: string,
): string | null {
  const field = value[key]
  return typeof field === 'string' && field.trim().length > 0 ? field : null
}

function readOptionalNumber(
  value: Record<string, unknown>,
  key: string,
): number | null {
  const field = value[key]
  return typeof field === 'number' && Number.isFinite(field) && field >= 0
    ? field
    : null
}

function readOptionalRecord(
  value: Record<string, unknown>,
  key: string,
): Record<string, unknown> | null {
  const field = value[key]
  return isRecord(field) ? field : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
