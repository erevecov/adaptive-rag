/**
 * @vitest-environment jsdom
 */
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import App from './App'
import type {
  ApiClient,
  ChatObservabilitySummary,
  ChatResponseBody,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
  ChatStreamHandlers,
  IngestionJob,
  IngestionJobListResponse,
  IngestionRunResponse,
  ChatModelListResponse,
  KnowledgeProposal,
  KnowledgeProposalListResponse,
  Project,
  ProjectMembership,
  ProjectMembershipListResponse,
  ProjectRuntimeSettings,
  ProviderConnectionListResponse,
  ProviderModelListResponse,
  RuntimeSlotDefaultListResponse,
  ProjectListResponse,
  Source,
  SourceListResponse,
  User,
  UserListResponse,
} from './lib/apiClient'
import { ApiClientError } from './lib/apiClient'

const projectId = '11111111-1111-4111-8111-111111111111'

function installLocalStorage() {
  const entries = new Map<string, string>()
  const storage = {
    get length() {
      return entries.size
    },
    clear() {
      entries.clear()
    },
    getItem(key: string) {
      return entries.get(key) ?? null
    },
    key(index: number) {
      return Array.from(entries.keys())[index] ?? null
    },
    removeItem(key: string) {
      entries.delete(key)
    },
    setItem(key: string, value: string) {
      entries.set(key, value)
    },
  } satisfies Storage

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage,
  })
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: storage,
  })
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: width,
  })
  window.dispatchEvent(new Event('resize'))
}

beforeEach(() => {
  setViewportWidth(1400)
  installLocalStorage()
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.classList.remove('dark')
  delete (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition
  delete (window as unknown as { webkitSpeechRecognition?: unknown })
    .webkitSpeechRecognition
})

class FakeSpeechRecognition {
  static latest: FakeSpeechRecognition | null = null

  continuous = false
  interimResults = false
  lang = ''
  onend: (() => void) | null = null
  onerror: ((event: { error?: string }) => void) | null = null
  onresult:
    | ((event: { results: Array<Array<{ transcript: string }>> }) => void)
    | null = null
  start = vi.fn()
  stop = vi.fn()

  constructor() {
    FakeSpeechRecognition.latest = this
  }
}

function installFakeSpeechRecognition() {
  FakeSpeechRecognition.latest = null
  Object.defineProperty(window, 'SpeechRecognition', {
    configurable: true,
    value: FakeSpeechRecognition,
  })
}

function createClientStub(options: {
  askChat?: ApiClient['askChat']
  askChatStream?: ApiClient['askChatStream']
  archiveChatSession?: ApiClient['archiveChatSession']
  createProject?: ApiClient['createProject']
  createProviderConnection?: ApiClient['createProviderConnection']
  createSource?: ApiClient['createSource']
  createUser?: ApiClient['createUser']
  enqueueIngestionJob?: ApiClient['enqueueIngestionJob']
  getChatObservabilitySummary?: ApiClient['getChatObservabilitySummary']
  getChatSession?: ApiClient['getChatSession']
  getCurrentUser?: ApiClient['getCurrentUser']
  getIngestionJob?: ApiClient['getIngestionJob']
  getProject?: ApiClient['getProject']
  getProjectRuntimeSettings?: ApiClient['getProjectRuntimeSettings']
  getChatRetrievalSettings?: ApiClient['getChatRetrievalSettings']
  getSource?: ApiClient['getSource']
  listChatModels?: ApiClient['listChatModels']
  listChatSessions?: ApiClient['listChatSessions']
  listIngestionJobs?: ApiClient['listIngestionJobs']
  listKnowledgeProposals?: ApiClient['listKnowledgeProposals']
  listProjectMemberships?: ApiClient['listProjectMemberships']
  listProviderConnections?: ApiClient['listProviderConnections']
  listProviderModels?: ApiClient['listProviderModels']
  listProjects?: ApiClient['listProjects']
  listRuntimeSlotDefaults?: ApiClient['listRuntimeSlotDefaults']
  listSources?: ApiClient['listSources']
  listUsers?: ApiClient['listUsers']
  unarchiveChatSession?: ApiClient['unarchiveChatSession']
  updateChatSessionTitle?: ApiClient['updateChatSessionTitle']
  updateChatRetrievalSettings?: ApiClient['updateChatRetrievalSettings']
  updateCurrentUserPreferences?: ApiClient['updateCurrentUserPreferences']
  refineKnowledgeProposal?: ApiClient['refineKnowledgeProposal']
  approveKnowledgeProposal?: ApiClient['approveKnowledgeProposal']
  rejectKnowledgeProposal?: ApiClient['rejectKnowledgeProposal']
  retryIngestionJob?: ApiClient['retryIngestionJob']
  runNextIngestionJob?: ApiClient['runNextIngestionJob']
  submitKnowledgeProposal?: ApiClient['submitKnowledgeProposal']
  upsertChatModel?: ApiClient['upsertChatModel']
  upsertProjectChatRetrievalSettings?: ApiClient['upsertProjectChatRetrievalSettings']
  upsertProjectMembership?: ApiClient['upsertProjectMembership']
  upsertProjectChatModel?: ApiClient['upsertProjectChatModel']
  upsertProjectRuntimeSlotOverride?: ApiClient['upsertProjectRuntimeSlotOverride']
  upsertProviderConnection?: ApiClient['upsertProviderConnection']
  upsertProviderSecret?: ApiClient['upsertProviderSecret']
  upsertRuntimeSlotDefault?: ApiClient['upsertRuntimeSlotDefault']
  deleteProjectChatRetrievalSettings?: ApiClient['deleteProjectChatRetrievalSettings']
  deleteProjectRuntimeSlotOverride?: ApiClient['deleteProjectRuntimeSlotOverride']
  syncProviderModels?: ApiClient['syncProviderModels']
}): ApiClient {
  return {
    askChat: options.askChat ?? vi.fn(),
    askChatStream: options.askChatStream ?? vi.fn(),
    archiveChatSession: options.archiveChatSession ?? vi.fn(),
    createProject: options.createProject ?? vi.fn(),
    createProviderConnection: options.createProviderConnection ?? vi.fn(),
    createSource: options.createSource ?? vi.fn(),
    createUser: options.createUser ?? vi.fn(),
    enqueueIngestionJob: options.enqueueIngestionJob ?? vi.fn(),
    getCurrentUser:
      options.getCurrentUser ??
      vi.fn(async () => ({
        display_name: 'Bootstrap Superadmin',
        id: null,
        is_bootstrap: true,
        last_project_id: null,
        login: 'bootstrap',
        system_role: 'superadmin',
      })),
    getChatObservabilitySummary:
      options.getChatObservabilitySummary ?? vi.fn(),
    getChatSession: options.getChatSession ?? vi.fn(async () => emptySessionDetail),
    getIngestionJob: options.getIngestionJob ?? vi.fn(),
    getProject: options.getProject ?? vi.fn(),
    getProjectRuntimeSettings: options.getProjectRuntimeSettings ?? vi.fn(),
    getChatRetrievalSettings:
      options.getChatRetrievalSettings ??
      vi.fn(async () => ({
        max_limit: 50,
        rerank_candidate_limit: 10,
        rerank_enabled: true,
        retrieval_limit: 5,
      })),
    getSource: options.getSource ?? vi.fn(),
    listChatModels: options.listChatModels ?? vi.fn(),
    listChatSessions:
      options.listChatSessions ??
      vi.fn(async () => ({ items: [], next_cursor: null })),
    listIngestionJobs: options.listIngestionJobs ?? vi.fn(),
    listKnowledgeProposals: options.listKnowledgeProposals ?? vi.fn(),
    listProjectMemberships: options.listProjectMemberships ?? vi.fn(),
    listProviderConnections: options.listProviderConnections ?? vi.fn(),
    listProviderModels: options.listProviderModels ?? vi.fn(),
    listProjects:
      options.listProjects ?? vi.fn(async () => ({ items: [] })),
    listRuntimeSlotDefaults: options.listRuntimeSlotDefaults ?? vi.fn(),
    listSources: options.listSources ?? vi.fn(),
    listUsers: options.listUsers ?? vi.fn(),
    refineKnowledgeProposal: options.refineKnowledgeProposal ?? vi.fn(),
    approveKnowledgeProposal: options.approveKnowledgeProposal ?? vi.fn(),
    rejectKnowledgeProposal: options.rejectKnowledgeProposal ?? vi.fn(),
    retryIngestionJob: options.retryIngestionJob ?? vi.fn(),
    runNextIngestionJob: options.runNextIngestionJob ?? vi.fn(),
    submitKnowledgeProposal: options.submitKnowledgeProposal ?? vi.fn(),
    unarchiveChatSession: options.unarchiveChatSession ?? vi.fn(),
    updateChatSessionTitle: options.updateChatSessionTitle ?? vi.fn(),
    updateChatRetrievalSettings:
      options.updateChatRetrievalSettings ?? vi.fn(),
    updateCurrentUserPreferences:
      options.updateCurrentUserPreferences ??
      vi.fn(async () => ({
        display_name: 'Bootstrap Superadmin',
        id: null,
        is_bootstrap: true,
        last_project_id: null,
        login: 'bootstrap',
        system_role: 'superadmin',
    })),
    upsertChatModel: options.upsertChatModel ?? vi.fn(),
    upsertProjectChatRetrievalSettings:
      options.upsertProjectChatRetrievalSettings ?? vi.fn(),
    upsertProjectMembership: options.upsertProjectMembership ?? vi.fn(),
    upsertProjectChatModel: options.upsertProjectChatModel ?? vi.fn(),
    upsertProjectRuntimeSlotOverride:
      options.upsertProjectRuntimeSlotOverride ?? vi.fn(),
    upsertProviderConnection: options.upsertProviderConnection ?? vi.fn(),
    upsertProviderSecret: options.upsertProviderSecret ?? vi.fn(),
    upsertRuntimeSlotDefault: options.upsertRuntimeSlotDefault ?? vi.fn(),
    deleteChatModel: vi.fn(),
    deleteProjectChatModel: vi.fn(),
    deleteProjectChatRetrievalSettings:
      options.deleteProjectChatRetrievalSettings ?? vi.fn(),
    deleteProjectRuntimeSlotOverride:
      options.deleteProjectRuntimeSlotOverride ?? vi.fn(),
    deleteProviderConnection: vi.fn(),
    deleteProviderSecret: vi.fn(),
    deleteRuntimeSlotDefault: vi.fn(),
    setDefaultChatModel: vi.fn(),
    setDefaultProjectChatModel: vi.fn(),
    syncProviderModels: options.syncProviderModels ?? vi.fn(),
  }
}

const chatResponse: ChatResponseBody = {
  answer: 'Use the deployment runbook before retrying the import.',
  citations: [
    {
      chunk_id: 'chunk-1',
      citation: {
        char_end: 98,
        char_start: 12,
        chunk_id: 'chunk-1',
        document_id: 'document-1',
        document_stable_id: 'deployment-runbook',
        document_version_id: 'version-1',
        document_version_number: 2,
        section_metadata: null,
        snippet: 'Restart the worker before retrying the import.',
        source_external_id: 'https://docs.local/runbook',
        source_extra_metadata: null,
        source_id: 'source-1',
        source_tags: ['runbook'],
        source_type: 'url',
      },
      distance: 0.12,
      embedding_metadata: null,
      score: 0.88,
    },
  ],
  session_id: 'session-123',
  tool_calls: [
    {
      limit: 5,
      name: 'rag_search',
      query: 'deployment retry runbook',
      result_count: 1,
    },
  ],
}

const sessionListResponse: ChatSessionListResponse = {
  items: [
    {
      archived_at: null,
      created_at: '2026-06-21T00:00:00Z',
      error_message: null,
      has_approved_training: true,
      has_pending_training: false,
      message_count: 2,
      model_config: null,
      prompt_version: 'default',
      provider_usage_count: 1,
      retrieval_run_count: 1,
      session_id: 'session-123',
      status: 'succeeded',
      title: 'Deployment question',
      title_is_custom: false,
      tool_call_count: 1,
      total_estimated_cost_usd: 0.0025,
      updated_at: '2026-06-21T00:00:01Z',
    },
  ],
  next_cursor: null,
}

const projectSummary: Project = {
  budget_config_json: null,
  created_at: '2026-06-22T00:00:00Z',
  embedding_mode: 'dense',
  id: projectId,
  name: 'Demo',
  retrieval_contextualization_enabled: true,
  updated_at: '2026-06-22T00:00:00Z',
}

const projectListResponse: ProjectListResponse = {
  items: [projectSummary],
}

const viewerUser: User = {
  created_at: '2026-06-22T00:00:00Z',
  display_name: 'Viewer User',
  id: '44444444-4444-4444-8444-444444444444',
  is_active: true,
  last_project_id: null,
  login: 'viewer@example.com',
  system_role: 'user',
  updated_at: '2026-06-22T00:00:00Z',
}

const userListResponse: UserListResponse = {
  items: [viewerUser],
}

const viewerMembership: ProjectMembership = {
  created_at: '2026-06-22T00:00:00Z',
  id: '55555555-5555-4555-8555-555555555555',
  project_id: projectId,
  role: 'viewer',
  updated_at: '2026-06-22T00:00:00Z',
  user_id: viewerUser.id,
}

const membershipListResponse: ProjectMembershipListResponse = {
  items: [viewerMembership],
}

const pendingKnowledgeProposal: KnowledgeProposal = {
  approved_source_id: null,
  created_at: '2026-06-22T00:00:00Z',
  id: '66666666-6666-4666-8666-666666666666',
  origin_message_id: null,
  origin_session_id: null,
  project_id: projectId,
  proposed_text: 'Document the escalation runbook from chat.',
  refined_text: null,
  review_note: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  status: 'pending',
  submitted_by_user_id: viewerUser.id,
  updated_at: '2026-06-22T00:00:00Z',
}

const knowledgeProposalListResponse: KnowledgeProposalListResponse = {
  items: [pendingKnowledgeProposal],
}

const sourceSummary: Source = {
  created_at: '2026-06-22T00:00:01Z',
  external_id: 'notes.md',
  extra_metadata: { content: '# Notes' },
  id: '22222222-2222-4222-8222-222222222222',
  project_id: projectId,
  source_type: 'markdown',
  tags: ['docs', 'local'],
  updated_at: '2026-06-22T00:00:01Z',
}

const citationSource: Source = {
  created_at: '2026-06-21T00:00:00Z',
  external_id: 'https://docs.local/runbook',
  extra_metadata: { owner: 'ops', title: 'Deployment runbook' },
  id: 'source-1',
  project_id: projectId,
  source_type: 'url',
  tags: ['runbook'],
  updated_at: '2026-06-21T00:00:00Z',
}

const sourceListResponse: SourceListResponse = {
  items: [sourceSummary],
}

const ingestionJob: IngestionJob = {
  attempts: 1,
  created_at: '2026-06-22T00:00:02Z',
  id: '33333333-3333-4333-8333-333333333333',
  job_type: 'ingest_source',
  last_error: 'missing content',
  locked_by: null,
  locked_until: null,
  max_attempts: 3,
  payload_json: { source_id: sourceSummary.id },
  priority: 0,
  project_id: projectId,
  run_after: '2026-06-22T00:00:02Z',
  status: 'blocked',
  updated_at: '2026-06-22T00:00:03Z',
}

const ingestionJobListResponse: IngestionJobListResponse = {
  items: [ingestionJob],
}

const processedIngestionRun: IngestionRunResponse = {
  created_document_version: true,
  document_id: '44444444-4444-4444-8444-444444444444',
  document_version_id: '55555555-5555-4555-8555-555555555555',
  error_message: null,
  job_id: ingestionJob.id,
  project_id: projectId,
  source_id: sourceSummary.id,
  status: 'processed',
  worker_id: 'frontend',
}

const observabilitySummary: ChatObservabilitySummary = {
  errors: {
    provider_error_count: 1,
    session_error_count: 2,
    top_messages: [{ count: 2, message: 'runner failed' }],
  },
  filters: {
    created_at_from: '2026-06-21T00:00:00Z',
    created_at_to: '2026-06-22T00:00:00Z',
    status: 'failed',
  },
  project_id: projectId,
  provider_usage: {
    groups: [
      {
        estimated_cost_usd: 0.08,
        input_count: null,
        input_tokens: 1200,
        latency_ms: {
          avg: 220.5,
          count: 8,
          max: 420,
          min: 120,
          p50: 210,
          p95: 410,
        },
        model: 'qwen-plus',
        operation: 'chat',
        output_tokens: 640,
        provider: 'qwen',
        record_count: 8,
        total_tokens: 1840,
      },
    ],
    missing_cost_count: 1,
    total_estimated_cost_usd: 0.1234,
    total_records: 18,
  },
  sessions: {
    by_status: {
      failed: 2,
      running: 0,
      succeeded: 10,
    },
    total: 12,
  },
}

const providerConnectionsResponse: ProviderConnectionListResponse = {
  items: [
    {
      base_url: 'https://dashscope.example.test/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding', 'rerank'],
      connection_id: 'qwen-hosted',
      connection_type: 'hosted',
      created_at: '2026-06-24T00:00:00Z',
      metadata: { label: 'Hosted Qwen' },
      provider: 'qwen',
      secrets: [
        {
          configured: true,
          connection_id: 'qwen-hosted',
          fingerprint: 'fingerprint',
          last_four: 'cret',
          secret_name: 'api_key',
          updated_at: '2026-06-24T00:00:01Z',
        },
      ],
      updated_at: '2026-06-24T00:00:00Z',
    },
    {
      base_url: 'http://localhost:11434/v1',
      capabilities: ['chat'],
      connection_id: 'local-chat',
      connection_type: 'local',
      created_at: '2026-06-24T00:00:00Z',
      metadata: null,
      provider: 'local_openai_compatible',
      secrets: [],
      updated_at: '2026-06-24T00:00:00Z',
    },
  ],
}

