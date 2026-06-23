type JsonObject = Record<string, unknown>

export type Project = {
  id: string
  name: string
  embedding_mode: string
  retrieval_contextualization_enabled: boolean
  budget_config_json: JsonObject | null
  created_at: string
  updated_at: string
}

export type ProjectCreateBody = {
  name: string
  embedding_mode?: string
  retrieval_contextualization_enabled?: boolean
  budget_config_json?: JsonObject | null
}

export type ProjectListResponse = {
  items: Project[]
}

export type Source = {
  id: string
  project_id: string
  source_type: string
  external_id: string
  tags: string[] | null
  extra_metadata: JsonObject | null
  created_at: string
  updated_at: string
}

export type SourceCreateBody = {
  source_type: string
  external_id: string
  tags?: string[] | null
  extra_metadata?: JsonObject | null
}

export type SourceListParams = {
  source_type?: string | null
  external_id?: string | null
  tag?: string | null
}

export type SourceListResponse = {
  items: Source[]
}

export type RetrievalMetadataFilter = {
  source_id?: string | null
  document_id?: string | null
  source_type?: string | null
  tags?: string[]
  source_created_at_from?: string | null
  source_created_at_to?: string | null
  document_created_at_from?: string | null
  document_created_at_to?: string | null
}

export type RetrievalCitation = {
  source_id: string
  source_type: string
  source_external_id: string
  source_tags: string[]
  source_extra_metadata: JsonObject | null
  document_id: string
  document_stable_id: string
  document_version_id: string
  document_version_number: number
  chunk_id: string
  char_start: number
  char_end: number
  snippet: string
  section_metadata: JsonObject | null
}

export type RetrievalResult = {
  chunk_id: string
  distance: number
  score: number
  citation: RetrievalCitation
  embedding_metadata: JsonObject | null
  rerank_metadata?: JsonObject | null
}

export type ChatRequestBody = {
  message: string
  retrieval_limit?: number
  metadata_filter?: RetrievalMetadataFilter | null
}

export type ChatToolCall = {
  name: string
  query: string
  limit: number
  result_count: number
}

export type ChatResponseBody = {
  answer: string
  citations: RetrievalResult[]
  tool_calls: ChatToolCall[]
  session_id: string | null
}

export type ChatStreamEvent =
  | {
      event: 'session_started'
      data: { session_id: string }
    }
  | {
      event: 'tool_call'
      data: ChatToolCall
    }
  | {
      event: 'answer_delta'
      data: { text: string }
    }
  | {
      event: 'heartbeat'
      data: { elapsed_ms: number }
    }
  | {
      event: 'final'
      data: ChatResponseBody
    }
  | {
      event: 'error'
      data: { detail: string }
    }

export type ChatStreamHandlers = {
  onAnswerDelta?(text: string): void
  onErrorEvent?(detail: string): void
  onEvent?(event: ChatStreamEvent): void
  onHeartbeat?(elapsedMs: number): void
  onSessionStarted?(sessionId: string): void
  onToolCall?(toolCall: ChatToolCall): void
}

export type ChatStreamOptions = {
  signal?: AbortSignal
}

export type ChatSessionStatus = 'running' | 'succeeded' | 'failed' | string

export type ChatSessionSummary = {
  session_id: string
  status: ChatSessionStatus
  created_at: string
  updated_at: string
  model_config: JsonObject | null
  prompt_version: string | null
  message_count: number
  tool_call_count: number
  retrieval_run_count: number
  provider_usage_count: number
  total_estimated_cost_usd: number
  error_message: string | null
}

export type ChatSessionListResponse = {
  items: ChatSessionSummary[]
  next_cursor: string | null
}

export type ChatSessionListParams = {
  status?: ChatSessionStatus
  limit?: number
  cursor?: string | null
}

export type ChatObservabilitySummaryParams = {
  created_at_from?: string | null
  created_at_to?: string | null
  status?: ChatSessionStatus | null
}

export type ChatObservabilityFilters = {
  created_at_from: string | null
  created_at_to: string | null
  status: ChatSessionStatus | null
}

export type ChatObservabilitySessionSummary = {
  total: number
  by_status: Record<string, number>
}

export type ChatObservabilityLatencySummary = {
  count: number
  min: number | null
  avg: number | null
  p50: number | null
  p95: number | null
  max: number | null
}

export type ChatObservabilityProviderUsageGroup = {
  operation: string
  provider: string
  model: string
  record_count: number
  estimated_cost_usd: number | null
  input_tokens: number | null
  output_tokens: number | null
  total_tokens: number | null
  input_count: number | null
  latency_ms: ChatObservabilityLatencySummary
}

