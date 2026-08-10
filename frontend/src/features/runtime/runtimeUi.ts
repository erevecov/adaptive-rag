import type {
  ProviderConnection,
  ProviderModel,
} from '@/lib/apiClient'

const DEFAULT_RETRIEVAL_LIMIT = 5

export const CHAT_RETRIEVAL_MAX_LIMIT = 50
export const RUNTIME_SLOTS = [
  'chat',
  'dense_embedding',
  'sparse_embedding',
  'rerank',
  'contextualization',
  'vision',
] as const
export const PROVIDER_CONNECTION_CAPABILITIES: readonly string[] = RUNTIME_SLOTS

export type RequestState =
  | 'idle'
  | 'loading'
  | 'succeeded'
  | 'failed'
  | 'canceled'
export type RuntimeSubmodule =
  | 'connections'
  | 'model_catalog'
  | 'global_defaults'
  | 'workspace_overrides'
export type ProviderModelOption = {
  connection_id: string
  model_id: string
}

export function normalizeChatRetrievalLimit(value: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return DEFAULT_RETRIEVAL_LIMIT
  }
  return Math.min(CHAT_RETRIEVAL_MAX_LIMIT, Math.max(1, Math.trunc(parsed)))
}

export function statusClassName(state: RequestState): string {
  return state === 'failed' ? 'status-dot status-dot-error' : 'status-dot'
}

export function runtimeStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Working…'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Saved'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Ready'
}

export function connectionsForCapability(
  connections: ProviderConnection[],
  capability: string,
): ProviderConnection[] {
  return connections.filter((connection) =>
    connection.capabilities.includes(capability),
  )
}

export function missingSyncedModelMessage({
  connectionId,
  modelOptions,
  target,
}: {
  connectionId: string
  modelOptions: ProviderModelOption[]
  target: string
}): string | null {
  const trimmedConnectionId = connectionId.trim()
  if (trimmedConnectionId.length === 0 || modelOptions.length > 0) {
    return null
  }
  const slot = slotLabel(target)
  return (
    `No ${slot} models in the catalog for this connection. ` +
    `Open Model Catalog to sync, or pick a connection that exposes ${slot} models.`
  )
}

/**
 * Warn when a Qwen catalog model’s capabilities need a DashScope service URL
 * but the connection base_url is an OpenAI-compatible chat gateway (e.g. Bailian
 * Token Plan). Those gateways often list/seed rerank+embed models that 404 live.
 */
export function qwenServiceModelEndpointWarning({
  provider,
  baseUrl,
  capabilities,
}: {
  provider: string
  baseUrl: string | null | undefined
  capabilities: readonly string[]
}): string | null {
  if (provider !== 'qwen') {
    return null
  }
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '')
  if (base.length === 0) {
    return null
  }
  const caps = new Set(capabilities)
  const needsRerank = caps.has('rerank')
  const needsDense = caps.has('dense_embedding')
  const needsSparse = caps.has('sparse_embedding')
  if (!needsRerank && !needsDense && !needsSparse) {
    return null
  }

  const isCompatMode = base.includes('/compatible-mode/')
  const isNativeEmbed = base.includes('/services/embeddings/text-embedding')
  const isNativeRerank = base.includes('/services/rerank/text-rerank')
  const isDashscopeApiRoot = /\/api\/v1$/i.test(base) && !isCompatMode

  if (needsSparse && !isNativeEmbed) {
    return (
      'Sparse embeddings need a DashScope native text-embedding URL ' +
      '(…/services/embeddings/…), not an OpenAI-compatible chat base URL.'
    )
  }
  if (needsDense && !isNativeEmbed && isCompatMode) {
    return (
      'This OpenAI-compatible base URL often lacks embedding APIs ' +
      '(e.g. Bailian Token Plan returns 404). Prefer a DashScope embeddings endpoint.'
    )
  }
  if (needsRerank && !isNativeRerank && !isDashscopeApiRoot) {
    return (
      'Rerank needs a DashScope API root (…/api/v1) or native text-rerank URL. ' +
      'OpenAI-compatible chat gateways typically return 404 for qwen3-rerank.'
    )
  }
  return null
}

export function connectionForId(
  connections: ProviderConnection[],
  connectionId: string,
): ProviderConnection | null {
  const trimmed = connectionId.trim()
  if (trimmed.length === 0) {
    return null
  }
  return (
    connections.find((connection) => connection.connection_id === trimmed) ??
    null
  )
}

/** Slot/catalog warning for a selected connection + model capability set. */
export function selectedSlotEndpointWarning({
  connections,
  connectionId,
  modelId,
  providerModels,
  capability,
}: {
  connections: ProviderConnection[]
  connectionId: string
  modelId: string
  providerModels: ProviderModel[]
  capability: string
}): string | null {
  const connection = connectionForId(connections, connectionId)
  if (connection === null || modelId.trim().length === 0) {
    return null
  }
  const model = providerModels.find(
    (row) =>
      row.connection_id === connection.connection_id &&
      row.model_id === modelId.trim(),
  )
  const capabilities =
    model?.capabilities ??
    (capability.trim().length > 0 ? [capability.trim()] : [])
  return qwenServiceModelEndpointWarning({
    provider: connection.provider,
    baseUrl: connection.base_url,
    capabilities,
  })
}