const runtimeSlotDefaultsResponse: RuntimeSlotDefaultListResponse = {
  items: [
    {
      connection_id: 'qwen-hosted',
      created_at: '2026-06-24T00:00:00Z',
      model_id: 'text-embedding-v4',
      parameters: null,
      slot: 'dense_embedding',
      updated_at: '2026-06-24T00:00:00Z',
    },
  ],
}

const chatModelsResponse: ChatModelListResponse = {
  items: [
    {
      connection_id: 'local-chat',
      created_at: '2026-06-24T00:00:00Z',
      is_default: true,
      model_id: 'llama3.1:8b',
      parameters: null,
      updated_at: '2026-06-24T00:00:00Z',
    },
  ],
}

const providerModelsResponse: ProviderModelListResponse = {
  items: [
    {
      capabilities: ['chat'],
      connection_id: 'qwen-hosted',
      created_at: '2026-06-24T00:00:00Z',
      last_seen_at: '2026-06-24T00:00:00Z',
      metadata: { object: 'model' },
      model_id: 'qwen-plus',
      pricing: null,
      updated_at: '2026-06-24T00:00:00Z',
    },
    {
      capabilities: ['dense_embedding', 'sparse_embedding'],
      connection_id: 'qwen-hosted',
      created_at: '2026-06-24T00:00:00Z',
      last_seen_at: '2026-06-24T00:00:00Z',
      metadata: { name: 'Qwen Embedding' },
      model_id: 'text-embedding-v4',
      pricing: { input_per_million_tokens_usd: 0.07 },
      updated_at: '2026-06-24T00:00:00Z',
    },
    {
      capabilities: ['chat'],
      connection_id: 'local-chat',
      created_at: '2026-06-24T00:00:00Z',
      last_seen_at: '2026-06-24T00:00:00Z',
      metadata: { object: 'model' },
      model_id: 'llama3.1:8b',
      pricing: null,
      updated_at: '2026-06-24T00:00:00Z',
    },
  ],
}

