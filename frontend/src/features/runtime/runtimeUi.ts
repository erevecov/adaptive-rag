import type { ProviderConnection, ProviderModel } from '@/lib/apiClient'

const DEFAULT_RETRIEVAL_LIMIT = 5

export const CHAT_RETRIEVAL_MAX_LIMIT = 50
export const RUNTIME_SLOTS = [
  'chat',
  'dense_embedding',
  'sparse_embedding',
  'rerank',
  'contextualization',
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
  | 'project_overrides'
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
    return 'Refreshing'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Saved'
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
  return `Sync models for ${trimmedConnectionId} before saving ${target}.`
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
  const label = metadataLabel(connection.metadata)
  if (label === null) {
    return `${connection.connection_id} (${connection.provider}/${connection.connection_type})`
  }
  return `${label} (${connection.provider}/${connection.connection_type})`
}

export function metadataLabel(
  metadata: Record<string, unknown> | null,
): string | null {
  const label = metadata?.label
  return typeof label === 'string' && label.trim().length > 0
    ? label.trim()
    : null
}