export type ChatObservabilityProviderUsageSummary = {
  total_records: number
  total_estimated_cost_usd: number
  missing_cost_count: number
  groups: ChatObservabilityProviderUsageGroup[]
}

export type ChatObservabilityErrorMessage = {
  message: string
  count: number
}

export type ChatObservabilityErrorSummary = {
  session_error_count: number
  provider_error_count: number
  top_messages: ChatObservabilityErrorMessage[]
}

export type ChatObservabilitySummary = {
  project_id: string
  filters: ChatObservabilityFilters
  sessions: ChatObservabilitySessionSummary
  provider_usage: ChatObservabilityProviderUsageSummary
  errors: ChatObservabilityErrorSummary
}

export type ChatSessionMetadata = {
  session_id: string
  status: ChatSessionStatus
  created_at: string
  updated_at: string
  model_config: JsonObject | null
  prompt_version: string | null
  error_message: string | null
}

export type ChatHistoryMessage = {
  message_id: string
  role: string
  content: string
  metadata: JsonObject | null
  created_at: string
}

export type ChatHistoryToolCall = {
  tool_call_id: string
  tool_name: string
  arguments: JsonObject | null
  result_summary: JsonObject | null
  status: string
  latency_ms: number | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type ChatHistoryRetrievedChunk = {
  retrieved_chunk_id: string
  chunk_id: string
  rank: number
  dense_score: number | null
  lexical_score: number | null
  rrf_score: number | null
  rerank_score: number | null
  citation: JsonObject
  created_at: string
}

export type ChatHistoryRetrievalRun = {
  retrieval_run_id: string
  tool_call_id: string | null
  query: string
  strategy: string
  top_k: number
  used_rerank: boolean
  filters: JsonObject | null
  latency_ms: number | null
  error_message: string | null
  created_at: string
  retrieved_chunks: ChatHistoryRetrievedChunk[]
}

export type ChatHistoryProviderUsage = {
  provider_usage_id: string
  operation: string
  provider: string
  model: string
  status: string
  usage_source: string
  input_tokens: number | null
  output_tokens: number | null
  total_tokens: number | null
  input_count: number | null
  estimated_cost_usd: number | null
  currency: string | null
  latency_ms: number | null
  provider_request_id: string | null
  error_message: string | null
  created_at: string
}

export type ChatSessionDetailResponse = {
  session: ChatSessionMetadata
  messages: ChatHistoryMessage[]
  tool_calls: ChatHistoryToolCall[]
  retrieval_runs: ChatHistoryRetrievalRun[]
  provider_usage: ChatHistoryProviderUsage[]
}

export class ApiClientError extends Error {
  readonly detail: unknown
  readonly status: number

  constructor(message: string, options: { detail: unknown; status: number }) {
    super(message)
    this.name = 'ApiClientError'
    this.detail = options.detail
    this.status = options.status
  }
}

export type ApiClient = {
  createProject(body: ProjectCreateBody): Promise<Project>
  listProjects(): Promise<ProjectListResponse>
  getProject(projectId: string): Promise<Project>
  createSource(projectId: string, body: SourceCreateBody): Promise<Source>
  listSources(
    projectId: string,
    params?: SourceListParams,
  ): Promise<SourceListResponse>
  getSource(projectId: string, sourceId: string): Promise<Source>
  askChat(projectId: string, body: ChatRequestBody): Promise<ChatResponseBody>
  askChatStream(
    projectId: string,
    body: ChatRequestBody,
    handlers?: ChatStreamHandlers,
    options?: ChatStreamOptions,
  ): Promise<ChatResponseBody>
  listChatSessions(
    projectId: string,
    params?: ChatSessionListParams,
  ): Promise<ChatSessionListResponse>
  getChatSession(
    projectId: string,
    sessionId: string,
  ): Promise<ChatSessionDetailResponse>
  getChatObservabilitySummary(
    projectId: string,
    params?: ChatObservabilitySummaryParams,
  ): Promise<ChatObservabilitySummary>
}

export type ApiClientOptions = {
  baseUrl: string
  fetch?: typeof fetch
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = options.baseUrl.replace(/\/+$/, '')
  const fetchImpl = options.fetch ?? globalThis.fetch

  return {
    createProject(body) {
      return requestJson<Project>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects`,
      })
    },
    listProjects() {
      return requestJson<ProjectListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects`,
      })
    },
    getProject(projectId) {
      return requestJson<Project>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}`,
      })
    },
    createSource(projectId, body) {
      return requestJson<Source>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}/sources`,
      })
    },
    listSources(projectId, params = {}) {
      const url = new URL(
        `${baseUrl}/projects/${encodePathSegment(projectId)}/sources`,
      )
      appendSearchParam(url, 'source_type', params.source_type)
      appendSearchParam(url, 'external_id', params.external_id)
      appendSearchParam(url, 'tag', params.tag)

      return requestJson<SourceListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    getSource(projectId, sourceId) {
      return requestJson<Source>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/sources/${encodePathSegment(sourceId)}`,
      })
    },
    askChat(projectId, body) {
      return requestJson<ChatResponseBody>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}/chat`,
      })
    },
    askChatStream(projectId, body, handlers = {}, requestOptions = {}) {
      return requestChatStream(fetchImpl, {
        body,
        handlers,
        signal: requestOptions.signal,
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}/chat/stream`,
      })
    },
    getChatSession(projectId, sessionId) {
      return requestJson<ChatSessionDetailResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/chat/sessions/${encodePathSegment(sessionId)}`,
      })
    },
    getChatObservabilitySummary(projectId, params = {}) {
      const url = new URL(
        `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/chat/observability/summary`,
      )
      appendSearchParam(url, 'created_at_from', params.created_at_from)
      appendSearchParam(url, 'created_at_to', params.created_at_to)
      appendSearchParam(url, 'status', params.status)

      return requestJson<ChatObservabilitySummary>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    listChatSessions(projectId, params = {}) {
      const url = new URL(
        `${baseUrl}/projects/${encodePathSegment(projectId)}/chat/sessions`,
      )
      appendSearchParam(url, 'status', params.status)
      appendSearchParam(url, 'limit', params.limit)
      appendSearchParam(url, 'cursor', params.cursor)

      return requestJson<ChatSessionListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
  }
}