const projectRuntimeSettings: ProjectRuntimeSettings = {
  chat_models: [
    {
      connection_id: 'local-chat',
      is_default: true,
      model_id: 'llama3.1:8b',
      parameters: null,
      source: 'overridden',
    },
  ],
  chat_retrieval: {
    max_limit: 50,
    rerank_candidate_limit: 10,
    rerank_enabled: true,
    retrieval_limit: 5,
    source: 'project',
  },
  project_id: projectId,
  slots: [
    {
      connection_id: 'qwen-hosted',
      model_id: 'text-embedding-v4',
      parameters: null,
      slot: 'dense_embedding',
      source: 'inherited',
    },
    {
      connection_id: 'local-chat',
      model_id: 'llama3.1:8b',
      parameters: null,
      slot: 'chat',
      source: 'overridden',
    },
  ],
}

const emptySessionDetail: ChatSessionDetailResponse = {
  messages: [],
  provider_usage: [],
  retrieval_runs: [],
  session: {
    archived_at: null,
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    model_config: null,
    prompt_version: null,
    session_id: 'session-123',
    status: 'succeeded',
    title: null,
    title_is_custom: false,
    updated_at: '2026-06-21T00:00:01Z',
  },
  tool_calls: [],
}

const sessionDetailResponse: ChatSessionDetailResponse = {
  messages: [
    {
      content: 'What failed during deployment?',
      created_at: '2026-06-21T00:00:00Z',
      message_id: 'message-user-1',
      metadata: null,
      role: 'user',
    },
    {
      content: 'The import failed because the worker was not running.',
      created_at: '2026-06-21T00:00:01Z',
      message_id: 'message-assistant-1',
      metadata: null,
      role: 'assistant',
    },
  ],
  provider_usage: [
    {
      created_at: '2026-06-21T00:00:02Z',
      currency: 'USD',
      error_message: null,
      estimated_cost_usd: 0.0042,
      input_count: null,
      input_tokens: 120,
      latency_ms: 230,
      model: 'qwen-plus',
      operation: 'chat',
      output_tokens: 48,
      provider: 'qwen',
      provider_request_id: 'provider-request-1',
      provider_usage_id: 'usage-1',
      status: 'succeeded',
      total_tokens: 168,
      usage_source: 'response',
    },
  ],
  retrieval_runs: [
    {
      created_at: '2026-06-21T00:00:01Z',
      error_message: null,
      filters: null,
      latency_ms: 41,
      query: 'deployment import failure',
      retrieval_run_id: 'retrieval-run-1',
      retrieved_chunks: [
        {
          chunk_id: 'chunk-1',
          citation: {
            snippet: 'Confirm the worker is running before retrying the import.',
            source_id: 'source-1',
            source_external_id: 'https://docs.local/deploy',
          },
          created_at: '2026-06-21T00:00:01Z',
          dense_score: 0.84,
          lexical_score: null,
          rerank_score: null,
          retrieved_chunk_id: 'retrieved-chunk-1',
          rrf_score: null,
          rank: 1,
        },
      ],
      strategy: 'dense',
      tool_call_id: 'tool-call-1',
      top_k: 5,
      used_rerank: false,
    },
  ],
  session: {
    archived_at: null,
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    model_config: { chat_provider: 'qwen' },
    prompt_version: 'default',
    session_id: 'session-123',
    status: 'succeeded',
    title: 'Deployment question',
    title_is_custom: false,
    updated_at: '2026-06-21T00:00:02Z',
  },
  tool_calls: [
    {
      arguments: { query: 'deployment import failure' },
      created_at: '2026-06-21T00:00:01Z',
      error_message: null,
      latency_ms: 39,
      result_summary: { result_count: 1 },
      status: 'succeeded',
      tool_call_id: 'tool-call-1',
      tool_name: 'rag_search',
      updated_at: '2026-06-21T00:00:01Z',
    },
  ],
}

const unknownUsageSessionDetail: ChatSessionDetailResponse = {
  ...sessionDetailResponse,
  provider_usage: [
    {
      created_at: '2026-06-21T00:00:02Z',
      currency: null,
      error_message: null,
      estimated_cost_usd: null,
      input_count: null,
      input_tokens: null,
      latency_ms: null,
      model: 'qwen-plus',
      operation: 'chat',
      output_tokens: null,
      provider: 'qwen',
      provider_request_id: null,
      provider_usage_id: 'usage-unknown',
      status: 'succeeded',
      total_tokens: null,
      usage_source: 'response',
    },
  ],
}

function createDeferred<T>(): {
  promise: Promise<T>
  reject(reason?: unknown): void
  resolve(value: T): void
} {
  let reject!: (reason?: unknown) => void
  let resolve!: (value: T) => void
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })
  return { promise, reject, resolve }
}

async function openSettingsSubmodule(
  user: { click(element: Element): Promise<void> },
  moduleName: 'Authoring' | 'Observability' | 'Runtime',
  submoduleName: string,
) {
  await user.click(screen.getByRole('button', { name: 'Settings' }))
  const settingsNavigation = screen.getByRole('navigation', {
    name: 'Settings navigation',
  })
  await user.click(within(settingsNavigation).getByRole('button', { name: moduleName }))
  await user.click(
    within(settingsNavigation).getByRole('button', { name: submoduleName }),
  )
}

