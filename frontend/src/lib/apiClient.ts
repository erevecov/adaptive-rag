type JsonObject = Record<string, unknown>

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
  askChat(projectId: string, body: ChatRequestBody): Promise<ChatResponseBody>
  listChatSessions(
    projectId: string,
    params?: ChatSessionListParams,
  ): Promise<ChatSessionListResponse>
  getChatSession(
    projectId: string,
    sessionId: string,
  ): Promise<ChatSessionDetailResponse>
}

export type ApiClientOptions = {
  baseUrl: string
  fetch?: typeof fetch
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = options.baseUrl.replace(/\/+$/, '')
  const fetchImpl = options.fetch ?? globalThis.fetch

  return {
    askChat(projectId, body) {
      return requestJson<ChatResponseBody>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}/chat`,
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

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.length === 0) {
    return null
  }
  return JSON.parse(text) as unknown
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
