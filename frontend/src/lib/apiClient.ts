import type {
  ChatStep,
  ChatStepEvent,
  ChatStepStatus,
  ChatStepUsage,
} from './chatSteps'

type JsonObject = Record<string, unknown>

export type Workspace = {
  id: string
  name: string
  embedding_mode: string
  retrieval_contextualization_enabled: boolean
  budget_config_json: JsonObject | null
  access_role?: string | null
  can_access?: boolean
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export type WorkspaceCreateBody = {
  name: string
  embedding_mode?: string
  retrieval_contextualization_enabled?: boolean
  budget_config_json?: JsonObject | null
}

export type WorkspaceUpdateBody = {
  name?: string
  embedding_mode?: string
  retrieval_contextualization_enabled?: boolean
  budget_config_json?: JsonObject | null
}

export type WorkspaceListResponse = {
  items: Workspace[]
}

export type CurrentUser = {
  id: string | null
  login: string
  display_name: string
  system_role: string
  is_bootstrap: boolean
  last_workspace_id: string | null
}

export type CurrentUserPreferencesBody = {
  last_workspace_id: string | null
}

export type User = {
  id: string
  login: string
  display_name: string
  system_role: string
  is_active: boolean
  last_workspace_id: string | null
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

export type WorkspaceMembership = {
  id: string
  workspace_id: string
  user_id: string
  role: string
  created_at: string
  updated_at: string
}

export type WorkspaceMembershipUpsertBody = {
  role: string
}

export type WorkspaceMembershipListResponse = {
  items: WorkspaceMembership[]
}

export type Source = {
  id: string
  workspace_id: string
  source_type: string
  external_id: string
  tags: string[] | null
  extra_metadata: JsonObject | null
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export type SourceCreateBody = {
  source_type: string
  external_id: string
  tags?: string[] | null
  extra_metadata?: JsonObject | null
}

export type SourceUpdateBody = {
  external_id?: string
  tags?: string[] | null
  extra_metadata?: JsonObject | null
}

export type AccessTokenRevokeBody = {
  access_token: string
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
  workspace_id: string
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
  workspace_id: string
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
  workspace_id: string
  worker_id: string
  job_id: string | null
  source_id: string | null
  document_id: string | null
  document_version_id: string | null
  created_document_version: boolean | null
  error_message: string | null
}

export type BackgroundJob = {
  id: string
  scope: 'workspace' | 'system'
  workspace_id: string | null
  queue_name: string
  job_type: string
  handler_version: number
  status: string
  priority: number
  payload_json: unknown
  result_json: unknown
  idempotency_key: string | null
  run_after: string
  attempt_count: number
  retry_count: number
  max_retries: number
  current_attempt_id: string | null
  schedule_id: string | null
  scheduled_for: string | null
  concurrency_key: string | null
  cancellation_requested_at: string | null
  last_error: {
    code: string | null
    message: string | null
    trace_id: string | null
  } | null
  finished_at: string | null
  version: number
  created_at: string
  updated_at: string
}

export type BackgroundJobAttempt = {
  id: string
  job_id: string
  attempt_number: number
  worker_id: string
  status: string
  started_at: string
  heartbeat_at: string
  lease_expires_at: string
  finished_at: string | null
  progress_json: JsonObject | null
  error_code: string | null
  error_message: string | null
  trace_id: string | null
}

export type BackgroundJobEvent = {
  id: string
  job_id: string
  attempt_id: string | null
  event_type: string
  message: string | null
  extra_metadata: JsonObject | null
  actor_type: string | null
  actor_id: string | null
  created_at: string
}

export type BackgroundJobDetail = {
  job: BackgroundJob
  attempts: BackgroundJobAttempt[]
  events: BackgroundJobEvent[]
}

export type BackgroundJobListParams = {
  status?: string | null
  queue?: string | null
  job_type?: string | null
  limit?: number | null
  cursor?: string | null
}

export type BackgroundJobPage = {
  items: BackgroundJob[]
  next_cursor: string | null
}

export type EnqueueBackgroundJobBody = {
  job_type: string
  handler_version?: number
  payload?: JsonObject
  queue_name?: string | null
  priority?: number | null
  idempotency_key?: string | null
  run_after?: string | null
  concurrency_key?: string | null
}

export type EnqueueBackgroundJobResponse = {
  created: boolean
  job: BackgroundJob
}

export type VersionMutationBody = {
  version: number
  reset_retry_count?: boolean
}

export type JobHandler = {
  name: string
  version: number
  queue_name: string
  allowed_scopes: string[]
  allow_manual_enqueue: boolean
  minimum_manual_role: string
}

export type JobSchedule = {
  id: string
  scope: 'workspace' | 'system'
  workspace_id: string | null
  name: string
  description: string | null
  queue_name: string
  job_type: string
  handler_version: number
  payload_json: JsonObject
  priority: number
  concurrency_key: string | null
  cron_expression: string
  timezone: string
  misfire_policy: 'skip' | 'run_once' | 'catch_up'
  max_catch_up: number
  paused_at: string | null
  archived_at: string | null
  next_run_at: string
  last_scheduled_for: string | null
  version: number
  created_at: string
  updated_at: string
}

export type JobScheduleListResponse = { items: JobSchedule[] }

export type CreateJobScheduleBody = {
  name: string
  description?: string | null
  job_type: string
  handler_version?: number
  payload?: JsonObject
  queue_name?: string | null
  priority?: number | null
  concurrency_key?: string | null
  cron_expression: string
  timezone: string
  misfire_policy?: 'skip' | 'run_once' | 'catch_up'
  max_catch_up?: number
}

export type UpdateJobScheduleBody = Partial<
  Omit<CreateJobScheduleBody, 'job_type' | 'handler_version'>
> & { version: number }

export type JobQueue = {
  name: string
  paused_at: string | null
  global_concurrency_limit: number | null
  workspace_concurrency_limit: number | null
  default_lease_seconds: number
  version: number
}

export type ConfigureJobQueueBody = {
  version: number
  paused?: boolean | null
  global_concurrency_limit?: number | null
  workspace_concurrency_limit?: number | null
  default_lease_seconds?: number | null
}

export type JobWorker = {
  id: string
  process_identity: string
  application_version: string
  supported_queues: string[]
  supported_handlers: string[]
  max_concurrency: number
  started_at: string
  heartbeat_at: string
  draining_at: string | null
  shutdown_at: string | null
}

export type JobMetrics = {
  generated_at: string
  queues: Array<{
    name: string
    queued: number
    running: number
    blocked: number
    dead_letter: number
    oldest_eligible_age_seconds: number | null
    global_concurrency_limit: number | null
  }>
  workers: { live: number; stale: number; draining: number }
  unroutable_queued: number
  scheduler_lag_seconds: number
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
  strategy?: string
  fallback_reason?: string | null
  retrieval_metadata?: JsonObject | null
  rerank_metadata?: JsonObject | null
}

export type RetrievalStrategy =
  | 'dense'
  | 'sparse'
  | 'dense_sparse'
  | 'graph'

export type RetrievalSearchRequestBody = {
  query: string
  limit?: number
  strategy?: RetrievalStrategy
  metadata_filter?: RetrievalMetadataFilter | null
  rerank?: { candidate_limit: number } | null
}

export type RetrievalSearchResponse = {
  results: RetrievalResult[]
}

export type ChatRequestBody = {
  message: string
  session_id?: string | null
  retrieval_limit?: number
  metadata_filter?: RetrievalMetadataFilter | null
  attachment_ids?: string[]
}

export type ChatAttachmentUploadResponse = {
  id: string
  kind: 'image' | 'document'
  filename: string
  mime: string
  size_bytes: number
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
      data: ChatStreamErrorData
    }

/** Structured chat error from SSE error events and HTTP 4xx bodies. */
export type ChatStreamErrorData = {
  code?: string
  detail: string
  message?: string
  retryable?: boolean
}

export type ChatStreamHandlers = {
  onAnswerDelta?(text: string): void
  onErrorEvent?(error: ChatStreamErrorData): void
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
  workspace_id: string
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
  /** Null when the source chunk was cascade-deleted after soft-delete. */
  chunk_id: string | null
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
  workspace_id: string
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

export type ProviderConnectionCheckResponse = {
  connection_id: string
  ok: boolean
  model_count: number
  message: string
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

export type WorkspaceRuntimeSlot = {
  slot: string
  source: string
  connection_id: string
  model_id: string
  parameters: JsonObject | null
}

export type WorkspaceChatModel = {
  connection_id: string
  model_id: string
  is_default: boolean
  source: string
  parameters: JsonObject | null
}

export type WorkspaceChatRetrievalSettings = ChatRetrievalSettings & {
  source: string
}

export type WorkspaceRuntimeSettings = {
  workspace_id: string
  slots: WorkspaceRuntimeSlot[]
  chat_models: WorkspaceChatModel[]
  chat_retrieval: WorkspaceChatRetrievalSettings
}


export type UserMemoryStatus = 'proposed' | 'approved' | 'rejected'

export type UserMemory = {
  id: string
  user_id: string
  workspace_id: string | null
  content: string
  status: UserMemoryStatus
  created_at: string | null
  reviewed_at: string | null
  reviewed_by_user_id: string | null
}

export type UserMemoryListResponse = {
  items: UserMemory[]
}

export type UserMemoryListParams = {
  workspace_id?: string | null
  status?: UserMemoryStatus | null
}

export type UserMemoryProposeBody = {
  content: string
  workspace_id?: string | null
}

export type UserMemoryUpdateBody = {
  content: string
}

/** Backend hard limit; FE shows a soft hint earlier. */
export const USER_MEMORY_MAX_CHARS = 4000
export const USER_MEMORY_SOFT_HINT_CHARS = 500
/** Matches server assemble_user_memory_block max_items default. */
export const USER_MEMORY_INJECTION_MAX_ITEMS = 8

export class ApiClientError extends Error {
  readonly code: string | null
  readonly detail: unknown
  readonly retryable: boolean
  readonly status: number

  constructor(
    message: string,
    options: {
      code?: string | null
      detail: unknown
      retryable?: boolean
      status: number
    },
  ) {
    super(message)
    this.name = 'ApiClientError'
    this.code = options.code ?? extractErrorCode(options.detail)
    this.detail = options.detail
    this.retryable = options.retryable ?? extractErrorRetryable(options.detail)
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
  listWorkspaceMemberships(
    workspaceId: string,
  ): Promise<WorkspaceMembershipListResponse>
  upsertWorkspaceMembership(
    workspaceId: string,
    userId: string,
    body: WorkspaceMembershipUpsertBody,
  ): Promise<WorkspaceMembership>
  deleteWorkspaceMembership(workspaceId: string, userId: string): Promise<void>
  deactivateUser(userId: string): Promise<User>
  revokeAccessToken(body: AccessTokenRevokeBody): Promise<{ revoked: boolean }>
  createWorkspace(body: WorkspaceCreateBody): Promise<Workspace>
  listWorkspaces(): Promise<WorkspaceListResponse>
  getWorkspace(workspaceId: string): Promise<Workspace>
  updateWorkspace(workspaceId: string, body: WorkspaceUpdateBody): Promise<Workspace>
  deleteWorkspace(workspaceId: string): Promise<Workspace>
  createSource(workspaceId: string, body: SourceCreateBody): Promise<Source>
  listSources(
    workspaceId: string,
    params?: SourceListParams,
  ): Promise<SourceListResponse>
  getSource(workspaceId: string, sourceId: string): Promise<Source>
  updateSource(
    workspaceId: string,
    sourceId: string,
    body: SourceUpdateBody,
  ): Promise<Source>
  deleteSource(workspaceId: string, sourceId: string): Promise<Source>
  enqueueIngestionJob(
    workspaceId: string,
    sourceId: string,
    body?: EnqueueIngestionJobBody,
  ): Promise<IngestionJob>
  listIngestionJobs(
    workspaceId: string,
    params?: IngestionJobListParams,
  ): Promise<IngestionJobListResponse>
  getIngestionJob(
    workspaceId: string,
    jobId: string,
  ): Promise<IngestionJobDetailResponse>
  retryIngestionJob(
    workspaceId: string,
    jobId: string,
    body?: RetryIngestionJobBody,
  ): Promise<IngestionJob>
  runNextIngestionJob(
    workspaceId: string,
    body?: RunNextIngestionJobBody,
  ): Promise<IngestionRunResponse>
  listJobHandlers(workspaceId: string): Promise<JobHandler[]>
  enqueueBackgroundJob(
    workspaceId: string,
    body: EnqueueBackgroundJobBody,
  ): Promise<EnqueueBackgroundJobResponse>
  listBackgroundJobs(
    workspaceId: string,
    params?: BackgroundJobListParams,
  ): Promise<BackgroundJobPage>
  getBackgroundJob(
    workspaceId: string,
    jobId: string,
  ): Promise<BackgroundJobDetail>
  cancelBackgroundJob(
    workspaceId: string,
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  retryBackgroundJob(
    workspaceId: string,
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  unblockBackgroundJob(
    workspaceId: string,
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  listJobSchedules(workspaceId: string): Promise<JobScheduleListResponse>
  createJobSchedule(
    workspaceId: string,
    body: CreateJobScheduleBody,
  ): Promise<JobSchedule>
  getJobSchedule(workspaceId: string, scheduleId: string): Promise<JobSchedule>
  updateJobSchedule(
    workspaceId: string,
    scheduleId: string,
    body: UpdateJobScheduleBody,
  ): Promise<JobSchedule>
  archiveJobSchedule(
    workspaceId: string,
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  pauseJobSchedule(
    workspaceId: string,
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  resumeJobSchedule(
    workspaceId: string,
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  runJobScheduleNow(
    workspaceId: string,
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  listAdminBackgroundJobs(
    params?: BackgroundJobListParams & {
      scope?: 'workspace' | 'system'
      workspace_id?: string | null
    },
  ): Promise<BackgroundJobPage>
  listAdminJobHandlers(): Promise<JobHandler[]>
  enqueueAdminBackgroundJob(
    body: EnqueueBackgroundJobBody,
  ): Promise<EnqueueBackgroundJobResponse>
  getAdminBackgroundJob(jobId: string): Promise<BackgroundJobDetail>
  cancelAdminBackgroundJob(
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  retryAdminBackgroundJob(
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  unblockAdminBackgroundJob(
    jobId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  listAdminJobSchedules(): Promise<JobScheduleListResponse>
  createAdminJobSchedule(body: CreateJobScheduleBody): Promise<JobSchedule>
  updateAdminJobSchedule(
    scheduleId: string,
    body: UpdateJobScheduleBody,
  ): Promise<JobSchedule>
  archiveAdminJobSchedule(
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  pauseAdminJobSchedule(
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  resumeAdminJobSchedule(
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<JobSchedule>
  runAdminJobScheduleNow(
    scheduleId: string,
    body: VersionMutationBody,
  ): Promise<BackgroundJob>
  listJobQueues(): Promise<JobQueue[]>
  getJobQueue(queueName: string): Promise<JobQueue>
  configureJobQueue(
    queueName: string,
    body: ConfigureJobQueueBody,
  ): Promise<JobQueue>
  listJobWorkers(): Promise<JobWorker[]>
  getJobMetrics(): Promise<JobMetrics>
  askChat(workspaceId: string, body: ChatRequestBody): Promise<ChatResponseBody>
  askChatStream(
    workspaceId: string,
    body: ChatRequestBody,
    handlers?: ChatStreamHandlers,
    options?: ChatStreamOptions,
  ): Promise<ChatResponseBody>
  uploadChatAttachment(
    workspaceId: string,
    file: File,
    sessionId?: string | null,
  ): Promise<ChatAttachmentUploadResponse>
  deleteChatAttachment(
    workspaceId: string,
    attachmentId: string,
  ): Promise<void>
  /** Authenticated blob fetch for attachment preview / download. */
  getChatAttachmentContent(
    workspaceId: string,
    attachmentId: string,
  ): Promise<Blob>
  searchRetrieval(
    workspaceId: string,
    body: RetrievalSearchRequestBody,
  ): Promise<RetrievalSearchResponse>
  listChatSessions(
    workspaceId: string,
    params?: ChatSessionListParams,
  ): Promise<ChatSessionListResponse>
  getChatSession(
    workspaceId: string,
    sessionId: string,
  ): Promise<ChatSessionDetailResponse>
  updateChatSessionTitle(
    workspaceId: string,
    sessionId: string,
    title: string,
  ): Promise<{ session_id: string; title: string; title_is_custom: boolean }>
  archiveChatSession(workspaceId: string, sessionId: string): Promise<void>
  unarchiveChatSession(workspaceId: string, sessionId: string): Promise<void>
  deleteChatSession(workspaceId: string, sessionId: string): Promise<void>
  getChatObservabilitySummary(
    workspaceId: string,
    params?: ChatObservabilitySummaryParams,
  ): Promise<ChatObservabilitySummary>
  submitKnowledgeProposal(
    workspaceId: string,
    body: KnowledgeProposalSubmitBody,
  ): Promise<KnowledgeProposal>
  listKnowledgeProposals(
    workspaceId: string,
    params?: KnowledgeProposalListParams,
  ): Promise<KnowledgeProposalListResponse>
  refineKnowledgeProposal(
    workspaceId: string,
    proposalId: string,
    body: KnowledgeProposalRefineBody,
  ): Promise<KnowledgeProposal>
  approveKnowledgeProposal(
    workspaceId: string,
    proposalId: string,
    body: KnowledgeProposalApproveBody,
  ): Promise<KnowledgeProposal>
  rejectKnowledgeProposal(
    workspaceId: string,
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
  checkProviderConnection(
    connectionId: string,
  ): Promise<ProviderConnectionCheckResponse>
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
  getWorkspaceRuntimeSettings(workspaceId: string): Promise<WorkspaceRuntimeSettings>
  upsertWorkspaceRuntimeSlotOverride(
    workspaceId: string,
    slot: string,
    body: RuntimeSlotDefaultUpsertBody,
  ): Promise<WorkspaceRuntimeSlot>
  deleteWorkspaceRuntimeSlotOverride(
    workspaceId: string,
    slot: string,
  ): Promise<DeleteResponse>
  upsertWorkspaceChatModel(
    workspaceId: string,
    body: ChatModelUpsertBody,
  ): Promise<WorkspaceChatModel>
  setDefaultWorkspaceChatModel(
    workspaceId: string,
    connectionId: string,
    modelId: string,
  ): Promise<WorkspaceChatModel>
  deleteWorkspaceChatModel(
    workspaceId: string,
    connectionId: string,
    modelId: string,
  ): Promise<DeleteResponse>
  upsertWorkspaceChatRetrievalSettings(
    workspaceId: string,
    body: ChatRetrievalSettingsUpsertBody,
  ): Promise<WorkspaceChatRetrievalSettings>
  deleteWorkspaceChatRetrievalSettings(workspaceId: string): Promise<DeleteResponse>
  listUserMemories(
    params?: UserMemoryListParams,
  ): Promise<UserMemoryListResponse>
  proposeUserMemory(body: UserMemoryProposeBody): Promise<UserMemory>
  updateUserMemory(
    memoryId: string,
    body: UserMemoryUpdateBody,
  ): Promise<UserMemory>
  approveUserMemory(memoryId: string): Promise<UserMemory>
  rejectUserMemory(memoryId: string): Promise<UserMemory>
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
    listWorkspaceMemberships(workspaceId) {
      return requestJson<WorkspaceMembershipListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/memberships`,
      })
    },
    upsertWorkspaceMembership(workspaceId, userId, body) {
      return requestJson<WorkspaceMembership>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/memberships/${encodePathSegment(userId)}`,
      })
    },
    deleteWorkspaceMembership(workspaceId, userId) {
      return requestVoid(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/memberships/${encodePathSegment(userId)}`,
      })
    },
    deactivateUser(userId) {
      return requestJson<User>(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/admin/users/${encodePathSegment(userId)}/deactivate`,
      })
    },
    revokeAccessToken(body) {
      return requestJson<{ revoked: boolean }>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/access-tokens/revoke`,
      })
    },
    createWorkspace(body) {
      return requestJson<Workspace>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces`,
      })
    },
    listWorkspaces() {
      return requestJson<WorkspaceListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces`,
      })
    },
    getWorkspace(workspaceId) {
      return requestJson<Workspace>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}`,
      })
    },
    updateWorkspace(workspaceId, body) {
      return requestJson<Workspace>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}`,
      })
    },
    deleteWorkspace(workspaceId) {
      return requestJson<Workspace>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}`,
      })
    },
    createSource(workspaceId, body) {
      return requestJson<Source>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/sources`,
      })
    },
    listSources(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/sources`,
      )
      appendSearchParam(url, 'source_type', params.source_type)
      appendSearchParam(url, 'external_id', params.external_id)
      appendSearchParam(url, 'tag', params.tag)

      return requestJson<SourceListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    getSource(workspaceId, sourceId) {
      return requestJson<Source>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/sources/${encodePathSegment(sourceId)}`,
      })
    },
    updateSource(workspaceId, sourceId, body) {
      return requestJson<Source>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/sources/${encodePathSegment(sourceId)}`,
      })
    },
    deleteSource(workspaceId, sourceId) {
      return requestJson<Source>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/sources/${encodePathSegment(sourceId)}`,
      })
    },
    enqueueIngestionJob(workspaceId, sourceId, body = {}) {
      return requestJson<IngestionJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/sources/${encodePathSegment(sourceId)}/ingestion-jobs`,
      })
    },
    listIngestionJobs(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/ingestion-jobs`,
      )
      appendSearchParam(url, 'source_id', params.source_id)
      appendSearchParam(url, 'status', params.status)
      appendSearchParam(url, 'job_type', params.job_type)

      return requestJson<IngestionJobListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    getIngestionJob(workspaceId, jobId) {
      return requestJson<IngestionJobDetailResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/ingestion-jobs/${encodePathSegment(jobId)}`,
      })
    },
    retryIngestionJob(workspaceId, jobId, body = {}) {
      return requestJson<IngestionJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/ingestion-jobs/${encodePathSegment(jobId)}/retry`,
      })
    },
    runNextIngestionJob(workspaceId, body = {}) {
      return requestJson<IngestionRunResponse>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/ingestion-jobs/run-next`,
      })
    },
    listJobHandlers(workspaceId) {
      return requestJson<JobHandler[]>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-handlers`,
      })
    },
    enqueueBackgroundJob(workspaceId, body) {
      return requestJson<EnqueueBackgroundJobResponse>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/jobs`,
      })
    },
    listBackgroundJobs(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/jobs`,
      )
      appendSearchParam(url, 'status', params.status)
      appendSearchParam(url, 'queue', params.queue)
      appendSearchParam(url, 'job_type', params.job_type)
      appendSearchParam(url, 'limit', params.limit)
      appendSearchParam(url, 'cursor', params.cursor)
      return requestJson<BackgroundJobPage>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    getBackgroundJob(workspaceId, jobId) {
      return requestJson<BackgroundJobDetail>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/jobs/${encodePathSegment(jobId)}`,
      })
    },
    cancelBackgroundJob(workspaceId, jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/jobs/${encodePathSegment(jobId)}/cancel`,
      })
    },
    retryBackgroundJob(workspaceId, jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/jobs/${encodePathSegment(jobId)}/retry`,
      })
    },
    unblockBackgroundJob(workspaceId, jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/jobs/${encodePathSegment(jobId)}/unblock`,
      })
    },
    listJobSchedules(workspaceId) {
      return requestJson<JobScheduleListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules`,
      })
    },
    createJobSchedule(workspaceId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules`,
      })
    },
    getJobSchedule(workspaceId, scheduleId) {
      return requestJson<JobSchedule>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}`,
      })
    },
    updateJobSchedule(workspaceId, scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}`,
      })
    },
    archiveJobSchedule(workspaceId, scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}`,
      })
    },
    pauseJobSchedule(workspaceId, scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}/pause`,
      })
    },
    resumeJobSchedule(workspaceId, scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}/resume`,
      })
    },
    runJobScheduleNow(workspaceId, scheduleId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/job-schedules/${encodePathSegment(scheduleId)}/run-now`,
      })
    },
    listAdminBackgroundJobs(params = {}) {
      const url = new URL(`${baseUrl}/admin/jobs`)
      appendSearchParam(url, 'scope', params.scope)
      appendSearchParam(url, 'workspace_id', params.workspace_id)
      appendSearchParam(url, 'status', params.status)
      appendSearchParam(url, 'queue', params.queue)
      appendSearchParam(url, 'job_type', params.job_type)
      appendSearchParam(url, 'limit', params.limit)
      appendSearchParam(url, 'cursor', params.cursor)
      return requestJson<BackgroundJobPage>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    listAdminJobHandlers() {
      return requestJson<JobHandler[]>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-handlers`,
      })
    },
    enqueueAdminBackgroundJob(body) {
      return requestJson<EnqueueBackgroundJobResponse>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/jobs`,
      })
    },
    getAdminBackgroundJob(jobId) {
      return requestJson<BackgroundJobDetail>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/jobs/${encodePathSegment(jobId)}`,
      })
    },
    cancelAdminBackgroundJob(jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/jobs/${encodePathSegment(jobId)}/cancel`,
      })
    },
    retryAdminBackgroundJob(jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/jobs/${encodePathSegment(jobId)}/retry`,
      })
    },
    unblockAdminBackgroundJob(jobId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/jobs/${encodePathSegment(jobId)}/unblock`,
      })
    },
    listAdminJobSchedules() {
      return requestJson<JobScheduleListResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-schedules`,
      })
    },
    createAdminJobSchedule(body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/job-schedules`,
      })
    },
    updateAdminJobSchedule(scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/admin/job-schedules/${encodePathSegment(scheduleId)}`,
      })
    },
    archiveAdminJobSchedule(scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'DELETE',
        url: `${baseUrl}/admin/job-schedules/${encodePathSegment(scheduleId)}`,
      })
    },
    pauseAdminJobSchedule(scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/job-schedules/${encodePathSegment(scheduleId)}/pause`,
      })
    },
    resumeAdminJobSchedule(scheduleId, body) {
      return requestJson<JobSchedule>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/job-schedules/${encodePathSegment(scheduleId)}/resume`,
      })
    },
    runAdminJobScheduleNow(scheduleId, body) {
      return requestJson<BackgroundJob>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/admin/job-schedules/${encodePathSegment(scheduleId)}/run-now`,
      })
    },
    listJobQueues() {
      return requestJson<JobQueue[]>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-queues`,
      })
    },
    getJobQueue(queueName) {
      return requestJson<JobQueue>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-queues/${encodePathSegment(queueName)}`,
      })
    },
    configureJobQueue(queueName, body) {
      return requestJson<JobQueue>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/admin/job-queues/${encodePathSegment(queueName)}`,
      })
    },
    listJobWorkers() {
      return requestJson<JobWorker[]>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-workers`,
      })
    },
    getJobMetrics() {
      return requestJson<JobMetrics>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/admin/job-metrics`,
      })
    },
    askChat(workspaceId, body) {
      return requestJson<ChatResponseBody>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/chat`,
      })
    },
    searchRetrieval(workspaceId, body) {
      return requestJson<RetrievalSearchResponse>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/retrieval/search`,
      })
    },
    askChatStream(workspaceId, body, handlers = {}, requestOptions = {}) {
      return requestChatStream(fetchImpl, {
        body,
        handlers,
        signal: requestOptions.signal,
        url: `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/chat/stream`,
      })
    },
    uploadChatAttachment(workspaceId, file, sessionId = null) {
      const form = new FormData()
      form.append('file', file, file.name)
      if (sessionId !== null && sessionId !== undefined && sessionId.length > 0) {
        form.append('session_id', sessionId)
      }
      return requestForm<ChatAttachmentUploadResponse>(fetchImpl, {
        body: form,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/attachments`,
      })
    },
    deleteChatAttachment(workspaceId, attachmentId) {
      return requestVoid(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/attachments/${encodePathSegment(attachmentId)}`,
      })
    },
    getChatAttachmentContent(workspaceId, attachmentId) {
      return requestBlob(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/attachments/${encodePathSegment(attachmentId)}/content`,
      })
    },
    getChatSession(workspaceId, sessionId) {
      return requestJson<ChatSessionDetailResponse>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/sessions/${encodePathSegment(sessionId)}`,
      })
    },
    updateChatSessionTitle(workspaceId, sessionId, title) {
      return requestJson<{ session_id: string; title: string; title_is_custom: boolean }>(
        fetchImpl,
        {
          body: { title },
          method: 'PATCH',
          url: `${baseUrl}/workspaces/${encodePathSegment(
            workspaceId,
          )}/chat/sessions/${encodePathSegment(sessionId)}/title`,
        },
      )
    },
    archiveChatSession(workspaceId, sessionId) {
      return requestVoid(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/sessions/${encodePathSegment(sessionId)}/archive`,
      })
    },
    unarchiveChatSession(workspaceId, sessionId) {
      return requestVoid(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/sessions/${encodePathSegment(sessionId)}/unarchive`,
      })
    },
    deleteChatSession(workspaceId, sessionId) {
      return requestVoid(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/chat/sessions/${encodePathSegment(sessionId)}`,
      })
    },
    getChatObservabilitySummary(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
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
    listChatSessions(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/chat/sessions`,
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
    submitKnowledgeProposal(workspaceId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/knowledge-proposals`,
      })
    },
    listKnowledgeProposals(workspaceId, params = {}) {
      const url = new URL(
        `${baseUrl}/workspaces/${encodePathSegment(workspaceId)}/knowledge-proposals`,
      )
      appendSearchParam(url, 'status', params.status)

      return requestJson<KnowledgeProposalListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    refineKnowledgeProposal(workspaceId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/knowledge-proposals/${encodePathSegment(proposalId)}/refine`,
      })
    },
    approveKnowledgeProposal(workspaceId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/knowledge-proposals/${encodePathSegment(proposalId)}/approve`,
      })
    },
    rejectKnowledgeProposal(workspaceId, proposalId, body) {
      return requestJson<KnowledgeProposal>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
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
    checkProviderConnection(connectionId) {
      return requestJson<ProviderConnectionCheckResponse>(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/runtime-settings/connections/${encodePathSegment(
          connectionId,
        )}/check`,
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
    getWorkspaceRuntimeSettings(workspaceId) {
      return requestJson<WorkspaceRuntimeSettings>(fetchImpl, {
        method: 'GET',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings`,
      })
    },
    upsertWorkspaceRuntimeSlotOverride(workspaceId, slot, body) {
      return requestJson<WorkspaceRuntimeSlot>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    deleteWorkspaceRuntimeSlotOverride(workspaceId, slot) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/slots/${encodePathSegment(slot)}`,
      })
    },
    upsertWorkspaceChatModel(workspaceId, body) {
      return requestJson<WorkspaceChatModel>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/chat/models`,
      })
    },
    setDefaultWorkspaceChatModel(workspaceId, connectionId, modelId) {
      return requestJson<WorkspaceChatModel>(fetchImpl, {
        method: 'PUT',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}/default`,
      })
    },
    deleteWorkspaceChatModel(workspaceId, connectionId, modelId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/chat/models/${encodePathSegment(
          connectionId,
        )}/${encodePathSegment(modelId)}`,
      })
    },
    upsertWorkspaceChatRetrievalSettings(workspaceId, body) {
      return requestJson<WorkspaceChatRetrievalSettings>(fetchImpl, {
        body,
        method: 'PUT',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/chat/retrieval`,
      })
    },
    deleteWorkspaceChatRetrievalSettings(workspaceId) {
      return requestJson<DeleteResponse>(fetchImpl, {
        method: 'DELETE',
        url: `${baseUrl}/workspaces/${encodePathSegment(
          workspaceId,
        )}/runtime-settings/chat/retrieval`,
      })
    },
    listUserMemories(params = {}) {
      const url = new URL(`${baseUrl}/users/me/memories`)
      appendSearchParam(url, 'workspace_id', params.workspace_id)
      appendSearchParam(url, 'status', params.status)

      return requestJson<UserMemoryListResponse>(fetchImpl, {
        method: 'GET',
        url: url.toString(),
      })
    },
    proposeUserMemory(body) {
      return requestJson<UserMemory>(fetchImpl, {
        body,
        method: 'POST',
        url: `${baseUrl}/users/me/memories`,
      })
    },
    updateUserMemory(memoryId, body) {
      return requestJson<UserMemory>(fetchImpl, {
        body,
        method: 'PATCH',
        url: `${baseUrl}/users/me/memories/${encodePathSegment(memoryId)}`,
      })
    },
    approveUserMemory(memoryId) {
      return requestJson<UserMemory>(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/users/me/memories/${encodePathSegment(memoryId)}/approve`,
      })
    },
    rejectUserMemory(memoryId) {
      return requestJson<UserMemory>(fetchImpl, {
        method: 'POST',
        url: `${baseUrl}/users/me/memories/${encodePathSegment(memoryId)}/reject`,
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
      getApiErrorMessage(detail, response.status),
      {
        detail,
        status: response.status,
      },
    )
  }

  return payload as T
}

/** Multipart FormData; do not set content-type (browser sets boundary). */
async function requestForm<T>(
  fetchImpl: typeof fetch,
  options: {
    body: FormData
    method: 'POST' | 'PUT' | 'PATCH'
    url: string
  },
): Promise<T> {
  const response = await fetchImpl(options.url, {
    body: options.body,
    method: options.method,
  })
  const payload = await readJson(response)

  if (!response.ok) {
    const detail = getErrorDetail(payload)
    throw new ApiClientError(
      getApiErrorMessage(detail, response.status),
      {
        detail,
        status: response.status,
      },
    )
  }

  return payload as T
}

async function requestBlob(
  fetchImpl: typeof fetch,
  options: {
    method: 'GET'
    url: string
  },
): Promise<Blob> {
  const response = await fetchImpl(options.url, {
    method: options.method,
  })
  if (!response.ok) {
    const payload = await readJson(response)
    const detail = getErrorDetail(payload)
    throw new ApiClientError(getApiErrorMessage(detail, response.status), {
      detail,
      status: response.status,
    })
  }
  return response.blob()
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
      getApiErrorMessage(detail, response.status),
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
      getApiErrorMessage(detail, response.status),
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
    handlers.onErrorEvent?.(event.data)
    const message = event.data.message ?? event.data.detail
    throw new ApiClientError(message, {
      code: event.data.code ?? null,
      detail: event.data,
      retryable: event.data.retryable ?? false,
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
    const detail = readOptionalString(data, 'detail')
    const message = readOptionalString(data, 'message') ?? detail
    if (message === undefined) {
      throw new Error('Chat stream error event requires detail or message')
    }
    return {
      event: eventName,
      data: {
        code: readOptionalString(data, 'code'),
        detail: detail ?? message,
        message,
        retryable: readOptionalBoolean(data, 'retryable'),
      },
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

function getApiErrorMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string') {
    return detail
  }
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'message' in detail &&
    typeof (detail as { message: unknown }).message === 'string'
  ) {
    return (detail as { message: string }).message
  }
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'detail' in detail &&
    typeof (detail as { detail: unknown }).detail === 'string'
  ) {
    return (detail as { detail: string }).detail
  }
  return `Request failed with status ${status}`
}

function extractErrorCode(detail: unknown): string | null {
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'code' in detail &&
    typeof (detail as { code: unknown }).code === 'string'
  ) {
    return (detail as { code: string }).code
  }
  return null
}

function extractErrorRetryable(detail: unknown): boolean {
  if (
    detail !== null &&
    typeof detail === 'object' &&
    'retryable' in detail &&
    typeof (detail as { retryable: unknown }).retryable === 'boolean'
  ) {
    return (detail as { retryable: boolean }).retryable
  }
  return false
}

function readOptionalBoolean(
  value: JsonObject,
  key: string,
): boolean | undefined {
  const field = value[key]
  if (field === undefined || field === null) {
    return undefined
  }
  if (typeof field !== 'boolean') {
    throw new Error(`Chat stream event field ${key} must be a boolean`)
  }
  return field
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