export function providerModelOptions({
  capability,
  configuredModels = [],
  connectionId,
  providerModels,
  selectedModelId,
}: {
  capability: string
  configuredModels?: ProviderModelOption[]
  connectionId: string
  providerModels: ProviderModel[]
  selectedModelId: string
}): ProviderModelOption[] {
  if (connectionId.length === 0) {
    return []
  }
  const options: ProviderModelOption[] = providerModels
    .filter(
      (model) =>
        model.connection_id === connectionId &&
        model.capabilities.includes(capability),
    )
    .map((model) => ({
      connection_id: model.connection_id,
      model_id: model.model_id,
    }))
  for (const model of configuredModels) {
    if (model.connection_id === connectionId) {
      options.push(model)
    }
  }
  if (selectedModelId.trim().length > 0) {
    options.push({
      connection_id: connectionId,
      model_id: selectedModelId.trim(),
    })
  }
  return uniqueProviderModelOptions(options)
}

function uniqueProviderModelOptions(
  options: ProviderModelOption[],
): ProviderModelOption[] {
  const seen = new Set<string>()
  const unique: ProviderModelOption[] = []
  for (const option of options) {
    const key = `${option.connection_id}\u0000${option.model_id}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    unique.push(option)
  }
  return unique
}

export function connectionOptionLabel(connection: ProviderConnection): string {
  const detail = `${providerLabel(connection.provider)}/${connectionTypeLabel(connection.connection_type)}`
  const label = metadataLabel(connection.metadata)
  if (label === null) {
    return `${connection.connection_id} (${detail})`
  }
  return `${label} (${detail})`
}

export function providerLabel(provider: string): string {
  if (provider === 'local_openai_compatible') {
    return 'Local OpenAI-compatible'
  }
  if (provider === 'qwen') {
    return 'Qwen'
  }
  if (provider === 'fake') {
    return 'Fake'
  }
  return titleCaseToken(provider)
}

export function connectionTypeLabel(connectionType: string): string {
  if (connectionType === 'hosted') {
    return 'Hosted'
  }
  if (connectionType === 'local') {
    return 'Local'
  }
  if (connectionType === 'fake') {
    return 'Fake'
  }
  return titleCaseToken(connectionType)
}

export function slotLabel(slot: string): string {
  if (slot === 'chat') {
    return 'Chat'
  }
  if (slot === 'dense_embedding') {
    return 'Dense Embedding'
  }
  if (slot === 'sparse_embedding') {
    return 'Sparse Embedding'
  }
  if (slot === 'rerank') {
    return 'Rerank'
  }
  if (slot === 'contextualization') {
    return 'Contextualization'
  }
  if (slot === 'vision') {
    return 'Vision'
  }
  return titleCaseToken(slot)
}

export function titleCaseToken(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

export function metadataLabel(
  metadata: Record<string, unknown> | null,
): string | null {
  const label = metadata?.label
  return typeof label === 'string' && label.trim().length > 0
    ? label.trim()
    : null
}

/**
 * Compact summary of provider_model_catalog.pricing_json for Model Catalog rows.
 *
 * Backend shape (Alibaba list sync) uses one of:
 * - Token models: input/output/thinking *_per_million_tokens_usd
 * - Image models: usd_per_image
 * - TTS: input_per_10k_characters_usd
 * Missing or empty → No pricing.
 */
export type ProviderModelPricingSummary = {
  hasPricing: boolean
  /** e.g. "In $0.40 · Out $1.20 /1M" or "$0.03 /image" */
  summary: string | null
  badgeLabel: 'Priced' | 'No pricing'
}

export function formatProviderModelPricing(
  pricing: Record<string, unknown> | null | undefined,
): ProviderModelPricingSummary {
  if (pricing == null || typeof pricing !== 'object') {
    return { hasPricing: false, summary: null, badgeLabel: 'No pricing' }
  }

  const perImage = readNonNegativeNumber(pricing.usd_per_image)
  if (perImage !== null) {
    return {
      hasPricing: true,
      summary: `${formatUsdAmount(perImage)} /image`,
      badgeLabel: 'Priced',
    }
  }

  const per10kChars = readNonNegativeNumber(
    pricing.input_per_10k_characters_usd,
  )
  if (per10kChars !== null) {
    return {
      hasPricing: true,
      summary: `${formatUsdAmount(per10kChars)} /10k chars`,
      badgeLabel: 'Priced',
    }
  }

  const input = readNonNegativeNumber(pricing.input_per_million_tokens_usd)
  const output = readNonNegativeNumber(pricing.output_per_million_tokens_usd)
  const thinking = readNonNegativeNumber(
    pricing.output_thinking_per_million_tokens_usd,
  )

  if (input === null && output === null && thinking === null) {
    return { hasPricing: false, summary: null, badgeLabel: 'No pricing' }
  }

  const parts: string[] = []
  if (input !== null) {
    parts.push(`In ${formatUsdAmount(input)}`)
  }
  if (output !== null) {
    parts.push(`Out ${formatUsdAmount(output)}`)
  }
  if (thinking !== null) {
    parts.push(`Think ${formatUsdAmount(thinking)}`)
  }

  return {
    hasPricing: true,
    summary: `${parts.join(' · ')} /1M`,
    badgeLabel: 'Priced',
  }
}

function readNonNegativeNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return value
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed >= 0) {
      return parsed
    }
  }
  return null
}

function formatUsdAmount(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value)
}
