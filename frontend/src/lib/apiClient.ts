import type {
  ChatStep,
  ChatStepEvent,
  ChatStepStatus,
  ChatStepUsage,
} from './chatSteps'

type JsonObject = Record<string, unknown>

export type Project = {
  id: string
  name: string
  embedding_mode: string
  retrieval_contextualization_enabled: boolean
  budget_config_json: JsonObject | null
  access_role?: string | null
  can_access?: boolean
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

export type CurrentUser = {
  id: string | null
  login: string
  display_name: string
  system_role: string
  is_bootstrap: boolean
  last_project_id: string | null
}

export type CurrentUserPreferencesBody = {
  last_project_id: string | null
}

export type User = {
  id: string
  login: string
  display_name: string
  system_role: string
  is_active: boolean
  last_project_id: string | null
  created_at: string
  updated_at: string
}

export type UserCreateBody = {
  login: string
  display_name: string
  system_role?: string
  access_token?: string | null
  is_active?: boolean
}

export type UserListResponse = {
  items: User[]
}

export type ProjectMembership = {
  id: string
  project_id: string
  user_id: string
  role: string
  created_at: string
  updated_at: string
}

export type ProjectMembershipUpsertBody = {
  role: string
}

export type ProjectMembershipListResponse = {
  items: ProjectMembership[]
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

export type IngestionJob = {
  id: string
  project_id: string
  job_type: string
  status: string
  priority: number
  payload_json: JsonObject | null
  attempts: number
  max_attempts: number
  run_after: string
  locked_by: string | null
  locked_until: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export type IngestionJobEvent = {
  id: string
  project_id: string
  job_id: string
  event_type: string
  message: string | null
  extra_metadata: JsonObject | null
  created_at: string
}

export type EnqueueIngestionJobBody = {
  priority?: number
  max_attempts?: number
}

export type IngestionJobListParams = {
  source_id?: string | null
  status?: string | null
  job_type?: string | null
}

export type IngestionJobListResponse = {
  items: IngestionJob[]
}

export type IngestionJobDetailResponse = {
  job: IngestionJob
  events: IngestionJobEvent[]
}

export type RetryIngestionJobBody = {
  reset_attempts?: boolean
}

export type RunNextIngestionJobBody = {
  worker_id?: string | null
  lease_seconds?: number
}

export type IngestionRunResponse = {
  status: string
  project_id: string
  worker_id: string
  job_id: string | null
  source_id: string | null
  document_id: string | null
  document_version_id: string | null
  created_document_version: boolean | null
  error_message: string | null
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
  query?: string
  limit?: number
  result_count?: number
  arguments?: JsonObject
  result_summary?: JsonObject
}

export type ChatResponseBody = {
  answer: string
  citations: RetrievalResult[]
  tool_calls: ChatToolCall[]
  session_id: string | null
  steps?: ChatStep[]
}

export type ChatStreamEvent =
  | {
      event: 'session_started'
      data: { session_id: string }
    }
  | {
      event: 'step'
      data: ChatStepEvent
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
  onStep?(step: ChatStepEvent): void
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
  title: string | null
  title_is_custom: boolean
  archived_at: string | null
  model_config: JsonObject | null
  prompt_version: string | null
  message_count: number
  tool_call_count: number
  retrieval_run_count: number
  provider_usage_count: number
  total_estimated_cost_usd: number
  error_message: string | null
  has_pending_training: boolean
  has_approved_training: boolean
}

export type ChatSessionListResponse = {
  items: ChatSessionSummary[]
  next_cursor: string | null
}

export type ChatSessionListParams = {
  status?: ChatSessionStatus
  archived?: boolean
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
  title: string | null
  title_is_custom: boolean
  archived_at: string | null
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

export type KnowledgeProposal = {
  id: string
  project_id: string
  submitted_by_user_id: string | null
  origin_session_id: string | null
  origin_message_id: string | null
  approved_source_id: string | null
  reviewed_by_user_id: string | null
  status: string
  proposed_text: string
  refined_text: string | null
  review_note: string | null
  created_at: string
  updated_at: string
  reviewed_at: string | null
}

export type KnowledgeProposalSubmitBody = {
  proposed_text: string
  origin_session_id?: string | null
  origin_message_id?: string | null
}

export type KnowledgeProposalListParams = {
  status?: string | null
}

export type KnowledgeProposalListResponse = {
  items: KnowledgeProposal[]
}

export type KnowledgeProposalRefineBody = {
  refined_text: string
}

export type KnowledgeProposalApproveBody = {
  refined_text?: string | null
  review_note?: string | null
}

export type KnowledgeProposalRejectBody = {
  reason: string
}

export type ProviderSecretStatus = {
  connection_id: string
  secret_name: string
  configured: boolean
  updated_at: string | null
  last_four: string | null
  fingerprint: string | null
}

export type ProviderConnection = {
  connection_id: string
  provider: string
  connection_type: string
  base_url: string | null
  capabilities: string[]
  metadata: JsonObject | null
  secrets: ProviderSecretStatus[]
  created_at: string
  updated_at: string
}

export type ProviderConnectionListResponse = {
  items: ProviderConnection[]
}

export type ProviderConnectionUpsertBody = {
  provider: string
  connection_type: string
  base_url?: string | null
  capabilities: string[]
  metadata?: JsonObject | null
  api_key?: string | null
}

export type ProviderModel = {
  connection_id: string
  model_id: string
  capabilities: string[]
  metadata: JsonObject | null
  pricing: JsonObject | null
  last_seen_at: string
  created_at: string
  updated_at: string
}

export type ProviderModelListParams = {
  connection_id?: string | null
  capability?: string | null
}

export type ProviderModelListResponse = {
  items: ProviderModel[]
}

export type ProviderModelSyncResponse = {
  connection_id: string
  synced_count: number
  items: ProviderModel[]
}

export type ProviderSecretUpsertBody = {
  value: string
}

export type RuntimeSlotDefault = {
  slot: string
  connection_id: string
  model_id: string
  parameters: JsonObject | null
  created_at: string
  updated_at: string
}

export type RuntimeSlotDefaultListResponse = {
  items: RuntimeSlotDefault[]
}

export type RuntimeSlotDefaultUpsertBody = {
  connection_id: string
  model_id: string
  parameters?: JsonObject | null
}

export type ChatModel = {
  connection_id: string
  model_id: string
  is_default: boolean
  parameters: JsonObject | null
  created_at: string
  updated_at: string
}

export type ChatModelListResponse = {
  items: ChatModel[]
}

export type ChatModelUpsertBody = {
  connection_id: string
  model_id: string
  make_default?: boolean
  parameters?: JsonObject | null
}

export type ChatRetrievalSettings = {
  retrieval_limit: number
  rerank_enabled: boolean
  rerank_candidate_limit: number
  max_limit: number
}

export type ChatRetrievalSettingsUpsertBody = {
  retrieval_limit: number
  rerank_enabled: boolean
  rerank_candidate_limit: number
}

export type DeleteResponse = {
  deleted: boolean
}

export type ProjectRuntimeSlot = {
  slot: string
  source: string
  connection_id: string
  model_id: string
  parameters: JsonObject | null
}

export type ProjectChatModel = {
  connection_id: string
  model_id: string
  is_default: boolean
  source: string
  parameters: JsonObject | null
}

export type ProjectChatRetrievalSettings = ChatRetrievalSettings & {
  source: string
}

export type ProjectRuntimeSettings = {
  project_id: string
  slots: ProjectRuntimeSlot[]
  chat_models: ProjectChatModel[]
  chat_retrieval: ProjectChatRetrievalSettings
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
  getCurrentUser(): Promise<CurrentUser>
  updateCurrentUserPreferences(
    body: CurrentUserPreferencesBody,
  ): Promise<CurrentUser>
  createUser(body: UserCreateBody): Promise<User>
  listUsers(): Promise<UserListResponse>
  listProjectMemberships(
    projectId: string,
  ): Promise<ProjectMembershipListResponse>
  upsertProjectMembership(
    projectId: string,
    userId: string,
    body: ProjectMembershipUpsertBody,
  ): Promise<ProjectMembership>
  createProject(body: ProjectCreateBody): Promise<Project>
  listProjects(): Promise<ProjectListResponse>
  getProject(projectId: string): Promise<Project>
  createSource(projectId: string, body: SourceCreateBody): Promise<Source>
  listSources(
    projectId: string,
    params?: SourceListParams,
  ): Promise<SourceListResponse>
  getSource(projectId: string, sourceId: string): Promise<Source>
  enqueueIngestionJob(
    projectId: string,
    sourceId: string,
    body?: EnqueueIngestionJobBody,
  ): Promise<IngestionJob>
  listIngestionJobs(
    projectId: string,
    params?: IngestionJobListParams,
  ): Promise<IngestionJobListResponse>
  getIngestionJob(
    projectId: string,
    jobId: string,
  ): Promise<IngestionJobDetailResponse>
  retryIngestionJob(
    projectId: string,
    jobId: string,
    body?: RetryIngestionJobBody,
  ): Promise<IngestionJob>
  runNextIngestionJob(
    projectId: string,
    body?: RunNextIngestionJobBody,
  ): Promise<IngestionRunResponse>
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
  updateChatSessionTitle(
    projectId: string,
    sessionId: string,
    title: string,
  ): Promise<{ session_id: string; title: string; title_is_custom: boolean }>
  archiveChatSession(projectId: string, sessionId: string): Promise<void>
  unarchiveChatSession(projectId: string, sessionId: string): Promise<void>
  getChatObservabilitySummary(
    projectId: string,
    params?: ChatObservabilitySummaryParams,
  ): Promise<ChatObservabilitySummary>
  submitKnowledgeProposal(
    projectId: string,
    body: KnowledgeProposalSubmitBody,
  ): Promise<KnowledgeProposal>
  listKnowledgeProposals(
    projectId: string,
    params?: KnowledgeProposalListParams,
  ): Promise<KnowledgeProposalListResponse>
  refineKnowledgeProposal(
    projectId: string,
    proposalId: string,
    body: KnowledgeProposalRefineBody,
  ): Promise<KnowledgeProposal>
  approveKnowledgeProposal(
    projectId: string,
    proposalId: string,
    body: KnowledgeProposalApproveBody,
  ): Promise<KnowledgeProposal>
  rejectKnowledgeProposal(
    projectId: string,
    proposalId: string,
    body: KnowledgeProposalRejectBody,
  ): Promise<KnowledgeProposal>
  listProviderConnections(): Promise<ProviderConnectionListResponse>
  createProviderConnection(
    body: ProviderConnectionUpsertBody,
  ): Promise<ProviderConnection>
  upsertProviderConnection(
    connectionId: string,
    body: ProviderConnectionUpsertBody,
  ): Promise<ProviderConnection>
  deleteProviderConnection(connectionId: string): Promise<DeleteResponse>
  listProviderModels(
    params?: ProviderModelListParams,
  ): Promise<ProviderModelListResponse>
  syncProviderModels(connectionId: string): Promise<ProviderModelSyncResponse>
  upsertProviderSecret(
    connectionId: string,
    secretName: string,
    body: ProviderSecretUpsertBody,
  ): Promise<ProviderSecretStatus>
  deleteProviderSecret(
    connectionId: string,
    secretName: string,
  ): Promise<DeleteResponse>
  listRuntimeSlotDefaults(): Promise<RuntimeSlotDefaultListResponse>
  upsertRuntimeSlotDefault(
    slot: string,
    body: RuntimeSlotDefaultUpsertBody,
  ): Promise<RuntimeSlotDefault>
  deleteRuntimeSlotDefault(slot: string): Promise<DeleteResponse>
  listChatModels(): Promise<ChatModelListResponse>
  upsertChatModel(body: ChatModelUpsertBody): Promise<ChatModel>
  setDefaultChatModel(connectionId: string, modelId: string): Promise<ChatModel>
  deleteChatModel(connectionId: string, modelId: string): Promise<DeleteResponse>
  getChatRetrievalSettings(): Promise<ChatRetrievalSettings>
  updateChatRetrievalSettings(
    body: ChatRetrievalSettingsUpsertBody,
  ): Promise<ChatRetrievalSettings>
  getProjectRuntimeSettings(projectId: string): Promise<ProjectRuntimeSettings>
  upsertProjectRuntimeSlotOverride(
    projectId: string,
    slot: string,
    body: RuntimeSlotDefaultUpsertBody,
  ): Promise<ProjectRuntimeSlot>
  deleteProjectRuntimeSlotOverride(
    projectId: string,
    slot: string,
  ): Promise<DeleteResponse>
  upsertProjectChatModel(
    projectId: string,
    body: ChatModelUpsertBody,
  ): Promise<ProjectChatModel>
  setDefaultProjectChatModel(
    projectId: string,
    connectionId: string,
    modelId: string,
  ): Promise<ProjectChatModel>
  deleteProjectChatModel(
    projectId: string,
    connectionId: string,
    modelId: string,
  ): Promise<DeleteResponse>
  upsertProjectChatRetrievalSettings(
    projectId: string,
    body: ChatRetrievalSettingsUpsertBody,
  ): Promise<ProjectChatRetrievalSettings>
  deleteProjectChatRetrievalSettings(projectId: string): Promise<DeleteResponse>
}

export type ApiClientOptions = {
  authToken?: string | null
  baseUrl: string
  fetch?: typeof fetch
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = options.baseUrl.replace(/\/+$/, '')
  const fetchImpl = withAuthToken(
    options.fetch ?? globalThis.fetch,
    options.authToken ?? null,
  )

  return {
    getCurrentUser() {
      return requestJson<CurrentUser>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/auth/me`,
      })
    },
    updateCurrentUserPreferences(body) {
      return requestJson<CurrentUser>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/auth/me/preferences`,
      })
    },
    createUser(body) {
      return requestJson<User>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/users`,
      })
    },
    listUsers() {
      return requestJson<UserListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/users`,
      })
    },
    listProjectMemberships(projectId) {
      return requestJson<ProjectMembershipListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(projectId)}/memberships`,
      })
    },
    upsertProjectMembership(projectId, userId, body) {
      return requestJson<ProjectMembership>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/memberships/${encodePathSegment(userId)}`,
      })
    },
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
    enqueueIngestionJob(projectId, sourceId, body = {}) {
      return requestJson<IngestionJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/sources/${encodePathSegment(sourceId)}/ingestion-jobs`,
      })
    },
    listIngestionJobs(projectId, params = {}) {
      const url = new URL(
        `${baseUrl}/projects/${encodePathSegment(projectId)}/ingestion-jobs`,
      )
      appendSearchParam(url, 'source_id', params.source_id)
      appendSearchParam(url, 'status', params.status)
      appendSearchParam(url, 'job_type', params.job_type)

      return requestJson<IngestionJobListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    getIngestionJob(projectId, jobId) {
      return requestJson<IngestionJobDetailResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/ingestion-jobs/${encodePathSegment(jobId)}`,
      })
    },
    retryIngestionJob(projectId, jobId, body = {}) {
      return requestJson<IngestionJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/ingestion-jobs/${encodePathSegment(jobId)}/retry`,
      })
    },
    runNextIngestionJob(projectId, body = {}) {
      return requestJson<IngestionRunResponse>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/ingestion-jobs/run-next`,
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
    updateChatSessionTitle(projectId, sessionId, title) {
      return requestJson<{ session_id: string; title: string; title_is_custom: boolean }>(
        fetchImpl,
        {
          body: { title },
          method: 'PATCH',
          url: `${baseUrl}/projects/${encodePathSegment(
            projectId,
          )}/chat/sessions/${encodePathSegment(sessionId)}/title`,
        },
      )
    },
    archiveChatSession(projectId, sessionId) {
      return requestVoid(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/chat/sessions/${encodePathSegment(sessionId)}/archive`,
      })
    },
    unarchiveChatSession(projectId, sessionId) {
      return requestVoid(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/chat/sessions/${encodePathSegment(sessionId)}/unarchive`,
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
      appendSearchParam(url, 'archived', params.archived)
      appendSearchParam(url, 'limit', params.limit)
      appendSearchParam(url, 'cursor', params.cursor)

      return requestJson<ChatSessionListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    submitKnowledgeProposal(projectId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/knowledge-proposals`,
      })
    },
    listKnowledgeProposals(projectId, params = {}) {
      const url = new URL(
        `${baseUrl}/projects/${encodePathSegment(projectId)}/knowledge-proposals`,
      )
      appendSearchParam(url, 'status', params.status)

      return requestJson<KnowledgeProposalListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    refineKnowledgeProposal(projectId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/knowledge-proposals/${encodePathSegment(proposalId)}/refine`,
      })
    },
    approveKnowledgeProposal(projectId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/knowledge-proposals/${encodePathSegment(proposalId)}/approve`,
      })
    },
    rejectKnowledgeProposal(projectId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/knowledge-proposals/${encodePathSegment(proposalId)}/reject`,
      })
    },
    listProviderConnections() {
      return requestJson<ProviderConnectionListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/runtime-settings/connections`,
      })
    },
    createProviderConnection(body) {
      return requestJson<ProviderConnection>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/runtime-settings/connections`,
      })
    },
    upsertProviderConnection(connectionId, body) {
      return requestJson<ProviderConnection>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}`,
      })
    },
    deleteProviderConnection(connectionId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}`,
      })
    },
    listProviderModels(params = {}) {
      const url = new URL(`${baseUrl}/runtime-settings/models`)
      appendSearchParam(url, 'connection_id', params.connection_id)
      appendSearchParam(url, 'capability', params.capability)

      return requestJson<ProviderModelListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    syncProviderModels(connectionId) {
      return requestJson<ProviderModelSyncResponse>(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}/models/sync`,
      })
    },
    upsertProviderSecret(connectionId, secretName, body) {
      return requestJson<ProviderSecretStatus>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}/secrets/${encodePathSegment(secretName)}`,
      })
    },
    deleteProviderSecret(connectionId, secretName) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}/secrets/${encodePathSegment(secretName)}`,
      })
    },
    listRuntimeSlotDefaults() {
      return requestJson<RuntimeSlotDefaultListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/runtime-settings/slots`,
      })
    },
    upsertRuntimeSlotDefault(slot, body) {
      return requestJson<RuntimeSlotDefault>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    deleteRuntimeSlotDefault(slot) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    listChatModels() {
      return requestJson<ChatModelListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/runtime-settings/chat/models`,
      })
    },
    upsertChatModel(body) {
      return requestJson<ChatModel>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/runtime-settings/chat/models`,
      })
    },
    setDefaultChatModel(connectionId, modelId) {
      return requestJson<ChatModel>(fetchImpl, {
        method: 'PUT',
        url: `${baseUrl}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}/default`,
      })
    },
    deleteChatModel(connectionId, modelId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}`,
      })
    },
    getChatRetrievalSettings() {
      return requestJson<ChatRetrievalSettings>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/runtime-settings/chat/retrieval`,
      })
    },
    updateChatRetrievalSettings(body) {
      return requestJson<ChatRetrievalSettings>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/runtime-settings/chat/retrieval`,
      })
    },
    getProjectRuntimeSettings(projectId) {
      return requestJson<ProjectRuntimeSettings>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings`,
      })
    },
    upsertProjectRuntimeSlotOverride(projectId, slot, body) {
      return requestJson<ProjectRuntimeSlot>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    deleteProjectRuntimeSlotOverride(projectId, slot) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    upsertProjectChatModel(projectId, body) {
      return requestJson<ProjectChatModel>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/chat/models`,
      })
    },
    setDefaultProjectChatModel(projectId, connectionId, modelId) {
      return requestJson<ProjectChatModel>(fetchImpl, {
        method: 'PUT',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}/default`,
      })
    },
    deleteProjectChatModel(projectId, connectionId, modelId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}`,
      })
    },
    upsertProjectChatRetrievalSettings(projectId, body) {
      return requestJson<ProjectChatRetrievalSettings>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/chat/retrieval`,
      })
    },
    deleteProjectChatRetrievalSettings(projectId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/projects/${encodePathSegment(
          projectId,
        )}/runtime-settings/chat/retrieval`,
      })
    },
  }
}

function appendSearchParam(
  url: URL,
  key: string,
  value: boolean | number | string | null | undefined,
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

function withAuthToken(fetchImpl: typeof fetch, authToken: string | null): typeof fetch {
  const token = authToken?.trim() ?? ''
  if (token.length === 0) {
    return fetchImpl
  }
  return (input, init) =>
    fetchImpl(input, {
      ...init,
      headers: {
        ...headersToRecord(init?.headers),
        Authorization: `Bearer ${token}`,
      },
    })
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (headers === undefined) {
    return {}
  }
  if (headers instanceof Headers) {
    return Object.fromEntries(headers.entries())
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers)
  }
  return { ...headers }
}

async function requestJson<T>(
  fetchImpl: typeof fetch,
  options: {
    body?: unknown
    method: 'DELETE' | 'GET' | 'PATCH' | 'POST' | 'PUT'
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

async function requestVoid(
  fetchImpl: typeof fetch,
  options: {
    body?: unknown
    method: 'DELETE' | 'PATCH' | 'POST' | 'PUT'
    url: string
  },
): Promise<void> {
  const response = await fetchImpl(options.url, {
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    headers:
      options.body === undefined ? undefined : { 'content-type': 'application/json' },
    method: options.method,
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
  if (event.event === 'step') {
    handlers.onStep?.(event.data)
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
        arguments: readOptionalJsonObject(data, 'arguments'),
        limit: readOptionalNumber(data, 'limit'),
        name: readString(data, 'name'),
        query: readOptionalString(data, 'query'),
        result_count: readOptionalNumber(data, 'result_count'),
        result_summary: readOptionalJsonObject(data, 'result_summary'),
      },
    }
  }
  if (eventName === 'step') {
    return {
      event: eventName,
      data: toChatStepEvent(data),
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

function readOptionalNumber(value: JsonObject, key: string): number | undefined {
  const field = value[key]
  if (field === undefined || field === null) {
    return undefined
  }
  if (typeof field !== 'number' || !Number.isFinite(field) || field < 0) {
    throw new Error(`Chat stream event field ${key} must be a non-negative number`)
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

function readOptionalString(value: JsonObject, key: string): string | undefined {
  const field = value[key]
  if (field === undefined || field === null) {
    return undefined
  }
  if (typeof field !== 'string') {
    throw new Error(`Chat stream event field ${key} must be a string`)
  }
  return field
}

function readOptionalJsonObject(
  value: JsonObject,
  key: string,
): JsonObject | undefined {
  const field = value[key]
  if (field === undefined || field === null) {
    return undefined
  }
  if (typeof field !== 'object' || Array.isArray(field)) {
    throw new Error(`Chat stream event field ${key} must be a JSON object`)
  }
  return field as JsonObject
}

function toChatStepEvent(data: JsonObject): ChatStepEvent {
  const step: ChatStepEvent = {
    id: readString(data, 'id'),
    status: readChatStepStatus(data),
  }
  const elapsedMs = readOptionalNumber(data, 'elapsed_ms')
  if (elapsedMs !== undefined) {
    step.elapsed_ms = elapsedMs
  }
  const detail = readOptionalJsonObject(data, 'detail')
  if (detail !== undefined) {
    step.detail = detail
  }
  const usage = readOptionalJsonObject(data, 'usage')
  if (usage !== undefined) {
    step.usage = toChatStepUsage(usage)
  }
  return step
}

function readChatStepStatus(data: JsonObject): ChatStepStatus {
  const status = readString(data, 'status')
  if (status === 'start' || status === 'done' || status === 'error') {
    return status
  }
  throw new Error('Chat stream event field status must be start, done or error')
}

function toChatStepUsage(data: JsonObject): ChatStepUsage {
  const usage: ChatStepUsage = {
    model: readString(data, 'model'),
    provider: readString(data, 'provider'),
    slot: readString(data, 'slot'),
  }
  const inputTokens = readOptionalNumber(data, 'input_tokens')
  if (inputTokens !== undefined) {
    usage.input_tokens = inputTokens
  }
  const outputTokens = readOptionalNumber(data, 'output_tokens')
  if (outputTokens !== undefined) {
    usage.output_tokens = outputTokens
  }
  const totalTokens = readOptionalNumber(data, 'total_tokens')
  if (totalTokens !== undefined) {
    usage.total_tokens = totalTokens
  }
  const estimatedCostUsd = readOptionalNumber(data, 'estimated_cost_usd')
  if (estimatedCostUsd !== undefined) {
    usage.estimated_cost_usd = estimatedCostUsd
  }
  const costSource = readOptionalString(data, 'cost_source')
  if (costSource !== undefined) {
    usage.cost_source = costSource
  }
  return usage
}