function appendSearchParam(
  url: URL,
  key: string,
  value: number | string | null | undefined,
): void {
  if (value === undefined || value === null) {
    return
  }
  if (typeof value === 'string' && value.trim().length === 0) {
    return
  }
  url.searchParams.append(key, String(value))
}

function encodePathSegment(value: string): string {
  return encodeURIComponent(value)
}

async function requestJson<T>(
  fetchImpl: typeof fetch,
  options: {
    body?: unknown
    method: 'GET' | 'POST'
    url: string
  },
): Promise<T> {
  const response = await fetchImpl(options.url, {
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    headers:
      options.body === undefined ? undefined : { 'content-type': 'application/json' },
    method: options.method,
  })
  const payload = await readJson(response)

  if (!response.ok) {
    const detail = getErrorDetail(payload)
    throw new ApiClientError(
      typeof detail === 'string'
        ? detail
        : `Request failed with status ${response.status}`,
      {
        detail,
        status: response.status,
      },
    )
  }

  return payload as T
}

async function requestChatStream(
  fetchImpl: typeof fetch,
  options: {
    body: ChatRequestBody
    handlers: ChatStreamHandlers
    signal?: AbortSignal
    url: string
  },
): Promise<ChatResponseBody> {
  const response = await fetchImpl(options.url, {
    body: JSON.stringify(options.body),
    headers: {
      accept: 'text/event-stream',
      'content-type': 'application/json',
    },
    method: 'POST',
    signal: options.signal,
  })

  if (!response.ok) {
    const payload = await readJson(response)
    const detail = getErrorDetail(payload)
    throw new ApiClientError(
      typeof detail === 'string'
        ? detail
        : `Request failed with status ${response.status}`,
      {
        detail,
        status: response.status,
      },
    )
  }

  if (response.body === null) {
    throw new ApiClientError('Chat stream response body is empty', {
      detail: 'Chat stream response body is empty',
      status: response.status,
    })
  }

  return readChatStream(response.body, options.handlers, response.status)
}

async function readChatStream(
  body: ReadableStream<Uint8Array>,
  handlers: ChatStreamHandlers,
  status: number,
): Promise<ChatResponseBody> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResponse: ChatResponseBody | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const result = consumeSseBuffer(buffer, handlers, status, finalResponse)
    buffer = result.buffer
    finalResponse = result.finalResponse
  }

  if (buffer.trim().length > 0) {
    const event = parseSseBlock(buffer)
    if (event !== null) {
      const handledResponse = handleChatStreamEvent(event, handlers, status)
      if (handledResponse !== null) {
        finalResponse = handledResponse
      }
    }
  }

  if (finalResponse === null) {
    throw new ApiClientError('Chat stream ended before final event', {
      detail: 'Chat stream ended before final event',
      status,
    })
  }

  return finalResponse
}