describe('App chat workspace', () => {
  test('renders with the local API fallback when no API base URL is configured', () => {
    render(<App />)

    expect(screen.getByRole('button', { name: /Project selector/i })).toBeTruthy()
    expect(screen.getByLabelText('Question')).toBeTruthy()
  })

  test('keeps primary sidebar navigation stable and renders chat sessions only in Chat', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary sidebar',
    })
    const navigation = within(sidebar).getByRole('navigation', {
      name: 'Primary navigation',
    })

    expect(
      within(navigation)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Chat', 'My account', 'Settings'])
    expect(within(sidebar).getByRole('heading', { name: 'Sesiones' })).toBeTruthy()

    await user.click(within(navigation).getByRole('button', { name: 'My account' }))

    expect(
      within(sidebar).getByRole('navigation', { name: 'My account navigation' }),
    ).toBeTruthy()
    expect(within(sidebar).queryByRole('heading', { name: 'Sesiones' })).toBeNull()

    await user.click(within(navigation).getByRole('button', { name: 'Settings' }))

    expect(
      within(sidebar).getByRole('navigation', { name: 'Settings navigation' }),
    ).toBeTruthy()
    expect(within(sidebar).queryByRole('heading', { name: 'Sesiones' })).toBeNull()
  })

  test('shows account modules in the sidebar without rendering fake memory state', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'My account' }))

    const accountNavigation = screen.getByRole('navigation', {
      name: 'My account navigation',
    })

    expect(
      within(accountNavigation)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Appearance', 'Memory'])
    const memoryButton = within(accountNavigation).getByRole('button', {
      name: 'Memory',
    }) as HTMLButtonElement
    expect(memoryButton.disabled).toBe(true)
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeTruthy()
    expect(screen.queryByText(/remembered/i)).toBeNull()
  })

  test('shows settings modules and submodules in the sidebar', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Settings' }))

    const settingsNavigation = screen.getByRole('navigation', {
      name: 'Settings navigation',
    })

    expect(within(settingsNavigation).getByRole('button', { name: 'Authoring' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Projects' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Users' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Knowledge' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Sources' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Observability' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Runtime' })).toBeTruthy()
    expect(screen.queryByRole('tablist', { name: 'Settings sections' })).toBeNull()
  })

  test('routes settings sidebar submodules to focused content', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Authoring', 'Users')
    expect(screen.getByRole('heading', { name: 'Users' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Content registry' })).toBeNull()

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    expect(screen.getByRole('heading', { name: 'Content registry' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    expect(screen.getByRole('heading', { name: 'Summary' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    expect(screen.getByRole('heading', { name: 'Connections' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Refresh runtime' })).toBeNull()
  })

  test('opens and closes the left sidebar with the burger control', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const toggle = screen.getByRole('button', { name: 'Collapse left sidebar' })
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(
      screen.getByRole('complementary', { name: 'Primary sidebar' }).className,
    ).toContain('app-sidebar-open')

    await user.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.getAttribute('aria-label')).toBe('Open left sidebar')
    expect(
      screen.getByRole('complementary', { name: 'Primary sidebar' }).className,
    ).toContain('app-sidebar-closed')
  })

  test('moves project selection into the sidebar above primary navigation', async () => {
    const user = userEvent.setup()
    const updateCurrentUserPreferences = vi.fn(async () => ({
      display_name: 'Viewer',
      id: '22222222-2222-4222-8222-222222222222',
      is_bootstrap: false,
      last_project_id: projectId,
      login: 'viewer@example.com',
      system_role: 'user',
    }))
    const client = createClientStub({
      listProjects: vi.fn(async () => projectListResponse),
      updateCurrentUserPreferences,
    })

    render(<App apiClient={client} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary sidebar',
    })
    const selector = await within(sidebar).findByRole('button', {
      name: /Project selector/i,
    })
    const navigation = within(sidebar).getByRole('navigation', {
      name: 'Primary navigation',
    })

    expect(
      selector.compareDocumentPosition(navigation) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.queryByRole('combobox', { name: 'Project' })).toBeNull()

    await user.click(selector)
    await user.click(screen.getByRole('option', { name: /Select project Demo/ }))

    expect(localStorage.getItem('adaptive-rag:last-project-id')).toBe(projectId)
    expect(updateCurrentUserPreferences).toHaveBeenCalledWith({
      last_project_id: projectId,
    })
    expect(screen.getByRole('button', { name: /Project selector: Demo/ })).toBeTruthy()
  })

  test('orders, filters and disables sidebar project options', async () => {
    const user = userEvent.setup()
    const inaccessibleAlpha: Project = {
      ...projectSummary,
      can_access: false,
      id: '99999999-9999-4999-8999-999999999999',
      name: 'Alpha Restricted',
    }
    const accessibleZulu: Project = {
      ...projectSummary,
      id: '22222222-2222-4222-8222-222222222222',
      name: 'Zulu Enabled',
    }
    const accessibleBeta: Project = {
      ...projectSummary,
      access_role: 'admin',
      id: '33333333-3333-4333-8333-333333333333',
      name: 'Beta Enabled',
    }
    const inaccessibleOmega: Project = {
      ...projectSummary,
      can_access: false,
      id: '88888888-8888-4888-8888-888888888888',
      name: 'Omega Restricted',
    }
    const client = createClientStub({
      listProjects: vi.fn(async () => ({
        items: [
          inaccessibleOmega,
          accessibleZulu,
          inaccessibleAlpha,
          accessibleBeta,
        ],
      })),
    })

    render(<App apiClient={client} />)

    await user.click(
      await screen.findByRole('button', { name: /Project selector/i }),
    )

    expect(
      within(screen.getByRole('listbox', { name: 'Projects' }))
        .getAllByRole('option')
        .map((option) => option.getAttribute('aria-label')),
    ).toEqual([
      'Select project Beta Enabled',
      'Select project Zulu Enabled',
      'Project Alpha Restricted. No tienes acceso para ese proyecto',
      'Project Omega Restricted. No tienes acceso para ese proyecto',
    ])

    const betaOption = screen.getByRole('option', {
      name: /Select project Beta Enabled/,
    })
    expect(betaOption.textContent).toBe('Beta Enabled')
    expect(betaOption.textContent).not.toContain(accessibleBeta.id)
    expect(betaOption.textContent).not.toContain('admin')

    const restrictedOption = screen.getByRole('option', {
      name: /Project Alpha Restricted\. No tienes acceso para ese proyecto/,
    }) as HTMLButtonElement
    expect(restrictedOption.disabled).toBe(true)
    expect(restrictedOption.textContent).toBe('Alpha Restricted')
    expect(restrictedOption.textContent).not.toContain(inaccessibleAlpha.id)
    expect(
      within(restrictedOption).getByLabelText(
        'No tienes acceso para ese proyecto',
      ),
    ).toBeTruthy()

    await user.type(screen.getByLabelText('Search projects'), 'omega')
    expect(screen.queryByRole('option', { name: /Beta Enabled/ })).toBeNull()
    expect(screen.getByRole('option', { name: /Omega Restricted/ })).toBeTruthy()
  })

  test('restores the last selected sidebar project for the returning user', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      listProjects: vi.fn(async () => projectListResponse),
    })

    const { unmount } = render(<App apiClient={client} />)

    await user.click(
      await screen.findByRole('button', { name: /Project selector/i }),
    )
    await user.click(screen.getByRole('option', { name: /Select project Demo/ }))
    expect(localStorage.getItem('adaptive-rag:last-project-id')).toBe(projectId)

    unmount()
    render(<App apiClient={client} />)

    expect(
      await screen.findByRole('button', { name: /Project selector: Demo/ }),
    ).toBeTruthy()
  })

  test('hydrates the last sidebar project from the authenticated account', async () => {
    const getCurrentUser = vi.fn(async () => ({
      display_name: 'Viewer',
      id: '22222222-2222-4222-8222-222222222222',
      is_bootstrap: false,
      last_project_id: projectId,
      login: 'viewer@example.com',
      system_role: 'user',
    }))
    const updateCurrentUserPreferences = vi.fn(async () => ({
      display_name: 'Viewer',
      id: '22222222-2222-4222-8222-222222222222',
      is_bootstrap: false,
      last_project_id: projectId,
      login: 'viewer@example.com',
      system_role: 'user',
    }))
    const client = createClientStub({
      getCurrentUser,
      listProjects: vi.fn(async () => projectListResponse),
      updateCurrentUserPreferences,
    })

    render(<App apiClient={client} />)

    expect(
      await screen.findByRole('button', { name: /Project selector: Demo/ }),
    ).toBeTruthy()
    expect(updateCurrentUserPreferences).not.toHaveBeenCalled()
  })

  test('submits current chat text as a knowledge proposal', async () => {
    const user = userEvent.setup()
    const submitKnowledgeProposal = vi.fn(async () => pendingKnowledgeProposal)

    render(
      <App
        apiClient={createClientStub({ submitKnowledgeProposal })}
        initialProjectId={projectId}
      />,
    )

    await user.type(
      screen.getByLabelText('Question'),
      'Document this deployment exception.',
    )
    await user.click(screen.getByRole('button', { name: 'Propose knowledge' }))

    await waitFor(() =>
      expect(submitKnowledgeProposal).toHaveBeenCalledWith(projectId, {
        proposed_text: 'Document this deployment exception.',
      }),
    )
  })

  test('creates users and assigns project membership from authoring', async () => {
    const user = userEvent.setup()
    const createUser = vi.fn(async () => viewerUser)
    const upsertProjectMembership = vi.fn(async () => viewerMembership)

    render(
      <App
        apiClient={createClientStub({
          createUser,
          listProjectMemberships: vi.fn(async () => membershipListResponse),
          listUsers: vi.fn(async () => userListResponse),
          upsertProjectMembership,
        })}
        initialProjectId={projectId}
      />,
    )

    await openSettingsSubmodule(user, 'Authoring', 'Users')
    await user.type(screen.getByLabelText('User login'), viewerUser.login)
    await user.type(screen.getByLabelText('Display name'), viewerUser.display_name)
    await user.type(screen.getByLabelText('Access token'), 'viewer-token')
    await user.click(screen.getByRole('button', { name: 'Create user' }))

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith({
        access_token: 'viewer-token',
        display_name: viewerUser.display_name,
        login: viewerUser.login,
        system_role: 'user',
      }),
    )

    await user.type(screen.getByLabelText('Member user ID'), viewerUser.id)
    await user.selectOptions(screen.getByLabelText('Project role'), 'admin')
    await user.click(screen.getByRole('button', { name: 'Save membership' }))

    await waitFor(() =>
      expect(upsertProjectMembership).toHaveBeenCalledWith(
        projectId,
        viewerUser.id,
        { role: 'admin' },
      ),
    )
  })

  test('reviews pending knowledge proposals from authoring', async () => {
    const user = userEvent.setup()
    const refineKnowledgeProposal = vi.fn(async () => ({
      ...pendingKnowledgeProposal,
      refined_text: 'Refined escalation runbook.',
    }))
    const approveKnowledgeProposal = vi.fn(async () => ({
      ...pendingKnowledgeProposal,
      status: 'approved',
    }))
    const rejectKnowledgeProposal = vi.fn(async () => ({
      ...pendingKnowledgeProposal,
      status: 'rejected',
    }))

    render(
      <App
        apiClient={createClientStub({
          approveKnowledgeProposal,
          listKnowledgeProposals: vi.fn(async () => knowledgeProposalListResponse),
          refineKnowledgeProposal,
          rejectKnowledgeProposal,
        })}
        initialProjectId={projectId}
      />,
    )

    await openSettingsSubmodule(user, 'Authoring', 'Knowledge')
    await user.click(screen.getByRole('button', { name: 'Refresh proposals' }))

    expect(
      await screen.findByText('Document the escalation runbook from chat.'),
    ).toBeTruthy()

    await user.type(screen.getByLabelText('Refined text'), 'Refined escalation runbook.')
    await user.click(screen.getByRole('button', { name: 'Refine proposal' }))

    await waitFor(() =>
      expect(refineKnowledgeProposal).toHaveBeenCalledWith(
        projectId,
        pendingKnowledgeProposal.id,
        { refined_text: 'Refined escalation runbook.' },
      ),
    )

    await user.click(screen.getByRole('button', { name: 'Approve proposal' }))

    await waitFor(() =>
      expect(approveKnowledgeProposal).toHaveBeenCalledWith(
        projectId,
        pendingKnowledgeProposal.id,
        {
          refined_text: 'Refined escalation runbook.',
          review_note: null,
        },
      ),
    )

    await user.type(screen.getByLabelText('Reject reason'), 'Needs source owner.')
    await user.click(screen.getByRole('button', { name: 'Reject proposal' }))

    await waitFor(() =>
      expect(rejectKnowledgeProposal).toHaveBeenCalledWith(
        projectId,
        pendingKnowledgeProposal.id,
        { reason: 'Needs source owner.' },
      ),
    )
  })

  test('opens and closes the right dock from composer controls', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    expect(
      screen.queryByRole('complementary', { name: 'Workspace inspector' }),
    ).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    expect(
      screen.getByRole('complementary', { name: 'Workspace inspector' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected'),
    ).toBe('true')

    await user.click(screen.getByRole('button', { name: 'Open minimap sidebar' }))

    expect(
      screen.getByRole('tab', { name: 'Minimap' }).getAttribute('aria-selected'),
    ).toBe('true')
    expect(
      screen
        .getByRole('button', { name: 'Open minimap sidebar' })
        .getAttribute('aria-pressed'),
    ).toBe('true')

    await user.click(screen.getByRole('button', { name: 'Close right sidebar' }))

    expect(
      screen.queryByRole('complementary', { name: 'Workspace inspector' }),
    ).toBeNull()
  })

  test('renders the right dock inline on xl viewports and as an overlay below xl', async () => {
    const user = userEvent.setup()

    setViewportWidth(1400)
    const { unmount } = render(
      <App apiClient={createClientStub({})} initialProjectId={projectId} />,
    )

    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    expect(
      screen
        .getByRole('complementary', { name: 'Workspace inspector' })
        .className,
    ).toContain('workspace-inspector-inline')
    expect(screen.queryByTestId('workspace-inspector-backdrop')).toBeNull()
    expect(document.querySelector('.chat-workspace-grid')?.className).toContain(
      'chat-workspace-grid-docked',
    )

    unmount()
    setViewportWidth(900)
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    expect(
      screen
        .getByRole('complementary', { name: 'Workspace inspector' })
        .className,
    ).toContain('workspace-inspector-overlay')
    expect(screen.getByTestId('workspace-inspector-backdrop')).toBeTruthy()
    expect(document.querySelector('.chat-workspace-grid')?.className).not.toContain(
      'chat-workspace-grid-docked',
    )
  })

  test('auto-follows streaming chat until the user scrolls away from the bottom', async () => {
    const user = userEvent.setup()
    const finalResponse = createDeferred<ChatResponseBody>()
    let streamHandlers: ChatStreamHandlers | undefined
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async (_projectId, _body, handlers) => {
        streamHandlers = handlers
        handlers.onSessionStarted?.('session-stream')
        return finalResponse.promise
      }),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    const transcript = screen.getByRole('region', { name: 'Chat transcript' })
    Object.defineProperty(transcript, 'clientHeight', {
      configurable: true,
      value: 240,
    })
    Object.defineProperty(transcript, 'scrollHeight', {
      configurable: true,
      value: 600,
    })

    transcript.scrollTop = 360
    fireEvent.scroll(transcript)

    await act(async () => {
      streamHandlers?.onAnswerDelta?.('Partial streaming answer')
    })

    expect(transcript.scrollTop).toBe(600)

    transcript.scrollTop = 80
    fireEvent.scroll(transcript)
    Object.defineProperty(transcript, 'scrollHeight', {
      configurable: true,
      value: 700,
    })

    await act(async () => {
      streamHandlers?.onAnswerDelta?.(' while reading earlier context')
    })

    expect(transcript.scrollTop).toBe(80)

    await act(async () => {
      finalResponse.resolve(chatResponse)
    })
    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
  })

  test('renders the transcript action as an icon-only composer button', () => {
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const transcriptButton = screen.getByRole('button', {
      name: 'Transcript unavailable',
    })

    expect(transcriptButton.querySelector('svg')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Dictate' })).toBeNull()
  })

  test('opens appearance from my account and applies the selected theme globally', async () => {
    const user = userEvent.setup()
    const client = createClientStub({})

    render(<App apiClient={client} initialProjectId={projectId} />)

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.querySelector('main')?.className).toContain('app-shell')

    await user.click(screen.getByRole('button', { name: 'My account' }))

    const appearancePanel = screen.getByRole('region', { name: 'Appearance' })
    expect(within(appearancePanel).getByRole('heading', { name: 'Appearance' })).toBeTruthy()
    expect(within(appearancePanel).getByText('My account')).toBeTruthy()
    expect(screen.getByText('Choose the interface palette.')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /Light/ }).getAttribute('aria-pressed'),
    ).toBe('false')
    const darkThemeButton = screen.getByRole('button', { name: /Dark/ })
    expect(darkThemeButton.getAttribute('aria-pressed')).toBe('true')
    const purpleThemeButton = screen.getByRole('button', { name: /Purple/ })
    expect(
      purpleThemeButton.getAttribute('aria-pressed'),
    ).toBe('false')
    expect(
      screen.getByText('High-contrast purple workspace palette.'),
    ).toBeTruthy()
    expect(document.body.textContent ?? '').not.toMatch(
      new RegExp(['be', 'flow'].join(''), 'i'),
    )

    await user.click(purpleThemeButton)

    expect(document.documentElement.getAttribute('data-theme')).toBe('purple')
    expect(purpleThemeButton.getAttribute('aria-pressed')).toBe('true')
    expect(
      darkThemeButton.querySelector<HTMLElement>('.theme-swatch')?.style
        .background,
    ).toBe('rgb(0, 0, 0)')
    expect(
      darkThemeButton.querySelector<HTMLElement>('.theme-swatch-accent')?.style
        .background,
    ).toBe('rgb(245, 245, 245)')

    await user.click(screen.getByRole('button', { name: /Light/ }))

    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('adaptive-rag-theme')).toBe('light')

    await openSettingsSubmodule(user, 'Authoring', 'Projects')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.querySelector('main')?.className).toContain('app-shell')

    await user.click(screen.getByRole('button', { name: /^Chat$/ }))
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.querySelector('main')?.className).toContain('app-shell')
  })

  test('hydrates the global theme from local storage', async () => {
    const user = userEvent.setup()
    localStorage.setItem('adaptive-rag-theme', 'dark')
    const client = createClientStub({})

    render(<App apiClient={client} initialProjectId={projectId} />)

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    await user.click(screen.getByRole('button', { name: 'My account' }))

    expect(
      screen.getByRole('button', { name: /Dark/ }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: /Purple/ }).getAttribute(
        'aria-pressed',
      ),
    ).toBe('false')
  })

  test('creates a project and source from the authoring workspace', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      createProject: vi.fn(async () => projectSummary),
      createSource: vi.fn(async () => sourceSummary),
      listProjects: vi.fn(async () => projectListResponse),
      listSources: vi.fn(async () => sourceListResponse),
    })

    render(<App apiClient={client} />)

    await openSettingsSubmodule(user, 'Authoring', 'Projects')
    expect(await screen.findByText('Demo')).toBeTruthy()

    await user.type(screen.getByLabelText('Project name'), 'Demo')
    await user.click(screen.getByRole('button', { name: 'Create project' }))

    expect(client.createProject).toHaveBeenCalledWith({ name: 'Demo' })
    expect((await screen.findAllByText(projectId)).length).toBeGreaterThanOrEqual(1)

    await user.selectOptions(screen.getByLabelText('Source type'), 'markdown')
    await user.type(screen.getByLabelText('External ID'), 'notes.md')
    await user.type(screen.getByLabelText('Content'), '# Notes')
    await user.type(screen.getByLabelText('Tags'), 'docs, local')
    await user.click(screen.getByRole('button', { name: 'Create source' }))

    expect(client.createSource).toHaveBeenCalledWith(projectId, {
      external_id: 'notes.md',
      extra_metadata: { content: '# Notes' },
      source_type: 'markdown',
      tags: ['docs', 'local'],
    })
    expect(await screen.findByText('notes.md')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Chat' }))
    expect(screen.getByRole('button', { name: /Project selector: Demo/ })).toBeTruthy()
  })

  test('runs ingestion operations from the authoring workspace', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      enqueueIngestionJob: vi.fn(async () => ({
        ...ingestionJob,
        last_error: null,
        status: 'queued',
      })),
      listIngestionJobs: vi.fn(async () => ingestionJobListResponse),
      listSources: vi.fn(async () => sourceListResponse),
      retryIngestionJob: vi.fn(async () => ({
        ...ingestionJob,
        last_error: null,
        status: 'queued',
      })),
      runNextIngestionJob: vi.fn(async () => processedIngestionRun),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    await user.click(screen.getByRole('button', { name: 'Refresh sources' }))
    expect(await screen.findByText('notes.md')).toBeTruthy()

    await user.click(
      screen.getByRole('button', { name: 'Enqueue ingestion for notes.md' }),
    )

    expect(client.enqueueIngestionJob).toHaveBeenCalledWith(
      projectId,
      sourceSummary.id,
    )
    expect(await screen.findByText('queued')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Refresh jobs' }))

    expect(client.listIngestionJobs).toHaveBeenCalledWith(projectId, {
      job_type: 'ingest_source',
    })
    expect(await screen.findByText('blocked')).toBeTruthy()
    expect(screen.getByText('missing content')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Run next job' }))

    expect(client.runNextIngestionJob).toHaveBeenCalledWith(projectId)
    expect(await screen.findByText('processed')).toBeTruthy()

    await user.click(
      screen.getByRole('button', {
        name: `Retry ingestion job ${ingestionJob.id}`,
      }),
    )

    expect(client.retryIngestionJob).toHaveBeenCalledWith(projectId, ingestionJob.id)
  })

  test('keeps compact workspace context visible across workspace views', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      listProjects: vi.fn(async () => projectListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    expect(screen.getByRole('heading', { name: 'Nuevo chat' })).toBeTruthy()
    expect(screen.queryByText('Selected project')).toBeNull()
    expect(screen.queryByText('dense default')).toBeNull()

    await openSettingsSubmodule(user, 'Authoring', 'Projects')
    await user.click(await screen.findByRole('button', { name: 'Select Demo' }))

    expect(screen.getByRole('heading', { name: 'Nuevo chat' })).toBeTruthy()
    expect(screen.getAllByText('Demo').length).toBeGreaterThanOrEqual(1)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    expect((screen.getByLabelText('Project ID') as HTMLInputElement).value).toBe(
      projectId,
    )
    expect(screen.getByRole('heading', { name: 'Nuevo chat' })).toBeTruthy()
    expect(screen.queryByText('Selected project')).toBeNull()
  })

  test('frames chat as dense retrieval without advanced mode controls', () => {
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    expect(screen.getByLabelText('Retrieval limit')).toBeTruthy()
    expect(
      screen.queryByRole('region', { name: 'Chat retrieval mode' }),
    ).toBeNull()
    expect(
      screen.queryByRole('combobox', { name: /retrieval strategy/i }),
    ).toBeNull()
    expect(screen.queryByText('hybrid_rrf')).toBeNull()
    expect(screen.queryByText('dense_sparse')).toBeNull()
    expect(screen.queryByText('graph')).toBeNull()
  })

  test('shows explicit ingestion next steps and job operation metadata', async () => {
    const user = userEvent.setup()
    const idleRun: IngestionRunResponse = {
      created_document_version: null,
      document_id: null,
      document_version_id: null,
      error_message: null,
      job_id: null,
      project_id: projectId,
      source_id: null,
      status: 'idle',
      worker_id: 'frontend',
    }
    const client = createClientStub({
      listIngestionJobs: vi.fn(async () => ingestionJobListResponse),
      listSources: vi.fn(async () => sourceListResponse),
      runNextIngestionJob: vi.fn(async () => idleRun),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    await user.click(screen.getByRole('button', { name: 'Refresh sources' }))

    expect(await screen.findByText('Ready to queue ingestion')).toBeTruthy()
    expect(screen.getByText('Queue ingestion when this source should be indexed.')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Refresh jobs' }))

    expect(await screen.findByText('attempt 1 of 3')).toBeTruthy()
    expect(screen.getByText('run after 2026-06-22T00:00:02Z')).toBeTruthy()
    expect(screen.getByText('unlocked')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Run next job' }))

    expect(await screen.findByText('Last run idle')).toBeTruthy()
    expect(screen.getByText('No ingestion job was processed.')).toBeTruthy()
  })

  test('submits a chat question and renders response details', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChatStream).toHaveBeenCalledWith(
      projectId,
      {
        message: 'How do I retry?',
      },
      expect.any(Object),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(client.askChat).not.toHaveBeenCalled()
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })
    expect(
      screen.getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText('score 0.88')).toBeTruthy()
    expect(screen.getByText('url source')).toBeTruthy()
    expect(screen.getByText('version 2')).toBeTruthy()
    expect(screen.getByText('chars 12-98')).toBeTruthy()
    expect(screen.getByText('rag_search')).toBeTruthy()
    expect(
      screen.getByRole('heading', { name: 'Deployment question' }),
    ).toBeTruthy()
    expect(
      screen
        .getByRole('button', { name: 'Abrir sesión Deployment question' })
        .closest('.session-row')?.className,
    ).toContain('session-row-selected')
  })

  test('sends a chat retrieval limit override only when the field is filled', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    fireEvent.change(screen.getByLabelText('Retrieval limit'), {
      target: { value: '12' },
    })
    await user.type(screen.getByLabelText('Question'), 'How wide should search be?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChatStream).toHaveBeenCalledWith(
      projectId,
      {
        message: 'How wide should search be?',
        retrieval_limit: 12,
      },
      expect.any(Object),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  test('adds a streaming session to the sidebar as soon as it starts', async () => {
    const user = userEvent.setup()
    const finalResponse = createDeferred<ChatResponseBody>()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async (_projectId, _body, handlers) => {
        handlers.onSessionStarted?.('session-stream')
        return finalResponse.promise
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Start a fresh session')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    const sessionButton = await screen.findByRole('button', {
      name: 'Abrir sesión Start a fresh session',
    })
    expect(sessionButton.closest('.session-row')?.className).toContain(
      'session-row-selected',
    )

    await act(async () => {
      finalResponse.resolve({ ...chatResponse, session_id: 'session-stream' })
    })
  })

  test('opens source viewer from a chat citation using the citation source id', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      getSource: vi.fn(async () => citationSource),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await screen.findByText(chatResponse.answer)

    await user.click(screen.getByRole('button', { name: 'Open minimap sidebar' }))
    expect(
      screen.getByRole('tab', { name: 'Minimap' }).getAttribute('aria-selected'),
    ).toBe('true')

    await user.click(
      screen.getByRole('button', {
        name: 'View source https://docs.local/runbook',
      }),
    )

    expect(client.getSource).toHaveBeenCalledWith(projectId, 'source-1')
    expect(
      screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected'),
    ).toBe('true')
    const viewer = await screen.findByRole('region', { name: 'Source viewer' })
    expect(within(viewer).getByText('https://docs.local/runbook')).toBeTruthy()
    expect(within(viewer).getByText('url')).toBeTruthy()
    expect(within(viewer).getByText('runbook')).toBeTruthy()
    expect(
      within(viewer).getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(within(viewer).getByText('Deployment runbook')).toBeTruthy()
    expect(within(viewer).getByText('ops')).toBeTruthy()
  })

  test('keeps chat response visible when source lookup fails', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      getSource: vi.fn(async () => {
        throw new ApiClientError('source not found', {
          detail: 'source not found',
          status: 404,
        })
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await screen.findByText(chatResponse.answer)

    await user.click(
      screen.getByRole('button', {
        name: 'View source https://docs.local/runbook',
      }),
    )

    const viewer = await screen.findByRole('region', { name: 'Source viewer' })
    expect(within(viewer).getByRole('alert').textContent).toContain(
      'source not found',
    )
    expect(
      within(viewer).getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText(chatResponse.answer)).toBeTruthy()
    expect(
      screen.getAllByText('Restart the worker before retrying the import.')
        .length,
    ).toBeGreaterThanOrEqual(2)
  })

  test('shows speech input as unsupported when browser STT is unavailable', () => {
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const button = screen.getByRole('button', {
      name: 'Transcript unavailable',
    }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
    expect(
      screen.getByText('Speech recognition is not supported in this browser.'),
    ).toBeTruthy()
  })

  test('uses browser speech recognition to fill the chat question', async () => {
    installFakeSpeechRecognition()
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Start transcript' }))
    expect(FakeSpeechRecognition.latest?.start).toHaveBeenCalled()

    await act(async () => {
      FakeSpeechRecognition.latest?.onresult?.({
        results: [[{ transcript: 'How do I retry from voice?' }]],
      })
    })

    const question = screen.getByLabelText('Question') as HTMLTextAreaElement
    expect(question.value).toBe('How do I retry from voice?')
    expect(screen.getByText('Voice transcript added.')).toBeTruthy()
  })

  test('shows speech recognition errors without submitting chat', async () => {
    installFakeSpeechRecognition()
    const user = userEvent.setup()
    const client = createClientStub({})

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Start transcript' }))
    await act(async () => {
      FakeSpeechRecognition.latest?.onerror?.({ error: 'not-allowed' })
    })

    expect(screen.getByRole('alert').textContent).toContain(
      'Speech recognition error: not-allowed',
    )
    expect(client.askChatStream).not.toHaveBeenCalled()
  })

  test('renders streaming deltas before the final response resolves', async () => {
    const user = userEvent.setup()
    const finalResponse = createDeferred<ChatResponseBody>()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async (_projectId, _body, handlers) => {
        handlers.onSessionStarted?.('session-stream')
        handlers.onToolCall?.({
          limit: 2,
          name: 'retrieval.search',
          query: 'streaming evidence',
          result_count: 1,
        })
        handlers.onAnswerDelta?.('Partial streaming answer')
        return finalResponse.promise
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How does streaming work?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('Partial streaming answer')).toBeTruthy()
    expect(screen.getByText('Streaming answer')).toBeTruthy()
    expect(screen.getByText('Retrieval in progress')).toBeTruthy()
    expect(
      screen.getByText('Citations appear after the final response.'),
    ).toBeTruthy()
    expect(screen.queryByText('No citations returned.')).toBeNull()
    expect(screen.getByText('streaming evidence')).toBeTruthy()

    finalResponse.resolve(chatResponse)

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChat).not.toHaveBeenCalled()
  })

  test('falls back to the non-streaming chat request before stream events open', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(async () => chatResponse),
      askChatStream: vi.fn(async () => {
        throw new TypeError('stream unavailable')
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChatStream).toHaveBeenCalled()
    expect(client.askChat).toHaveBeenCalledWith(projectId, {
      message: 'How do I retry?',
    })
  })

  test('cancels an open streaming request without rendering a final answer', async () => {
    const user = userEvent.setup()
    let capturedSignal: AbortSignal | undefined
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn((_projectId, _body, _handlers, options) => {
        capturedSignal = options?.signal
        return new Promise<ChatResponseBody>((_resolve, reject) => {
          capturedSignal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          })
        })
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Cancel this request')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await user.click(await screen.findByRole('button', { name: 'Cancel' }))

    expect(capturedSignal?.aborted).toBe(true)
    expect(await screen.findByRole('button', { name: 'Ask' })).toBeTruthy()
    expect(screen.queryByText(chatResponse.answer)).toBeNull()
    expect(client.askChat).not.toHaveBeenCalled()
  })

  test('shows request errors without clearing the draft question', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(async () => {
        throw new ApiClientError('backend unavailable', {
          detail: 'backend unavailable',
          status: 503,
        })
      }),
      askChatStream: vi.fn(async () => {
        throw new TypeError('stream unavailable')
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Why did it fail?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('backend unavailable')
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(
      'Why did it fail?',
    )
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })
  })

  test('filters project sessions by active training and archived tabs', async () => {
    const user = userEvent.setup()
    const archivedResponse: ChatSessionListResponse = {
      items: [
        {
          ...sessionListResponse.items[0],
          archived_at: '2026-06-21T00:05:00Z',
          has_approved_training: false,
          session_id: 'session-archived',
          title: 'Archived question',
        },
      ],
      next_cursor: null,
    }
    const client = createClientStub({
      listChatSessions: vi.fn(async (_projectId, params) =>
        params?.archived === true ? archivedResponse : sessionListResponse,
      ),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    const navigation = screen.getByRole('complementary', {
      name: 'Sesiones',
    })
    expect(
      await within(navigation).findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    ).toBeTruthy()
    expect(within(navigation).getByTitle('Training')).toBeTruthy()
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })

    await user.click(within(navigation).getByRole('button', { name: 'TRAIN' }))
    expect(
      await within(navigation).findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    ).toBeTruthy()

    await user.click(within(navigation).getByRole('button', { name: 'ARCHIVADOS' }))
    await waitFor(() =>
      expect(client.listChatSessions).toHaveBeenLastCalledWith(projectId, {
        archived: true,
        limit: 15,
      }),
    )
    expect(
      await within(navigation).findByRole('button', {
        name: 'Abrir sesión Archived question',
      }),
    ).toBeTruthy()
    expect(
      within(navigation).queryByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    ).toBeNull()
  })

  test('loads more sessions in windows of fifteen', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      listChatSessions: vi.fn(async (_projectId, params) => ({
        ...sessionListResponse,
        next_cursor: params?.limit === 15 ? 'next-page' : null,
      })),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await screen.findByRole('button', {
      name: 'Abrir sesión Deployment question',
    })
    await user.click(screen.getByRole('button', { name: 'ver más' }))

    await waitFor(() =>
      expect(client.listChatSessions).toHaveBeenLastCalledWith(projectId, {
        archived: false,
        limit: 30,
      }),
    )
  })

  test('renames and archives a session from the hover menu actions', async () => {
    const user = userEvent.setup()
    const updateChatSessionTitle = vi.fn(async () => ({
      session_id: 'session-123',
      title: 'Renamed session',
      title_is_custom: true,
    }))
    const archiveChatSession = vi.fn(async () => undefined)
    const client = createClientStub({
      archiveChatSession,
      listChatSessions: vi.fn(async () => sessionListResponse),
      updateChatSessionTitle,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await screen.findByRole('button', {
      name: 'Abrir sesión Deployment question',
    })
    await user.click(
      screen.getByRole('button', { name: 'Opciones de Deployment question' }),
    )
    await user.click(screen.getByRole('button', { name: 'renombrar' }))
    const input = screen.getByLabelText('Nuevo nombre de sesión')
    await user.clear(input)
    await user.type(input, 'Renamed session{Enter}')

    expect(updateChatSessionTitle).toHaveBeenCalledWith(
      projectId,
      'session-123',
      'Renamed session',
    )

    await user.click(
      screen.getByRole('button', { name: 'Opciones de Deployment question' }),
    )
    await user.click(screen.getByRole('button', { name: 'Archivar' }))

    expect(archiveChatSession).toHaveBeenCalledWith(projectId, 'session-123')
  })

  test('selects a history session as the active chat without opening the inspector', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )

    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })
    expect(client.getChatSession).toHaveBeenCalledWith(projectId, 'session-123')
    expect(
      screen.queryByRole('complementary', { name: 'Workspace inspector' }),
    ).toBeNull()
    expect(screen.getByLabelText('Question')).toBeTruthy()
    const transcript = screen.getByRole('region', { name: 'Chat transcript' })
    expect(
      await within(transcript).findByText(
        'The import failed because the worker was not running.',
      ),
    ).toBeTruthy()
    expect(within(transcript).getByText('session-123')).toBeTruthy()
  })

  test('starts a blank chat session from the sidebar', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await screen.findByText('The import failed because the worker was not running.')

    await user.click(screen.getByRole('button', { name: 'nuevo chat' }))

    expect(
      screen
        .getByRole('button', { name: 'Abrir sesión Deployment question' })
        .closest('.session-row')?.className,
    ).not.toContain(
      'session-row-selected',
    )
    expect(screen.getByText('No response yet.')).toBeTruthy()
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(
      '',
    )
  })

  test('refreshes history and renders selected session detail read-only', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    const sessionMessages = await screen.findByRole('list', {
      name: 'Session messages',
    })
    expect(
      within(sessionMessages).getByText(
        'The import failed because the worker was not running.',
      ),
    ).toBeTruthy()
    const sessionDetail = screen.getByRole('region', {
      name: 'Selected session detail',
    })
    expect(within(sessionDetail).getByText('rag_search')).toBeTruthy()
    expect(within(sessionDetail).getByText('deployment import failure')).toBeTruthy()
    expect(within(sessionDetail).getByText('default dense retrieval')).toBeTruthy()
    expect(within(sessionDetail).getByText('latency 41 ms')).toBeTruthy()
    expect(
      within(sessionDetail).getByText(
        'Confirm the worker is running before retrying the import.',
      ),
    ).toBeTruthy()
    expect(within(sessionDetail).getByText('rank 1')).toBeTruthy()
    expect(within(sessionDetail).getByText('dense score 0.84')).toBeTruthy()
    expect(within(sessionDetail).getByText('qwen / qwen-plus')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Replay' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  test('opens source viewer from a historical retrieved chunk', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      getSource: vi.fn(async () => citationSource),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    const sessionDetail = await screen.findByRole('region', {
      name: 'Selected session detail',
    })
    await user.click(
      within(sessionDetail).getByRole('button', {
        name: 'View source https://docs.local/deploy',
      }),
    )

    expect(client.getSource).toHaveBeenCalledWith(projectId, 'source-1')
    const viewer = await screen.findByRole('region', { name: 'Source viewer' })
    expect(within(viewer).getByText('https://docs.local/runbook')).toBeTruthy()
    expect(
      within(viewer).getByText(
        'Confirm the worker is running before retrying the import.',
      ),
    ).toBeTruthy()
    expect(within(viewer).getByText('Deployment runbook')).toBeTruthy()
    expect(within(viewer).getByText('ops')).toBeTruthy()
  })

  test('summarizes selected session context and provider usage', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    const context = await screen.findByRole('region', {
      name: 'Session context',
    })
    expect(within(context).getByText('prompt default')).toBeTruthy()
    expect(within(context).getByText('qwen-plus')).toBeTruthy()
    expect(within(context).getByText('$0.0042')).toBeTruthy()
    expect(within(context).getByText('168 tokens')).toBeTruthy()
    expect(within(context).getByText('230 ms')).toBeTruthy()
  })

  test('keeps missing selected session usage values visible as unknown', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => unknownUsageSessionDetail),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    const context = await screen.findByRole('region', {
      name: 'Session context',
    })
    expect(within(context).getByText('unknown cost')).toBeTruthy()
    expect(within(context).getByText('unknown tokens')).toBeTruthy()
    expect(within(context).getByText('unknown latency')).toBeTruthy()
  })

  test('renders conversation minimap from persisted messages and focuses messages', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open minimap sidebar' }))

    const minimap = await screen.findByRole('navigation', {
      name: 'Conversation minimap',
    })
    expect(
      within(minimap).getByRole('button', {
        name: 'user: What failed during deployment?',
      }),
    ).toBeTruthy()

    await user.click(
      within(minimap).getByRole('button', {
        name: 'assistant: The import failed because the worker was not running.',
      }),
    )

    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByRole('article', { name: 'assistant message' }),
      ),
    )
    expect(
      screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected'),
    ).toBe('true')
  })

  test('renders internal action stepper from stored audit records read-only', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    const stepper = await screen.findByRole('region', {
      name: 'Internal action stepper',
    })
    expect(within(stepper).getByText('tool call succeeded')).toBeTruthy()
    expect(within(stepper).getByText('retrieval dense')).toBeTruthy()
    expect(within(stepper).getByText('provider usage succeeded')).toBeTruthy()
    expect(within(stepper).getByText('rag_search')).toBeTruthy()
    expect(within(stepper).getByText('deployment import failure')).toBeTruthy()
    expect(within(stepper).getByText('qwen-plus')).toBeTruthy()
    expect(within(stepper).getByText('39 ms')).toBeTruthy()
    expect(within(stepper).getByText('rank 1')).toBeTruthy()
    expect(within(stepper).getByText(/0\.0042/)).toBeTruthy()
    expect(within(stepper).queryByRole('button', { name: /replay/i })).toBeNull()
  })

  test('shows session detail errors without clearing the session list', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => {
        throw new ApiClientError('chat session not found', {
          detail: 'chat session not found',
          status: 404,
        })
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open context sidebar' }))

    expect(await screen.findByText('chat session not found')).toBeTruthy()
    expect(
      screen.getByRole('button', {
        name: 'Abrir sesión Deployment question',
      }),
    ).toBeTruthy()
  })

  test('refreshes observability with filters and renders metric cards', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    await user.type(
      screen.getByLabelText('Created from'),
      '2026-06-21T00:00:00Z',
    )
    await user.type(
      screen.getByLabelText('Created to'),
      '2026-06-22T00:00:00Z',
    )
    await user.selectOptions(screen.getByLabelText('Status'), 'failed')
    await user.click(screen.getByRole('button', { name: 'Refresh summary' }))

    expect(client.getChatObservabilitySummary).toHaveBeenCalledWith(projectId, {
      created_at_from: '2026-06-21T00:00:00Z',
      created_at_to: '2026-06-22T00:00:00Z',
      status: 'failed',
    })
    const metrics = await screen.findByLabelText('Chat observability metrics')
    expect(within(metrics).getByText('12')).toBeTruthy()
    expect(within(metrics).getByText('18')).toBeTruthy()
    expect(within(metrics).getByText('$0.1234')).toBeTruthy()
    expect(within(metrics).getByText('3')).toBeTruthy()
    expect(within(metrics).getByText('410 ms')).toBeTruthy()
  })

  test('refreshes observability without sending empty filters', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    await user.click(screen.getByRole('button', { name: 'Refresh summary' }))

    expect(client.getChatObservabilitySummary).toHaveBeenCalledWith(projectId, {
      created_at_from: null,
      created_at_to: null,
      status: null,
    })
    expect(await screen.findByText('12')).toBeTruthy()
  })

  test('renders observability breakdown sections from the summary', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    await user.click(screen.getByRole('button', { name: 'Refresh summary' }))

    const statusSection = await screen.findByRole('region', {
      name: 'Status breakdown',
    })
    expect(within(statusSection).getByText('succeeded')).toBeTruthy()
    expect(within(statusSection).getByText('10 sessions')).toBeTruthy()
    expect(within(statusSection).getByText('failed')).toBeTruthy()
    expect(within(statusSection).getByText('2 sessions')).toBeTruthy()

    const errorsSection = screen.getByRole('region', { name: 'Error messages' })
    expect(within(errorsSection).getByText('runner failed')).toBeTruthy()
    expect(within(errorsSection).getByText('2 occurrences')).toBeTruthy()

    const providerSection = screen.getByRole('region', { name: 'Provider usage' })
    expect(within(providerSection).getByText('chat')).toBeTruthy()
    expect(within(providerSection).getByText('qwen')).toBeTruthy()
    expect(within(providerSection).getByText('qwen-plus')).toBeTruthy()
    expect(within(providerSection).getByText('1,840')).toBeTruthy()

    const healthSection = screen.getByRole('region', { name: 'Session health' })
    expect(within(healthSection).getByText('83.3% success')).toBeTruthy()
  })

  test('renders empty breakdown states when summary groups are absent', async () => {
    const user = userEvent.setup()
    const emptyBreakdownSummary: ChatObservabilitySummary = {
      ...observabilitySummary,
      errors: {
        provider_error_count: 0,
        session_error_count: 0,
        top_messages: [],
      },
      provider_usage: {
        groups: [],
        missing_cost_count: 0,
        total_estimated_cost_usd: 0,
        total_records: 0,
      },
      sessions: {
        by_status: {},
        total: 0,
      },
    }
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => emptyBreakdownSummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    await user.click(screen.getByRole('button', { name: 'Refresh summary' }))

    expect(await screen.findByText('No status data yet.')).toBeTruthy()
    expect(screen.getByText('No provider usage groups yet.')).toBeTruthy()
    expect(screen.getByText('No error messages yet.')).toBeTruthy()
    expect(screen.getByText('No sessions in this filter window.')).toBeTruthy()
  })

  test('shows observability errors without clearing filters', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => {
        throw new ApiClientError('observability unavailable', {
          detail: 'observability unavailable',
          status: 503,
        })
      }),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    await user.type(
      screen.getByLabelText('Created from'),
      '2026-06-21T00:00:00Z',
    )
    await user.selectOptions(screen.getByLabelText('Status'), 'failed')
    await user.click(screen.getByRole('button', { name: 'Refresh summary' }))

    expect((await screen.findByRole('alert')).textContent).toContain(
      'observability unavailable',
    )
    expect(
      (screen.getByLabelText('Created from') as HTMLInputElement).value,
    ).toBe('2026-06-21T00:00:00Z')
    expect((screen.getByLabelText('Status') as HTMLSelectElement).value).toBe(
      'failed',
    )
  })

  test('manages runtime settings without rendering provider secrets', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      createProviderConnection: vi.fn(async () => providerConnectionsResponse.items[0]),
      getProjectRuntimeSettings: vi.fn(async () => projectRuntimeSettings),
      listChatModels: vi.fn(async () => chatModelsResponse),
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
      listRuntimeSlotDefaults: vi.fn(async () => runtimeSlotDefaultsResponse),
      upsertProviderSecret: vi.fn(async () => ({
        configured: true,
        connection_id: 'qwen-hosted',
        fingerprint: 'new-fingerprint',
        last_four: 'cret',
        secret_name: 'api_key',
        updated_at: '2026-06-24T00:00:02Z',
      })),
      upsertRuntimeSlotDefault: vi.fn(async () => runtimeSlotDefaultsResponse.items[0]),
      updateChatRetrievalSettings: vi.fn(async (body) => ({
        ...body,
        max_limit: 50,
      })),
      syncProviderModels: vi.fn(async () => ({
        connection_id: 'qwen-hosted',
        items: providerModelsResponse.items.filter(
          (model) => model.connection_id === 'qwen-hosted',
        ),
        synced_count: 2,
      })),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    await user.click(screen.getByRole('button', { name: 'Refresh connections' }))

    expect(client.listProviderConnections).toHaveBeenCalled()
    expect((await screen.findAllByText('qwen-hosted')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('local-chat').length).toBeGreaterThan(0)
    expect(screen.getByText('api_key configured / last four cret')).toBeTruthy()
    expect(screen.queryByText('sk-hosted-secret')).toBeNull()
    expect(screen.queryByLabelText('Connection ID')).toBeNull()

    await user.selectOptions(screen.getByLabelText('Provider'), 'qwen')
    await user.selectOptions(screen.getByLabelText('Connection type'), 'hosted')
    await user.type(
      screen.getByLabelText('Base URL'),
      'https://dashscope.example.test/compatible-mode/v1',
    )
    await user.type(screen.getByLabelText('Capabilities'), 'chat, dense_embedding')
    await user.click(screen.getByRole('button', { name: 'Save connection' }))

    expect(client.createProviderConnection).toHaveBeenCalledWith({
      base_url: 'https://dashscope.example.test/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding'],
      connection_type: 'hosted',
      metadata: null,
      provider: 'qwen',
    })

    await openSettingsSubmodule(user, 'Runtime', 'Model catalog')
    await user.click(screen.getByRole('button', { name: 'Refresh catalog' }))

    expect(client.listProviderModels).toHaveBeenCalled()
    await user.selectOptions(screen.getByLabelText('Model sync connection'), 'qwen-hosted')
    await user.click(screen.getByRole('button', { name: 'Sync models' }))

    expect(client.syncProviderModels).toHaveBeenCalledWith('qwen-hosted')

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    await user.click(screen.getByRole('button', { name: 'Refresh connections' }))

    await user.selectOptions(screen.getByLabelText('Secret connection'), 'qwen-hosted')
    await user.type(screen.getByLabelText('API key'), 'sk-hosted-secret')
    await user.click(screen.getByRole('button', { name: 'Save secret' }))

    expect(client.upsertProviderSecret).toHaveBeenCalledWith(
      'qwen-hosted',
      'api_key',
      { value: 'sk-hosted-secret' },
    )
    expect((screen.getByLabelText('API key') as HTMLInputElement).value).toBe('')
    expect(screen.queryByText('sk-hosted-secret')).toBeNull()

    await openSettingsSubmodule(user, 'Runtime', 'Global defaults')
    await user.click(screen.getByRole('button', { name: 'Reload global defaults' }))

    await user.selectOptions(screen.getByLabelText('Global slot'), 'dense_embedding')
    await user.selectOptions(screen.getByLabelText('Global slot connection'), 'qwen-hosted')
    await user.selectOptions(screen.getByLabelText('Global slot model'), 'text-embedding-v4')
    await user.click(screen.getByRole('button', { name: 'Save global slot' }))

    expect(client.upsertRuntimeSlotDefault).toHaveBeenCalledWith(
      'dense_embedding',
      {
        connection_id: 'qwen-hosted',
        model_id: 'text-embedding-v4',
      },
    )

    const globalRetrieval = screen.getByRole('region', {
      name: 'Global chat retrieval',
    })
    fireEvent.change(within(globalRetrieval).getByLabelText('Retrieval limit'), {
      target: { value: '7' },
    })
    fireEvent.change(within(globalRetrieval).getByLabelText('Candidate limit'), {
      target: { value: '12' },
    })
    await user.click(screen.getByRole('button', { name: 'Save chat retrieval' }))

    expect(client.updateChatRetrievalSettings).toHaveBeenCalledWith({
      retrieval_limit: 7,
      rerank_enabled: true,
      rerank_candidate_limit: 12,
    })
  })

  test('shows project runtime inheritance and resets overrides', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      deleteProjectChatRetrievalSettings: vi.fn(async () => ({ deleted: true })),
      deleteProjectRuntimeSlotOverride: vi.fn(async () => ({ deleted: true })),
      getProjectRuntimeSettings: vi.fn(async () => projectRuntimeSettings),
      listChatModels: vi.fn(async () => chatModelsResponse),
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
      listRuntimeSlotDefaults: vi.fn(async () => runtimeSlotDefaultsResponse),
      upsertProjectRuntimeSlotOverride: vi.fn(async () => ({
        connection_id: 'local-chat',
        model_id: 'llama3.1:8b',
        parameters: null,
        slot: 'chat',
        source: 'overridden',
      })),
      upsertProjectChatRetrievalSettings: vi.fn(async (body) => ({
        ...body,
        max_limit: 50,
        source: 'project',
      })),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Project overrides')
    await user.click(screen.getByRole('button', { name: 'Reload project settings' }))

    const projectSettings = await screen.findByRole('region', {
      name: 'Project runtime settings',
    })
    expect(within(projectSettings).getAllByText('dense_embedding').length).toBeGreaterThan(0)
    expect(within(projectSettings).getAllByText('inherited').length).toBeGreaterThan(0)
    expect(within(projectSettings).getAllByText('overridden').length).toBeGreaterThan(0)

    await user.selectOptions(screen.getByLabelText('Project slot'), 'chat')
    await user.selectOptions(screen.getByLabelText('Project slot connection'), 'local-chat')
    await user.selectOptions(screen.getByLabelText('Project slot model'), 'llama3.1:8b')
    await user.click(screen.getByRole('button', { name: 'Save project override' }))

    expect(client.upsertProjectRuntimeSlotOverride).toHaveBeenCalledWith(
      projectId,
      'chat',
      {
        connection_id: 'local-chat',
        model_id: 'llama3.1:8b',
      },
    )

    fireEvent.change(within(projectSettings).getByLabelText('Retrieval limit'), {
      target: { value: '4' },
    })
    await user.selectOptions(within(projectSettings).getByLabelText('Rerank'), 'false')
    fireEvent.change(within(projectSettings).getByLabelText('Candidate limit'), {
      target: { value: '8' },
    })
    await user.click(
      screen.getByRole('button', { name: 'Save project retrieval override' }),
    )

    expect(client.upsertProjectChatRetrievalSettings).toHaveBeenCalledWith(
      projectId,
      {
        retrieval_limit: 4,
        rerank_enabled: false,
        rerank_candidate_limit: 8,
      },
    )

    await user.click(screen.getByRole('button', { name: 'Reset chat to global' }))

    expect(client.deleteProjectRuntimeSlotOverride).toHaveBeenCalledWith(
      projectId,
      'chat',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reset chat retrieval to global' }),
    )

    expect(client.deleteProjectChatRetrievalSettings).toHaveBeenCalledWith(projectId)
  })

  test('blocks global slot save until the selected connection has compatible synced models', async () => {
    const user = userEvent.setup()
    const upsertRuntimeSlotDefault = vi.fn(
      async () => runtimeSlotDefaultsResponse.items[0],
    )
    const client = createClientStub({
      getProjectRuntimeSettings: vi.fn(async () => projectRuntimeSettings),
      listChatModels: vi.fn(async () => chatModelsResponse),
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => ({
        items: providerModelsResponse.items.filter(
          (model) =>
            !(
              model.connection_id === 'qwen-hosted' &&
              model.capabilities.includes('dense_embedding')
            ),
        ),
      })),
      listRuntimeSlotDefaults: vi.fn(async () => runtimeSlotDefaultsResponse),
      upsertRuntimeSlotDefault,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Global defaults')
    await user.click(screen.getByRole('button', { name: 'Reload global defaults' }))

    await screen.findByText('qwen-hosted')
    await user.selectOptions(screen.getByLabelText('Global slot'), 'dense_embedding')
    await user.selectOptions(screen.getByLabelText('Global slot connection'), 'qwen-hosted')

    expect(
      screen.getByText(
        'Sync models for qwen-hosted before saving dense_embedding.',
      ),
    ).toBeTruthy()
    const saveButton = screen.getByRole('button', {
      name: 'Save global slot',
    }) as HTMLButtonElement
    expect(saveButton.disabled).toBe(true)

    await user.click(saveButton)

    expect(upsertRuntimeSlotDefault).not.toHaveBeenCalled()
  })
})