function consumeSseBuffer(
  buffer: string,
  handlers: ChatStreamHandlers,
  status: number,
  finalResponse: ChatResponseBody | null,
): {
  buffer: string
  finalResponse: ChatResponseBody | null
} {
  let remaining = buffer
  let nextFinalResponse = finalResponse

  while (true) {
    const separatorIndex = remaining.indexOf('\n\n')
    if (separatorIndex === -1) {
      break
    }
    const block = remaining.slice(0, separatorIndex)
    remaining = remaining.slice(separatorIndex + 2)
    const event = parseSseBlock(block)
    if (event !== null) {
      const handledResponse = handleChatStreamEvent(event, handlers, status)
      if (handledResponse !== null) {
        nextFinalResponse = handledResponse
      }
    }
  }

  return {
    buffer: remaining,
    finalResponse: nextFinalResponse,
  }
}

function parseSseBlock(block: string): ChatStreamEvent | null {
  let eventName = ''
  const dataLines: string[] = []

  for (const rawLine of block.split(/\r?\n/)) {
    if (rawLine.length === 0 || rawLine.startsWith(':')) {
      continue
    }
    const separatorIndex = rawLine.indexOf(':')
    const field =
      separatorIndex === -1 ? rawLine : rawLine.slice(0, separatorIndex)
    let value = separatorIndex === -1 ? '' : rawLine.slice(separatorIndex + 1)
    if (value.startsWith(' ')) {
      value = value.slice(1)
    }
    if (field === 'event') {
      eventName = value
    }
    if (field === 'data') {
      dataLines.push(value)
    }
  }

  if (eventName.length === 0 && dataLines.length === 0) {
    return null
  }

  const data = parseJsonObject(dataLines.join('\n') || '{}')
  return toChatStreamEvent(eventName, data)
}

function handleChatStreamEvent(
  event: ChatStreamEvent,
  handlers: ChatStreamHandlers,
  status: number,
): ChatResponseBody | null {
  handlers.onEvent?.(event)

  if (event.event === 'session_started') {
    handlers.onSessionStarted?.(event.data.session_id)
    return null
  }
  if (event.event === 'tool_call') {
    handlers.onToolCall?.(event.data)
    return null
  }
  if (event.event === 'answer_delta') {
    handlers.onAnswerDelta?.(event.data.text)
    return null
  }
  if (event.event === 'heartbeat') {
    handlers.onHeartbeat?.(event.data.elapsed_ms)
    return null
  }
  if (event.event === 'error') {
    handlers.onErrorEvent?.(event.data.detail)
    throw new ApiClientError(event.data.detail, {
      detail: event.data.detail,
      status,
    })
  }
  return event.data
}

function toChatStreamEvent(
  eventName: string,
  data: JsonObject,
): ChatStreamEvent {
  if (eventName === 'session_started') {
    return {
      event: eventName,
      data: { session_id: readString(data, 'session_id') },
    }
  }
  if (eventName === 'tool_call') {
    return {
      event: eventName,
      data: {
        limit: readNumber(data, 'limit'),
        name: readString(data, 'name'),
        query: readString(data, 'query'),
        result_count: readNumber(data, 'result_count'),
      },
    }
  }
  if (eventName === 'answer_delta') {
    return {
      event: eventName,
      data: { text: readString(data, 'text') },
    }
  }
  if (eventName === 'heartbeat') {
    return {
      event: eventName,
      data: { elapsed_ms: readNumber(data, 'elapsed_ms') },
    }
  }
  if (eventName === 'final') {
    return {
      event: eventName,
      data: data as ChatResponseBody,
    }
  }
  if (eventName === 'error') {
    return {
      event: eventName,
      data: { detail: readString(data, 'detail') },
    }
  }
  throw new Error(`Unknown chat stream event: ${eventName}`)
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.length === 0) {
    return null
  }
  return JSON.parse(text) as unknown
}

function parseJsonObject(text: string): JsonObject {
  const value = JSON.parse(text) as unknown
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Chat stream event data must be a JSON object')
  }
  return value as JsonObject
}

function getErrorDetail(payload: unknown): unknown {
  if (
    payload !== null &&
    typeof payload === 'object' &&
    'detail' in payload
  ) {
    return (payload as { detail: unknown }).detail
  }
  return payload
}

function readNumber(value: JsonObject, key: string): number {
  const field = value[key]
  if (typeof field !== 'number') {
    throw new Error(`Chat stream event field ${key} must be a number`)
  }
  return field
}

function readString(value: JsonObject, key: string): string {
  const field = value[key]
  if (typeof field !== 'string') {
    throw new Error(`Chat stream event field ${key} must be a string`)
  }
  return field
}
