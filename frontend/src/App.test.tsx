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

import { installPointerEventMocks } from './test/pointerEvents'
import { chooseRadixSelectOption } from './test/radixSelect'
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

type NodeFsModule = {
  readFileSync(path: string, encoding: 'utf8'): string
}

type NodeProcess = {
  getBuiltinModule?(name: 'fs'): NodeFsModule
}

const appStyles =
  (
    globalThis as typeof globalThis & {
      process?: NodeProcess
    }
  ).process?.getBuiltinModule?.('fs').readFileSync('src/App.css', 'utf8') ??
  ''
const appSource =
  (
    globalThis as typeof globalThis & {
      process?: NodeProcess
    }
  ).process?.getBuiltinModule?.('fs').readFileSync('src/App.tsx', 'utf8') ??
  ''
const shellSource =
  (
    globalThis as typeof globalThis & {
      process?: NodeProcess
    }
  ).process
    ?.getBuiltinModule?.('fs')
    .readFileSync('src/features/shell/AppShell.tsx', 'utf8') ?? ''

installPointerEventMocks()

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
  window.history.replaceState(null, '', '/')
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
  checkProviderConnection?: ApiClient['checkProviderConnection']
  createProject?: ApiClient['createProject']
  createProviderConnection?: ApiClient['createProviderConnection']
  createSource?: ApiClient['createSource']
  createUser?: ApiClient['createUser']
  deactivateUser?: ApiClient['deactivateUser']
  deleteProject?: ApiClient['deleteProject']
  deleteProjectMembership?: ApiClient['deleteProjectMembership']
  deleteSource?: ApiClient['deleteSource']
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
  listUserMemories?: ApiClient['listUserMemories']
  proposeUserMemory?: ApiClient['proposeUserMemory']
  updateUserMemory?: ApiClient['updateUserMemory']
  approveUserMemory?: ApiClient['approveUserMemory']
  rejectUserMemory?: ApiClient['rejectUserMemory']
  unarchiveChatSession?: ApiClient['unarchiveChatSession']
  updateChatSessionTitle?: ApiClient['updateChatSessionTitle']
  updateChatRetrievalSettings?: ApiClient['updateChatRetrievalSettings']
  updateCurrentUserPreferences?: ApiClient['updateCurrentUserPreferences']
  updateProject?: ApiClient['updateProject']
  updateSource?: ApiClient['updateSource']
  refineKnowledgeProposal?: ApiClient['refineKnowledgeProposal']
  approveKnowledgeProposal?: ApiClient['approveKnowledgeProposal']
  rejectKnowledgeProposal?: ApiClient['rejectKnowledgeProposal']
  retryIngestionJob?: ApiClient['retryIngestionJob']
  revokeAccessToken?: ApiClient['revokeAccessToken']
  runNextIngestionJob?: ApiClient['runNextIngestionJob']
  searchRetrieval?: ApiClient['searchRetrieval']
  submitKnowledgeProposal?: ApiClient['submitKnowledgeProposal']
  upsertChatModel?: ApiClient['upsertChatModel']
  upsertProjectChatRetrievalSettings?: ApiClient['upsertProjectChatRetrievalSettings']
  upsertProjectMembership?: ApiClient['upsertProjectMembership']
  upsertProjectChatModel?: ApiClient['upsertProjectChatModel']
  upsertProjectRuntimeSlotOverride?: ApiClient['upsertProjectRuntimeSlotOverride']
  upsertProviderConnection?: ApiClient['upsertProviderConnection']
  upsertProviderSecret?: ApiClient['upsertProviderSecret']
  upsertRuntimeSlotDefault?: ApiClient['upsertRuntimeSlotDefault']
  deleteProviderConnection?: ApiClient['deleteProviderConnection']
  deleteProjectChatRetrievalSettings?: ApiClient['deleteProjectChatRetrievalSettings']
  deleteProjectRuntimeSlotOverride?: ApiClient['deleteProjectRuntimeSlotOverride']
  syncProviderModels?: ApiClient['syncProviderModels']
}): ApiClient {
  return {
    askChat: options.askChat ?? vi.fn(),
    askChatStream: options.askChatStream ?? vi.fn(),
    searchRetrieval: options.searchRetrieval ?? vi.fn(),
    archiveChatSession: options.archiveChatSession ?? vi.fn(),
    checkProviderConnection: options.checkProviderConnection ?? vi.fn(),
    createProject: options.createProject ?? vi.fn(),
    createProviderConnection: options.createProviderConnection ?? vi.fn(),
    createSource: options.createSource ?? vi.fn(),
    createUser: options.createUser ?? vi.fn(),
    deactivateUser: options.deactivateUser ?? vi.fn(),
    deleteProject: options.deleteProject ?? vi.fn(),
    deleteProjectMembership: options.deleteProjectMembership ?? vi.fn(),
    deleteSource: options.deleteSource ?? vi.fn(),
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
    listProviderConnections:
      options.listProviderConnections ?? vi.fn(async () => ({ items: [] })),
    listProviderModels: options.listProviderModels ?? vi.fn(),
    listProjects:
      options.listProjects ?? vi.fn(async () => ({ items: [] })),
    listRuntimeSlotDefaults: options.listRuntimeSlotDefaults ?? vi.fn(),
    listSources: options.listSources ?? vi.fn(),
    listUsers: options.listUsers ?? vi.fn(),
    listUserMemories:
      options.listUserMemories ?? vi.fn(async () => ({ items: [] })),
    proposeUserMemory: options.proposeUserMemory ?? vi.fn(),
    updateUserMemory: options.updateUserMemory ?? vi.fn(),
    approveUserMemory: options.approveUserMemory ?? vi.fn(),
    rejectUserMemory: options.rejectUserMemory ?? vi.fn(),
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
    updateProject: options.updateProject ?? vi.fn(),
    updateSource: options.updateSource ?? vi.fn(),
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
    deleteProviderConnection: options.deleteProviderConnection ?? vi.fn(),
    deleteProviderSecret: vi.fn(),
    deleteRuntimeSlotDefault: vi.fn(),
    revokeAccessToken: options.revokeAccessToken ?? vi.fn(),
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

const chatResponseWithSteps: ChatResponseBody = {
  ...chatResponse,
  steps: [
    {
      detail: { result_count: 1, strategy: 'dense' },
      elapsed_ms: 410,
      id: 'retrieval',
      status: 'done',
    },
    {
      detail: { tool_calls: 1 },
      elapsed_ms: 2500,
      id: 'answer',
      status: 'done',
      usage: {
        estimated_cost_usd: 0.0042,
        input_tokens: 120,
        model: 'qwen-plus',
        output_tokens: 48,
        provider: 'qwen',
        slot: 'chat',
        total_tokens: 168,
      },
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
    name: 'Settings Navigation',
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
      name: 'Primary Sidebar',
    })
    const navigation = within(sidebar).getByRole('navigation', {
      name: 'Primary Navigation',
    })

    expect(
      within(navigation)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Chat', 'My account', 'Settings'])
    expect(within(sidebar).getByRole('heading', { name: 'Sesiones' })).toBeTruthy()

    await user.click(within(navigation).getByRole('button', { name: 'My account' }))

    expect(
      within(sidebar).getByRole('navigation', { name: 'My Account Navigation' }),
    ).toBeTruthy()
    expect(within(sidebar).queryByRole('heading', { name: 'Sesiones' })).toBeNull()

    await user.click(within(navigation).getByRole('button', { name: 'Settings' }))

    expect(
      within(sidebar).getByRole('navigation', { name: 'Settings Navigation' }),
    ).toBeTruthy()
    expect(within(sidebar).queryByRole('heading', { name: 'Sesiones' })).toBeNull()
  })

  test('marks the current primary sidebar page with aria-current', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const chatButton = await screen.findByRole('button', { name: /^Chat$/ })
    const accountButton = screen.getByRole('button', { name: 'My account' })

    expect(chatButton.getAttribute('aria-current')).toBe('page')
    expect(accountButton.hasAttribute('aria-current')).toBe(false)

    await user.click(accountButton)

    expect(accountButton.getAttribute('aria-current')).toBe('page')
    expect(chatButton.hasAttribute('aria-current')).toBe(false)
  })

  test('shows account modules and a real Memory panel with propose/approve', async () => {
    const user = userEvent.setup()
    const memories: Array<{
      id: string
      user_id: string
      project_id: string | null
      content: string
      status: 'proposed' | 'approved' | 'rejected'
      created_at: string | null
      reviewed_at: string | null
      reviewed_by_user_id: string | null
    }> = []

    const listUserMemories = vi.fn(async () => ({ items: [...memories] }))
    const proposeUserMemory = vi.fn(async (body: { content: string }) => {
      const item = {
        content: body.content,
        created_at: '2026-08-05T00:00:00Z',
        id: `mem-${memories.length + 1}`,
        project_id: null,
        reviewed_at: null,
        reviewed_by_user_id: null,
        status: 'proposed' as const,
        user_id: 'user-1',
      }
      memories.push(item)
      return item
    })
    const approveUserMemory = vi.fn(async (memoryId: string) => {
      const item = memories.find((memory) => memory.id === memoryId)
      if (item === undefined) {
        throw new Error('missing')
      }
      item.status = 'approved'
      return item
    })

    render(
      <App
        apiClient={createClientStub({
          approveUserMemory,
          listUserMemories,
          proposeUserMemory,
        })}
        initialProjectId={projectId}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'My account' }))

    const accountNavigation = screen.getByRole('navigation', {
      name: 'My Account Navigation',
    })

    expect(
      within(accountNavigation)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Appearance', 'Memory'])
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeTruthy()
    const memoryButton = within(accountNavigation).getByRole('button', {
      name: 'Memory',
    })
    await user.click(memoryButton)
    expect(screen.getByRole('heading', { name: 'Memory' })).toBeTruthy()
    expect(screen.queryByText('Deferred')).toBeNull()
    expect(
      screen.getByText(/Only approved items inject as system context/i),
    ).toBeTruthy()

    await user.type(
      screen.getByLabelText('Propose memory'),
      'Prefer concise answers',
    )
    await user.click(screen.getByRole('button', { name: 'Propose' }))

    expect(proposeUserMemory).toHaveBeenCalled()
    expect(await screen.findByText('Prefer concise answers')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    expect(approveUserMemory).toHaveBeenCalled()
    // Status badge text "Approved" collides with the filter button of the same name.
    const memoryList = await screen.findByRole('list', { name: 'User memories' })
    expect(
      await within(memoryList).findByText('Approved'),
    ).toBeTruthy()
  
  })

  test('shows settings modules and submodules in the sidebar', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Settings' }))

    const settingsNavigation = screen.getByRole('navigation', {
      name: 'Settings Navigation',
    })

    expect(within(settingsNavigation).getByRole('button', { name: 'Authoring' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Projects' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Users' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Knowledge' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Sources' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Observability' })).toBeTruthy()
    expect(within(settingsNavigation).getByRole('button', { name: 'Runtime' })).toBeTruthy()
    expect(screen.queryByRole('tablist', { name: 'Settings sections' })).toBeNull()
    const settingsShell = document.querySelector(
      '[data-slot="settings-shell"]',
    ) as HTMLElement
    expect(within(settingsShell).getByRole('heading', { name: 'Settings' })).toBeTruthy()
    expect(
      document.querySelector('[data-slot="settings-shell-header"] .panel-label'),
    ).toBeNull()
  })

  test('routes settings sidebar submodules to focused content', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Authoring', 'Users')
    expect(screen.getByRole('heading', { name: 'Users' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Content Registry' })).toBeNull()

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    expect(screen.getByRole('heading', { name: 'Content Registry' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Observability', 'Summary')
    expect(screen.getByRole('heading', { name: 'Summary' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh Summary' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Observability', 'Costs')
    expect(screen.getByRole('heading', { name: 'Costs' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh Summary' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Observability', 'Errors')
    expect(screen.getByRole('heading', { name: 'Errors' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh Summary' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Observability', 'Latency')
    expect(screen.getByRole('heading', { name: 'Latency' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh Summary' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    expect(screen.getByRole('heading', { level: 2, name: 'Connections' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Refresh connections' })).toBeNull()

    await openSettingsSubmodule(user, 'Runtime', 'Model Catalog')
    expect(screen.getByRole('heading', { level: 2, name: 'Model Catalog' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh Catalog' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Runtime', 'Global Defaults')
    expect(screen.getByRole('heading', { level: 2, name: 'Global Defaults' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reload Global Defaults' })).toBeTruthy()

    await openSettingsSubmodule(user, 'Runtime', 'Project Overrides')
    expect(screen.getByRole('heading', { level: 2, name: 'Project Overrides' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reload project settings' })).toBeTruthy()
  })

  test('uses only sidebar navigation for runtime submodules', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Connections')

    expect(
      screen.queryByRole('group', {
        name: 'Runtime submodule navigation',
      }),
    ).toBeNull()

    const settingsNavigation = screen.getByRole('navigation', {
      name: 'Settings Navigation',
    })
    expect(
      within(settingsNavigation)
        .getByRole('button', { name: 'Connections' })
        .getAttribute('aria-pressed'),
    ).toBe('true')

    await user.click(
      within(settingsNavigation).getByRole('button', {
        name: 'Model Catalog',
      }),
    )

    expect(
      within(settingsNavigation)
        .getByRole('button', { name: 'Model Catalog' })
        .getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.getByRole('heading', { level: 2, name: 'Model Catalog' }),
    ).toBeTruthy()
  })

  test('does not render duplicated runtime submodule navigation in content', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Project Overrides')

    const settingsNavigation = screen.getByRole('navigation', {
      name: 'Settings Navigation',
    })
    expect(
      within(settingsNavigation)
        .getByRole('button', { name: 'Project Overrides' })
        .getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.queryByRole('group', {
      name: 'Runtime submodule navigation',
      }),
    ).toBeNull()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Project Overrides' }),
    ).toBeTruthy()
  })

  test('opens the module matching the current route on initial render', () => {
    window.history.replaceState(null, '', '/settings/runtime')

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    expect(
      screen.getByRole('heading', { level: 2, name: 'Connections' }),
    ).toBeTruthy()
    expect(window.location.pathname).toBe('/settings/runtime')
  })

  test('updates the route when primary modules and settings tabs change', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    expect(window.location.pathname).toBe('/settings/authoring')
    // Default authoring submodule is Projects (panel title), not a bare "Authoring" h2.
    expect(screen.getByRole('heading', { name: 'Projects' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Observability' }))
    expect(window.location.pathname).toBe('/settings/observability')
    expect(screen.getByRole('heading', { name: 'Summary' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Runtime' }))
    expect(window.location.pathname).toBe('/settings/runtime')
    expect(
      screen.getByRole('heading', { level: 2, name: 'Connections' }),
    ).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'My account' }))
    expect(window.location.pathname).toBe('/account')
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: /^Chat$/ }))
    expect(window.location.pathname).toBe('/chat')
    expect(screen.getByLabelText('Question')).toBeTruthy()
  })

  test('tracks browser back and forward between modules', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    await user.click(screen.getByRole('button', { name: 'Runtime' }))
    expect(window.location.pathname).toBe('/settings/runtime')

    window.history.back()

    await waitFor(() =>
      expect(window.location.pathname).toBe('/settings/authoring'),
    )
    expect(screen.getByRole('heading', { name: 'Projects' })).toBeTruthy()

    window.history.forward()

    await waitFor(() =>
      expect(window.location.pathname).toBe('/settings/runtime'),
    )
    expect(
      screen.getByRole('heading', { level: 2, name: 'Connections' }),
    ).toBeTruthy()
  })

  test('opens and closes the left sidebar with the burger control', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const toggle = screen.getByRole('button', { name: 'Collapse Left Sidebar' })
    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })

    expect(sidebar.getAttribute('data-slot')).toBe('app-sidebar')
    expect(sidebar.getAttribute('data-state')).toBe('open')
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(toggle.className).toMatch(/hover:bg-primary\/15/)
    expect(toggle.className).not.toMatch(/hover:bg-accent/)
    // Desktop viewport: no mobile scrim.
    expect(screen.queryByTestId('sidebar-backdrop')).toBeNull()

    await user.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.getAttribute('aria-label')).toBe('Open Left Sidebar')
    expect(sidebar.getAttribute('data-state')).toBe('closed')
    expect(screen.queryByTestId('sidebar-backdrop')).toBeNull()
    const closedContent = sidebar.querySelector(
      '[data-slot="app-sidebar-content"]',
    )
    expect(closedContent?.hasAttribute('inert')).toBe(true)
  })

  test('closes the left sidebar with the mobile scrim and Escape', async () => {
    const user = userEvent.setup()

    setViewportWidth(500)
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })

    if (sidebar.getAttribute('data-state') !== 'open') {
      await user.click(screen.getByRole('button', { name: 'Open Left Sidebar' }))
    }

    expect(sidebar.getAttribute('data-state')).toBe('open')

    const backdrop = screen.getByTestId('sidebar-backdrop')
    expect(backdrop.getAttribute('data-slot')).toBe('sidebar-backdrop')
    expect(backdrop.className).toContain('bg-[var(--overlay-backdrop)]')
    expect(backdrop.className).toContain('z-30')
    expect(backdrop.className).toContain('fixed')
    expect(backdrop.className).toContain('inset-0')

    await user.click(backdrop)

    expect(sidebar.getAttribute('data-state')).toBe('closed')
    expect(screen.queryByTestId('sidebar-backdrop')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Open Left Sidebar' }))
    expect(sidebar.getAttribute('data-state')).toBe('open')
    expect(screen.getByTestId('sidebar-backdrop')).toBeTruthy()
    expect(
      document.getElementById('main-content')?.hasAttribute('inert'),
    ).toBe(true)

    await user.keyboard('{Escape}')

    expect(sidebar.getAttribute('data-state')).toBe('closed')
    expect(screen.queryByTestId('sidebar-backdrop')).toBeNull()
    expect(
      document.getElementById('main-content')?.hasAttribute('inert'),
    ).toBe(false)
  })

  test('closes the left sidebar with Escape on desktop without a scrim', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })
    expect(sidebar.getAttribute('data-state')).toBe('open')
    expect(screen.queryByTestId('sidebar-backdrop')).toBeNull()

    await user.keyboard('{Escape}')

    expect(sidebar.getAttribute('data-state')).toBe('closed')
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
      name: 'Primary Sidebar',
    })
    const selector = await within(sidebar).findByRole('button', {
      name: /Project selector/i,
    })
    const navigation = within(sidebar).getByRole('navigation', {
      name: 'Primary Navigation',
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

  test('uses tokenized sidebar shell slots instead of legacy selectors', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })
    const primaryNavigation = within(sidebar).getByRole('navigation', {
      name: 'Primary Navigation',
    })
    const selector = await within(sidebar).findByRole('button', {
      name: /Project selector/i,
    })

    expect(sidebar.getAttribute('data-slot')).toBe('app-sidebar')
    expect(primaryNavigation.getAttribute('data-slot')).toBe(
      'sidebar-primary-navigation',
    )
    expect(selector.getAttribute('data-slot')).toBe('project-selector-trigger')
    expect(selector.closest('[data-slot="project-selector"]')).toBeTruthy()

    await user.click(selector)
    expect(selector.className).toMatch(/bg-primary\/15/)
    expect(selector.className).not.toMatch(/bg-accent/)
    await user.keyboard('{Escape}')

    await user.click(screen.getByRole('button', { name: 'Settings' }))

    const settingsNavigation = screen.getByRole('navigation', {
      name: 'Settings Navigation',
    })
    expect(settingsNavigation.getAttribute('data-slot')).toBe(
      'sidebar-contextual-navigation',
    )
    expect(
      within(settingsNavigation)
        .getByRole('button', { name: 'Authoring' })
        .getAttribute('data-slot'),
    ).toBe('sidebar-contextual-item')

    expect(appStyles).not.toMatch(/\.sidebar-navigation\b/)
    expect(appStyles).not.toMatch(/\.sidebar-nav-button\b/)
    expect(appStyles).not.toMatch(/\.contextual-navigation\b/)
    expect(appStyles).not.toMatch(/\.contextual-nav-/)
    expect(appStyles).not.toMatch(/\.project-selector-/)
    expect(appStyles).not.toMatch(/\.sidebar-project-selector\b/)
  })

  test('renders the project selector popover through Radix state and portal primitives', async () => {
    const user = userEvent.setup()

    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })
    const selector = await within(sidebar).findByRole('button', {
      name: /Project selector/i,
    })

    expect(selector.getAttribute('data-state')).toBe('closed')

    await user.click(selector)

    expect(selector.getAttribute('data-state')).toBe('open')

    const popover = screen
      .getByRole('listbox', { name: 'Projects' })
      .closest('[data-slot="project-selector-popover"]')

    expect(popover).toBeTruthy()
    expect(popover?.parentElement?.closest('[data-slot="app-sidebar"]')).toBeNull()
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

    await user.type(screen.getByLabelText('Search Projects'), 'omega')
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

  test('uses chat to request knowledge proposals instead of a composer button', async () => {
    const user = userEvent.setup()
    const submitKnowledgeProposal = vi.fn(async () => pendingKnowledgeProposal)
    const askChatStream = vi.fn(async () => chatResponse)

    render(
      <App
        apiClient={createClientStub({ askChatStream, submitKnowledgeProposal })}
        initialProjectId={projectId}
      />,
    )

    expect(
      screen.queryByRole('button', { name: 'Propose knowledge' }),
    ).toBeNull()
    await user.type(
      screen.getByLabelText('Question'),
      'Document this deployment exception.',
    )
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() =>
      expect(askChatStream).toHaveBeenCalledWith(
        projectId,
        {
          message: 'Document this deployment exception.',
        },
        expect.any(Object),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      ),
    )
    expect(submitKnowledgeProposal).not.toHaveBeenCalled()
  })

  test('renders a chat knowledge draft card and approves edited text', async () => {
    const user = userEvent.setup()
    const responseWithKnowledgeTool = {
      ...chatResponse,
      tool_calls: [
        {
          arguments: {
            knowledge_text: 'Document this deployment exception.',
            scope: 'session',
          },
          name: 'commit_knowledge',
          result_summary: {
            draft_id: 'draft-33333333',
            proposed_text: 'Document this deployment exception.',
            review_action: 'approve',
            scope: 'session',
            status: 'draft',
          },
        },
      ],
    }
    const approveResult = {
      ...pendingKnowledgeProposal,
      approved_source_id: 'source-approved',
      proposed_text: 'Document this deployment exception for import retries.',
      status: 'approved',
    }
    const submitKnowledgeProposal = vi.fn(async () => approveResult)
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => responseWithKnowledgeTool),
      listChatSessions: vi.fn(async () => sessionListResponse),
      submitKnowledgeProposal,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Capture this as knowledge.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(
      await screen.findByRole('region', {
        name: 'Knowledge draft draft-33333333',
      }),
    ).toBeTruthy()
    const draftText = screen.getByLabelText('Knowledge Draft Text')
    await user.clear(draftText)
    await user.type(
      draftText,
      'Document this deployment exception for import retries.',
    )
    await user.click(screen.getByRole('button', { name: 'Approve Knowledge' }))

    await waitFor(() =>
      expect(submitKnowledgeProposal).toHaveBeenCalledWith(projectId, {
        origin_session_id: 'session-123',
        proposed_text: 'Document this deployment exception for import retries.',
      }),
    )
    expect(await screen.findByText('Approved')).toBeTruthy()
    expect(
      screen.queryByText(/limit .* results/),
    ).toBeNull()
  })

  test('lets viewers request approval, refine via chat reference, or cancel draft cards', async () => {
    const user = userEvent.setup()
    const responseWithKnowledgeTool = {
      ...chatResponse,
      tool_calls: [
        {
          arguments: {
            knowledge_text: 'Viewer draft knowledge.',
            scope: 'message',
          },
          name: 'commit_knowledge',
          result_summary: {
            draft_id: 'draft-viewer',
            proposed_text: 'Viewer draft knowledge.',
            review_action: 'request_approval',
            scope: 'message',
            status: 'draft',
          },
        },
      ],
    }
    const submitKnowledgeProposal = vi.fn(async () => ({
      ...pendingKnowledgeProposal,
      proposed_text: 'Viewer draft knowledge.',
      status: 'pending',
    }))
    const client = createClientStub({
      askChatStream: vi.fn(async () => responseWithKnowledgeTool),
      submitKnowledgeProposal,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Remember this project rule.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByDisplayValue('Viewer draft knowledge.')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Refine In Chat' }))
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(
      [
        '[refining knowledge draft draft-viewer]',
        'Current draft:',
        'Viewer draft knowledge.',
        'Requested change: ',
      ].join('\n'),
    )

    await user.click(screen.getByRole('button', { name: 'Request Approval' }))
    await waitFor(() =>
      expect(submitKnowledgeProposal).toHaveBeenCalledWith(projectId, {
        origin_session_id: 'session-123',
        proposed_text: 'Viewer draft knowledge.',
      }),
    )
    expect(await screen.findByText('Pending')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Cancel Draft' }))
    expect(screen.getByText('Canceled')).toBeTruthy()
  })

  test('applies chat knowledge lifecycle tool calls to an existing draft card', async () => {
    const user = userEvent.setup()
    const responses = [
      {
        ...chatResponse,
        tool_calls: [
          {
            arguments: {
              knowledge_text: 'Original draft knowledge.',
              scope: 'message',
            },
            name: 'commit_knowledge',
            result_summary: {
              draft_id: 'draft-lifecycle',
              proposed_text: 'Original draft knowledge.',
              review_action: 'approve',
              scope: 'message',
              status: 'draft',
            },
          },
        ],
      },
      {
        ...chatResponse,
        answer: 'Updated the draft.',
        tool_calls: [
          {
            arguments: {
              draft_id: 'draft-lifecycle',
              knowledge_text: 'Refined draft knowledge.',
              scope: 'message',
            },
            name: 'refine_knowledge',
            result_summary: {
              draft_id: 'draft-lifecycle',
              knowledge_lifecycle: {
                action: 'refine',
                draft_id: 'draft-lifecycle',
              },
              proposed_text: 'Refined draft knowledge.',
              review_action: 'approve',
              scope: 'message',
              status: 'draft',
            },
          },
        ],
      },
      {
        ...chatResponse,
        answer: 'Cancelled the draft.',
        tool_calls: [
          {
            arguments: {
              draft_id: 'draft-lifecycle',
            },
            name: 'cancel_knowledge',
            result_summary: {
              draft_id: 'draft-lifecycle',
              knowledge_lifecycle: {
                action: 'cancel',
                draft_id: 'draft-lifecycle',
              },
              status: 'cancelled',
            },
          },
        ],
      },
    ]
    const askChatStream = vi.fn(async () => responses.shift() ?? chatResponse)

    render(
      <App
        apiClient={createClientStub({ askChatStream })}
        initialProjectId={projectId}
      />,
    )

    await user.type(screen.getByLabelText('Question'), 'Remember this.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByDisplayValue('Original draft knowledge.')).toBeTruthy()

    await user.type(screen.getByLabelText('Question'), 'Make that draft clearer.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByDisplayValue('Refined draft knowledge.')).toBeTruthy()

    await user.type(screen.getByLabelText('Question'), 'Cancel that draft.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect((await screen.findAllByText('Canceled')).length).toBeGreaterThan(0)
  })

  test('approves an existing draft when chat calls approve_knowledge', async () => {
    const user = userEvent.setup()
    const responses = [
      {
        ...chatResponse,
        tool_calls: [
          {
            arguments: {
              knowledge_text: 'Approval draft knowledge.',
              scope: 'session',
            },
            name: 'commit_knowledge',
            result_summary: {
              draft_id: 'draft-approve-chat',
              proposed_text: 'Approval draft knowledge.',
              review_action: 'approve',
              scope: 'session',
              status: 'draft',
            },
          },
        ],
      },
      {
        ...chatResponse,
        answer: 'Approving the draft.',
        tool_calls: [
          {
            arguments: {
              draft_id: 'draft-approve-chat',
            },
            name: 'approve_knowledge',
            result_summary: {
              draft_id: 'draft-approve-chat',
              knowledge_lifecycle: {
                action: 'approve',
                draft_id: 'draft-approve-chat',
              },
              status: 'approval_requested',
            },
          },
        ],
      },
    ]
    const approveResult = {
      ...pendingKnowledgeProposal,
      approved_source_id: 'source-approved',
      proposed_text: 'Approval draft knowledge.',
      status: 'approved',
    }
    const askChatStream = vi.fn(async () => responses.shift() ?? chatResponse)
    const submitKnowledgeProposal = vi.fn(async () => approveResult)

    render(
      <App
        apiClient={createClientStub({ askChatStream, submitKnowledgeProposal })}
        initialProjectId={projectId}
      />,
    )

    await user.type(screen.getByLabelText('Question'), 'Capture this.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByDisplayValue('Approval draft knowledge.')).toBeTruthy()

    await user.type(screen.getByLabelText('Question'), 'Approve draft-approve-chat.')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() =>
      expect(submitKnowledgeProposal).toHaveBeenCalledWith(projectId, {
        origin_session_id: 'session-123',
        proposed_text: 'Approval draft knowledge.',
      }),
    )
    expect(await screen.findByText('Approved')).toBeTruthy()
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
    await user.type(screen.getByLabelText('User Login'), viewerUser.login)
    await user.type(screen.getByLabelText('Display Name'), viewerUser.display_name)
    await user.type(screen.getByLabelText('Access Token'), 'viewer-token')
    await user.click(screen.getByRole('button', { name: 'Create User' }))

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith({
        access_token: 'viewer-token',
        display_name: viewerUser.display_name,
        login: viewerUser.login,
        system_role: 'user',
      }),
    )

    await user.type(screen.getByLabelText('Member user ID'), viewerUser.id)
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Project Role'),
      'Admin',
    )
    await user.click(screen.getByRole('button', { name: 'Save Membership' }))

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
    await user.click(screen.getByRole('button', { name: 'Refresh Proposals' }))

    expect(
      await screen.findByText('Document the escalation runbook from chat.'),
    ).toBeTruthy()

    await user.type(screen.getByLabelText('Refined Text'), 'Refined escalation runbook.')
    await user.click(screen.getByRole('button', { name: /^Refine / }))

    await waitFor(() =>
      expect(refineKnowledgeProposal).toHaveBeenCalledWith(
        projectId,
        pendingKnowledgeProposal.id,
        { refined_text: 'Refined escalation runbook.' },
      ),
    )

    await user.click(screen.getByRole('button', { name: /^Approve / }))

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

    await user.type(screen.getByLabelText('Reject Reason'), 'Needs source owner.')
    await user.click(screen.getByRole('button', { name: /^Reject / }))

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

    expect(screen.queryByLabelText('Workspace Inspector')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    expect(screen.getByLabelText('Workspace Inspector')).toBeTruthy()
    expect(
      screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected'),
    ).toBe('true')

    await user.click(screen.getByRole('button', { name: 'Open Minimap Sidebar' }))

    expect(
      screen.getByRole('tab', { name: 'Minimap' }).getAttribute('aria-selected'),
    ).toBe('true')
    expect(
      screen
        .getByRole('button', { name: 'Open Minimap Sidebar' })
        .getAttribute('aria-pressed'),
    ).toBe('true')

    await user.click(screen.getByRole('button', { name: 'Close Right Sidebar' }))

    expect(screen.queryByLabelText('Workspace Inspector')).toBeNull()
  })

  test('renders the right dock inline on xl viewports and as an overlay below xl', async () => {
    const user = userEvent.setup()

    setViewportWidth(1400)
    const { unmount } = render(
      <App apiClient={createClientStub({})} initialProjectId={projectId} />,
    )

    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const inlineInspector = screen.getByRole('complementary', {
      name: 'Workspace Inspector',
    })
    expect(inlineInspector.className).toContain('workspace-inspector-inline')
    expect(screen.queryByTestId('inspector-backdrop')).toBeNull()
    expect(document.querySelector('.chat-workspace-grid')?.className).toContain(
      'chat-workspace-grid-docked',
    )

    unmount()
    setViewportWidth(900)
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    // Overlay uses dialog role for modal keyboard semantics.
    const overlayInspector = screen.getByRole('dialog', {
      name: 'Workspace Inspector',
    })
    expect(overlayInspector.className).toContain('workspace-inspector-overlay')
    expect(overlayInspector.className).toMatch(/max-\[680px\]:inset-0/)
    expect(overlayInspector.className).not.toMatch(/max-\[680px\]:inset-3/)
    expect(overlayInspector.getAttribute('aria-modal')).toBe('true')
    expect(screen.getByTestId('inspector-backdrop')).toBeTruthy()
    expect(
      document
        .querySelector('[data-slot="chat-workspace-inert-host"]')
        ?.hasAttribute('inert'),
    ).toBe(true)
    expect(
      document
        .querySelector('[data-slot="app-shell-sidebar-host"]')
        ?.hasAttribute('inert'),
    ).toBe(true)
    expect(
      document
        .querySelector('[data-slot="workspace-topline-host"]')
        ?.hasAttribute('inert'),
    ).toBe(true)
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

    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
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
    expect(purpleThemeButton.className).toContain('focus-visible:ring-primary')
    expect(purpleThemeButton.className).toContain('bg-primary/25')
    expect(
      darkThemeButton.querySelector<HTMLElement>('[data-slot="theme-swatch"]')?.style
        .background,
    ).toBe('rgb(0, 0, 0)')
    expect(
      darkThemeButton
        .querySelector<HTMLElement>('[data-slot="theme-swatch-accent"]')
        ?.style
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

  test('keeps appearance theme options out of App.css legacy selectors', () => {
    expect(appStyles).not.toMatch(/\.theme-option\b/)
    expect(appStyles).not.toMatch(/\.theme-swatch\b/)
    expect(appStyles).not.toMatch(/\.settings-panel\b/)
    expect(appStyles).not.toMatch(/\.panel-label\b/)
  })

  test('uses shared button primitives for remaining App and shell actions', () => {
    expect(appSource).toContain('@/components/ui/button')
    expect(shellSource).toContain('@/components/ui/button')
    expect(appSource).not.toContain('<button')
    expect(shellSource).not.toContain('<button')
  })

  test('keeps shell components extracted from App.tsx', () => {
    expect(appSource).toContain('@/features/shell/AppShell')
    expect(appSource).not.toMatch(/function AppSidebar\b/)
    expect(appSource).not.toMatch(/function SidebarProjectSelector\b/)
    expect(appSource).not.toMatch(/function WorkspaceTopline\b/)
  })

  test('uses the shared Popover wrapper for shell project selection', () => {
    expect(shellSource).toContain('@/components/ui/popover')
    expect(shellSource).not.toContain('@radix-ui/react-popover')
  })

  test('uses lucide icons without global App.css icon selectors', () => {
    expect(shellSource).toContain('lucide-react')
    expect(shellSource).not.toContain('<svg')
    expect(shellSource).not.toContain('ui-icon')
    expect(appStyles).not.toMatch(/\.ui-icon\b/)
    expect(appStyles).not.toMatch(/\.brain-icon\b/)
    expect(appStyles).not.toMatch(/\.context-ring-/)
  })

  test('keeps workspace shell layout out of App.css legacy selectors', () => {
    for (const selector of [
      '.app-shell',
      '.workspace',
      '.workspace-topline',
      '.workspace-project-chip',
      '.workspace-grid',
      '.workspace-chat',
      '.chat-workspace-grid',
      '.workspace-inspector-inline',
      '.workspace-inspector-overlay',
      '.workspace-inspector-backdrop',
    ]) {
      expect(appStyles).not.toContain(selector)
    }

    expect(shellSource).toContain('data-slot="app-shell"')
    expect(shellSource).toContain('data-slot="workspace"')
    expect(shellSource).toContain('data-slot="workspace-topline"')
    expect(shellSource).toContain('data-slot="chat-workspace-grid"')
    expect(shellSource).toContain('data-slot="workspace-project-chip"')
  })

  test('renders a keyboard skip link targeting the chat composer', () => {
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const skip = screen.getByRole('link', { name: 'Skip to chat composer' })
    expect(skip.getAttribute('href')).toBe('#chat-composer')
    expect(skip.getAttribute('data-slot')).toBe('skip-link')
    expect(skip.className).toContain('focus-visible:ring-primary-foreground')
    expect(document.getElementById('chat-composer')).toBeTruthy()
    expect(document.getElementById('main-content')).toBeTruthy()
  })

  test('marks skip-link and shell hosts inert while the inspector overlay is open', async () => {
    const user = userEvent.setup()
    setViewportWidth(900)
    render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

    const skip = screen.getByRole('link', { name: 'Skip to chat composer' })
    expect(skip.hasAttribute('inert')).toBe(false)

    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))
    await screen.findByRole('dialog', { name: 'Workspace Inspector' })

    expect(skip.hasAttribute('inert')).toBe(true)
    expect(
      document
        .querySelector('[data-slot="app-shell-sidebar-host"]')
        ?.hasAttribute('inert'),
    ).toBe(true)
    expect(
      document
        .querySelector('[data-slot="chat-workspace-inert-host"]')
        ?.hasAttribute('inert'),
    ).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Close Right Sidebar' }))
    expect(skip.hasAttribute('inert')).toBe(false)
  })

  test('does not keep legacy inspector backdrop class markers in App.tsx', () => {
    expect(appSource).not.toContain('workspace-inspector-backdrop')
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

    await user.type(screen.getByLabelText('Project Name'), 'Demo')
    await user.click(screen.getByRole('button', { name: 'Create Project' }))

    expect(client.createProject).toHaveBeenCalledWith({ name: 'Demo' })
    expect((await screen.findAllByText(projectId)).length).toBeGreaterThanOrEqual(1)

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Source Type'),
      'Markdown',
    )
    await user.type(screen.getByLabelText('External ID'), 'notes.md')
    await user.type(screen.getByLabelText('Content'), '# Notes')
    await user.type(screen.getByLabelText('Tags'), 'docs, local')
    await user.click(screen.getByRole('button', { name: 'Create Source' }))

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

  test('rejects binary source files over the 5 MiB limit before upload', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      createSource: vi.fn(async () => sourceSummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Authoring', 'Sources')
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Source Type'),
      'PDF',
    )

    const oversize = new File([new Uint8Array(1)], 'huge.pdf', {
      type: 'application/pdf',
    })
    Object.defineProperty(oversize, 'size', { value: 6 * 1024 * 1024 })
    await user.upload(screen.getByLabelText('File'), oversize)

    expect(
      await screen.findByText('pdf source file exceeds the 5 MiB limit.'),
    ).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Create Source' }))
    expect(client.createSource).not.toHaveBeenCalled()
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
    await user.click(screen.getByRole('button', { name: 'Refresh Sources' }))
    expect(await screen.findByText('notes.md')).toBeTruthy()

    await user.click(
      screen.getByRole('button', { name: 'Enqueue ingestion for notes.md' }),
    )

    expect(client.enqueueIngestionJob).toHaveBeenCalledWith(
      projectId,
      sourceSummary.id,
    )
    expect((await screen.findAllByText('Queued')).length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: 'Refresh Jobs' }))

    expect(client.listIngestionJobs).toHaveBeenCalledWith(projectId, {
      job_type: 'ingest_source',
    })
    expect((await screen.findAllByText('Blocked')).length).toBeGreaterThan(0)
    expect(screen.getByText('missing content')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Run Next Job' }))

    expect(client.runNextIngestionJob).toHaveBeenCalledWith(projectId)
    expect((await screen.findAllByText('Processed')).length).toBeGreaterThan(0)

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

    expect(screen.queryByLabelText('Retrieval limit')).toBeNull()
    expect(
      screen.queryByRole('region', { name: 'Chat Retrieval mode' }),
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
    await user.click(screen.getByRole('button', { name: 'Refresh Sources' }))

    expect(await screen.findByText('Markdown · docs, local')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Refresh Jobs' }))

    expect(await screen.findByText('Attempt 1/3')).toBeTruthy()
    expect(screen.getByText('Unlocked')).toBeTruthy()
    expect(
      screen.getByText(`source ${sourceSummary.id}`, { exact: false }),
    ).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Run Next Job' }))

    const lastRun = await screen.findByText('Last run')
    expect(lastRun).toBeTruthy()
    const lastRunCard = document.querySelector('[data-slot="ingestion-last-run"]')
    expect(lastRunCard?.textContent).toMatch(/Idle/i)
    expect(screen.getByText('No Ingestion Job Was Processed.')).toBeTruthy()
  })

  test('submits a chat question and renders response details', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    const questionInput = screen.getByLabelText('Question') as HTMLTextAreaElement
    await user.type(questionInput, 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(questionInput.value).toBe('')
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
    await user.click(
      screen.getByRole('button', { name: 'Expand response details' }),
    )
    expect(
      screen.getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText('Score 0.88')).toBeTruthy()
    expect(screen.getByText('URL Source')).toBeTruthy()
    expect(screen.getByText('Version 2')).toBeTruthy()
    expect(screen.getByText('Chars 12-98')).toBeTruthy()
    expect(screen.getByText('rag_search')).toBeTruthy()
    expect(
      screen.getByRole('heading', { name: 'Deployment question' }),
    ).toBeTruthy()
    expect(
      screen
        .getByRole('button', { name: /Abrir sesión Deployment question/ })
        .closest('[data-slot="data-list-item"]')
        ?.getAttribute('data-selected'),
    ).toBe('')
  })

  test('keeps chat retrieval quantity controls in runtime settings instead of the composer', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    expect(screen.queryByLabelText('Retrieval limit')).toBeNull()

    await user.type(screen.getByLabelText('Question'), 'How wide should search be?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChatStream).toHaveBeenCalledWith(
      projectId,
      {
        message: 'How wide should search be?',
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
    expect(
      sessionButton
        .closest('[data-slot="data-list-item"]')
        ?.getAttribute('data-selected'),
    ).toBe('')

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

    await user.click(screen.getByRole('button', { name: 'Open Minimap Sidebar' }))
    expect(
      screen.getByRole('tab', { name: 'Minimap' }).getAttribute('aria-selected'),
    ).toBe('true')
    await user.click(
      screen.getByRole('button', { name: 'Expand response details' }),
    )

    // Citation chips + details panel share the same accessible name.
    await user.click(
      screen.getAllByRole('button', {
        name: 'View source https://docs.local/runbook',
      })[0],
    )

    expect(client.getSource).toHaveBeenCalledWith(projectId, 'source-1')
    expect(
      screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected'),
    ).toBe('true')
    const viewer = await screen.findByRole('region', { name: 'Source Viewer' })
    expect(within(viewer).getByText('https://docs.local/runbook')).toBeTruthy()
    expect(within(viewer).getByText('url')).toBeTruthy()
    expect(within(viewer).getByText('runbook')).toBeTruthy()
    expect(
      within(viewer).getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(within(viewer).getByText('Deployment runbook')).toBeTruthy()
    expect(within(viewer).getByText('ops')).toBeTruthy()
  })

  test('renders the submitted question as a sticky collapsible prompt', async () => {
    const user = userEvent.setup()
    const longQuestion =
      'How do I retry the import after the deployment worker failed and which runbook should I check before rerunning the job?'
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), longQuestion)
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await screen.findByText(chatResponse.answer)

    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
    const prompt = within(transcript).getByRole('button', {
      name: 'Expand full question',
    })
    expect(prompt.textContent).toContain('...')
    expect(prompt.textContent).not.toBe(longQuestion)
    expect(prompt.closest('[data-slot="chat-question-sticky"]')).toBeTruthy()

    await user.click(prompt)

    expect(prompt.textContent).toBe(longQuestion)
    expect(prompt.getAttribute('aria-label')).toBe('Collapse full question')
  })

  test('consolidates response sources and tool calls under a compact details panel', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(),
      askChatStream: vi.fn(async () => chatResponseWithSteps),
      getSource: vi.fn(async () => citationSource),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await screen.findByText(chatResponseWithSteps.answer)

    expect(screen.queryByRole('region', { name: 'Citations' })).toBeNull()
    expect(screen.queryByRole('region', { name: 'Tool calls' })).toBeNull()
    expect(
      screen.queryByRole('button', { name: 'Expand response details' }),
    ).toBeNull()

    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
    const stepper = within(transcript).getByRole('region', {
      name: 'Chat Pipeline Steps',
    })
    const detailsToggle = within(stepper).getByRole('button', {
      name: /Expand Chat Steps/,
    })
    expect(detailsToggle.textContent).toContain('1 Source')

    await user.click(detailsToggle)

    expect(within(transcript).getAllByText('qwen-plus').length).toBeGreaterThan(0)
    expect(within(transcript).getAllByText('168 Tokens').length).toBeGreaterThan(0)
    expect(within(transcript).getAllByText('$0.0042').length).toBeGreaterThan(0)
    expect(within(transcript).getByText('rag_search')).toBeTruthy()
    expect(within(transcript).getByText('deployment retry runbook')).toBeTruthy()
    // Source id may appear on answer citation chips and in expanded details.
    expect(
      within(transcript).getAllByText('https://docs.local/runbook').length,
    ).toBeGreaterThan(0)
    expect(
      within(transcript).getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()

    await user.click(
      within(transcript).getAllByRole('button', {
        name: 'View source https://docs.local/runbook',
      })[0],
    )
    expect(client.getSource).toHaveBeenCalledWith(projectId, 'source-1')
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
      screen.getByRole('button', { name: 'Expand response details' }),
    )
    await user.click(
      screen.getAllByRole('button', {
        name: 'View source https://docs.local/runbook',
      })[0],
    )

    const viewer = await screen.findByRole('region', { name: 'Source Viewer' })
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
        handlers.onStep?.({
          id: 'retrieval',
          status: 'start',
          detail: { query: 'streaming evidence' },
        })
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
    const stepper = screen.getByRole('region', {
      name: 'Chat Pipeline Steps',
    })
    expect(within(stepper).getAllByText('retrieval').length).toBeGreaterThan(0)
    expect(
      within(stepper).getByRole('button', { name: /Expand Chat Steps/ }),
    ).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Citations' })).toBeNull()
    expect(screen.queryByText('No citations returned.')).toBeNull()
    expect(
      screen.queryByText('Citations appear after the final response.'),
    ).toBeNull()
    await user.click(
      within(stepper).getByRole('button', { name: /Expand Chat Steps/ }),
    )
    expect(screen.getAllByText('streaming evidence').length).toBeGreaterThan(0)

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

  test('loads applied memories after JSON chat fallback succeeds', async () => {
    const user = userEvent.setup()
    const approvedMemory = {
      content: 'Prefer concise answers',
      created_at: '2026-08-05T00:00:00Z',
      id: 'mem-applied-1',
      project_id: null,
      reviewed_at: '2026-08-05T00:00:00Z',
      reviewed_by_user_id: 'user-1',
      status: 'approved' as const,
      user_id: 'user-1',
    }
    const listUserMemories = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'approved') {
        return { items: [approvedMemory] }
      }
      return { items: [] }
    })
    const client = createClientStub({
      askChat: vi.fn(async () => chatResponse),
      askChatStream: vi.fn(async () => {
        throw new TypeError('stream unavailable')
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
      listUserMemories,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChat).toHaveBeenCalled()
    expect(
      await screen.findByRole('region', { name: 'Memory Applied' }),
    ).toBeTruthy()
    expect(screen.getByText('Prefer concise answers')).toBeTruthy()
    expect(listUserMemories).toHaveBeenCalledWith({
      project_id: projectId,
      status: 'approved',
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
    await user.click(await screen.findByRole('button', { name: 'Cancel Request' }))

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

    // Failed transcript surface + composer InlineFeedback both expose role=alert.
    const alerts = await screen.findAllByRole('alert')
    expect(
      alerts.some((node) => node.textContent?.includes('backend unavailable')),
    ).toBe(true)
    expect(
      alerts.some((node) => node.textContent?.includes('Request failed.')),
    ).toBe(true)
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(
      'Why did it fail?',
    )
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })
  })

  test('redacts secrets from chat request error copy', async () => {
    const user = userEvent.setup()
    const leak = new ApiClientError('auth failed with sk-abcdefghijklmnop', {
      detail: 'auth failed with sk-abcdefghijklmnop',
      status: 401,
    })
    const client = createClientStub({
      askChat: vi.fn(async () => {
        throw leak
      }),
      askChatStream: vi.fn(async () => {
        throw leak
      }),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'Leak?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    const alerts = await screen.findAllByRole('alert')
    expect(alerts.some((node) => node.textContent?.includes('[redacted]'))).toBe(
      true,
    )
    expect(
      alerts.some((node) => node.textContent?.includes('sk-abcdefghijklmnop')),
    ).toBe(false)
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
        name: /Abrir sesión Deployment question/,
      }),
    ).toBeTruthy()
    expect(within(navigation).getByTitle('Training')).toBeTruthy()
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })

    await user.click(
      within(navigation).getByRole('button', { name: 'Sesiones con entrenamiento' }),
    )
    expect(
      await within(navigation).findByRole('button', {
        name: /Abrir sesión Deployment question/,
      }),
    ).toBeTruthy()

    await user.click(
      within(navigation).getByRole('button', { name: 'Sesiones archivadas' }),
    )
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
        name: /Abrir sesión Deployment question/,
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
      name: /Abrir sesión Deployment question/,
    })
    await user.click(screen.getByRole('button', { name: 'Ver más' }))

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
      name: /Abrir sesión Deployment question/,
    })
    await user.click(
      screen.getByRole('button', { name: 'Opciones de Deployment question' }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Renombrar' }))
    const input = await screen.findByLabelText('Nuevo nombre de sesión')
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
    await user.click(screen.getByRole('menuitem', { name: 'Archivar' }))

    expect(archiveChatSession).toHaveBeenCalledWith(projectId, 'session-123')
  })

  test('selects a history session as the active chat without opening the inspector', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: /Abrir sesión Deployment question/,
      }),
    )

    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      archived: false,
      limit: 15,
    })
    expect(client.getChatSession).toHaveBeenCalledWith(projectId, 'session-123')
    expect(
      screen.queryByRole('complementary', { name: 'Workspace Inspector' }),
    ).toBeNull()
    expect(screen.getByLabelText('Question')).toBeTruthy()
    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
    expect(
      await within(transcript).findByText(
        'The import failed because the worker was not running.',
      ),
    ).toBeTruthy()
    expect(within(transcript).getByText('What failed during deployment?')).toBeTruthy()
    expect(
      within(transcript).getByRole('button', {
        name: 'Expand response details',
      }),
    ).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await screen.findByText('The import failed because the worker was not running.')

    await user.click(screen.getByRole('button', { name: 'Nuevo chat' }))

    expect(
      screen
        .getByRole('button', { name: /Abrir sesión Deployment question/ })
        .closest('[data-slot="data-list-item"]')
        ?.hasAttribute('data-selected'),
    ).toBe(false)
    expect(screen.getByText('No Response Yet.')).toBeTruthy()
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe(
      '',
    )
  })

  test('refreshes open inspector session detail after a successful ask', async () => {
    const user = userEvent.setup()
    const getChatSession = vi.fn(async () => sessionDetailResponse)
    const client = createClientStub({
      askChatStream: vi.fn(async () => chatResponse),
      getChatSession,
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))
    await screen.findByRole('region', { name: 'Selected Session Detail' })
    expect(getChatSession).toHaveBeenCalledTimes(1)

    await user.type(screen.getByLabelText('Question'), 'Follow-up question')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()

    await waitFor(() => expect(getChatSession).toHaveBeenCalledTimes(2))
    expect(getChatSession).toHaveBeenLastCalledWith(projectId, 'session-123')
    expect(
      await screen.findByRole('region', { name: 'Selected Session Detail' }),
    ).toBeTruthy()
  })

  test('hydrates chat response tools from only the latest turn', async () => {
    const user = userEvent.setup()
    const multiTurnDetail: ChatSessionDetailResponse = {
      ...sessionDetailResponse,
      messages: [
        {
          content: 'First question',
          created_at: '2026-06-21T00:00:00Z',
          message_id: 'message-user-1',
          metadata: null,
          role: 'user',
        },
        {
          content: 'First answer',
          created_at: '2026-06-21T00:00:02Z',
          message_id: 'message-assistant-1',
          metadata: null,
          role: 'assistant',
        },
        {
          content: 'Second question',
          created_at: '2026-06-21T00:01:00Z',
          message_id: 'message-user-2',
          metadata: null,
          role: 'user',
        },
        {
          content: 'Second answer only',
          created_at: '2026-06-21T00:01:02Z',
          message_id: 'message-assistant-2',
          metadata: null,
          role: 'assistant',
        },
      ],
      retrieval_runs: [
        {
          ...sessionDetailResponse.retrieval_runs[0],
          created_at: '2026-06-21T00:00:01Z',
          query: 'first turn query',
          retrieval_run_id: 'retrieval-run-1',
          tool_call_id: 'tool-call-1',
        },
        {
          ...sessionDetailResponse.retrieval_runs[0],
          created_at: '2026-06-21T00:01:01Z',
          query: 'second turn query',
          retrieval_run_id: 'retrieval-run-2',
          retrieved_chunks: [
            {
              ...sessionDetailResponse.retrieval_runs[0].retrieved_chunks[0],
              citation: {
                snippet: 'Second turn citation only.',
                source_external_id: 'https://docs.local/second',
                source_id: 'source-2',
              },
              retrieved_chunk_id: 'retrieved-chunk-2',
            },
          ],
          tool_call_id: 'tool-call-2',
        },
      ],
      tool_calls: [
        {
          ...sessionDetailResponse.tool_calls[0],
          arguments: { query: 'first turn query' },
          created_at: '2026-06-21T00:00:01Z',
          tool_call_id: 'tool-call-1',
          tool_name: 'rag_search',
          updated_at: '2026-06-21T00:00:01Z',
        },
        {
          ...sessionDetailResponse.tool_calls[0],
          arguments: { query: 'second turn query' },
          created_at: '2026-06-21T00:01:01Z',
          tool_call_id: 'tool-call-2',
          tool_name: 'web_lookup',
          updated_at: '2026-06-21T00:01:01Z',
        },
      ],
    }
    const client = createClientStub({
      getChatSession: vi.fn(async () => multiTurnDetail),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: /Abrir sesión Deployment question/,
      }),
    )

    expect(await screen.findByText('Second answer only')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Expand response details' }),
    )
    expect(screen.getByText('web_lookup')).toBeTruthy()
    expect(screen.getByText('second turn query')).toBeTruthy()
    expect(screen.queryByText('rag_search')).toBeNull()
    expect(screen.queryByText('first turn query')).toBeNull()
    expect(screen.getByText('Second turn citation only.')).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const sessionMessages = await screen.findByRole('list', {
      name: 'Session Messages',
    })
    expect(
      within(sessionMessages).getByText(
        'The import failed because the worker was not running.',
      ),
    ).toBeTruthy()
    const sessionDetail = screen.getByRole('region', {
      name: 'Selected Session Detail',
    })
    expect(within(sessionDetail).getByText('rag_search')).toBeTruthy()
    expect(within(sessionDetail).getByText('deployment import failure')).toBeTruthy()
    expect(within(sessionDetail).getByText('Default Dense Retrieval')).toBeTruthy()
    expect(within(sessionDetail).getByText('Latency 41 ms')).toBeTruthy()
    expect(
      within(sessionDetail).getByText(
        'Confirm the worker is running before retrying the import.',
      ),
    ).toBeTruthy()
    expect(within(sessionDetail).getByText('Rank 1')).toBeTruthy()
    expect(within(sessionDetail).getByText('Dense Score 0.84')).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const sessionDetail = await screen.findByRole('region', {
      name: 'Selected Session Detail',
    })
    await user.click(
      within(sessionDetail).getByRole('button', {
        name: 'View source https://docs.local/deploy',
      }),
    )

    expect(client.getSource).toHaveBeenCalledWith(projectId, 'source-1')
    const viewer = await screen.findByRole('region', { name: 'Source Viewer' })
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const context = await screen.findByRole('region', {
      name: 'Session Context',
    })
    expect(within(context).getByText('Prompt default')).toBeTruthy()
    expect(within(context).getByText('qwen-plus')).toBeTruthy()
    expect(within(context).getByText('$0.0042')).toBeTruthy()
    expect(within(context).getByText('168 Tokens')).toBeTruthy()
    expect(within(context).getByText('230 ms')).toBeTruthy()
  })

  test('shows selected session question and usage inside response details', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(
      await screen.findByRole('button', {
        name: /Abrir sesión Deployment question/,
      }),
    )

    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
    expect(within(transcript).getByText('What failed during deployment?')).toBeTruthy()

    const detailsToggle = within(transcript).getByRole('button', {
      name: 'Expand response details',
    })
    expect(detailsToggle.textContent).toContain('1 Source')
    expect(detailsToggle.textContent).toContain('1 Tool Call')
    expect(detailsToggle.textContent).toContain('Usage')

    await user.click(detailsToggle)

    expect(within(transcript).getByText('qwen-plus')).toBeTruthy()
    expect(within(transcript).getByText('168 Tokens')).toBeTruthy()
    expect(within(transcript).getByText('$0.0042')).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const context = await screen.findByRole('region', {
      name: 'Session Context',
    })
    expect(within(context).getByText('Unknown Cost')).toBeTruthy()
    expect(within(context).getByText('Unknown Tokens')).toBeTruthy()
    expect(within(context).getByText('Unknown Latency')).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Minimap Sidebar' }))

    const minimap = await screen.findByRole('navigation', {
      name: 'Conversation Minimap',
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    const stepper = await screen.findByRole('region', {
      name: 'Internal Action Stepper',
    })
    expect(within(stepper).getByText('Tool Call Succeeded')).toBeTruthy()
    expect(within(stepper).getByText('Retrieval Dense')).toBeTruthy()
    expect(within(stepper).getByText('Provider Usage Succeeded')).toBeTruthy()
    expect(within(stepper).getByText('rag_search')).toBeTruthy()
    expect(within(stepper).getByText('deployment import failure')).toBeTruthy()
    expect(within(stepper).getByText('qwen-plus')).toBeTruthy()
    expect(within(stepper).getByText('39 ms')).toBeTruthy()
    expect(within(stepper).getByText('Rank 1')).toBeTruthy()
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
        name: /Abrir sesión Deployment question/,
      }),
    )
    await user.click(screen.getByRole('button', { name: 'Open Context Sidebar' }))

    expect(await screen.findByText('chat session not found')).toBeTruthy()
    expect(
      screen.getByRole('button', {
        name: /Abrir sesión Deployment question/,
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
    await chooseRadixSelectOption(user, screen.getByLabelText('Status'), 'Failed')
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

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
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

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
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    const statusSection = await screen.findByRole('region', {
      name: 'Status Breakdown',
    })
    expect(within(statusSection).getByText('Succeeded')).toBeTruthy()
    expect(within(statusSection).getByText('10 Sessions')).toBeTruthy()
    expect(within(statusSection).getByText('Failed')).toBeTruthy()
    expect(within(statusSection).getByText('2 Sessions')).toBeTruthy()

    const errorsSection = screen.getByRole('region', { name: 'Error messages' })
    expect(within(errorsSection).getByText('runner failed')).toBeTruthy()
    expect(within(errorsSection).getByText('2 Occurrences')).toBeTruthy()

    const providerSection = screen.getByRole('region', { name: 'Provider usage' })
    expect(within(providerSection).getByText('chat')).toBeTruthy()
    expect(within(providerSection).getByText('qwen')).toBeTruthy()
    expect(within(providerSection).getByText('qwen-plus')).toBeTruthy()
    expect(within(providerSection).getByText('1,840')).toBeTruthy()

    const healthSection = screen.getByRole('region', { name: 'Session Health' })
    expect(within(healthSection).getByText(/83\.3%\s*Success/i)).toBeTruthy()
  })

  test('renders costs observability content without error or health sections', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Costs')
    expect(screen.getByLabelText('Project ID')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    const metrics = await screen.findByLabelText('Cost observability metrics')
    expect(within(metrics).getByText('Estimated cost')).toBeTruthy()
    expect(within(metrics).getByText('$0.1234')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Provider usage' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Error messages' })).toBeNull()
    expect(screen.queryByRole('region', { name: 'Session Health' })).toBeNull()
  })

  test('renders errors observability content without provider usage', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Errors')
    expect(screen.getByLabelText('Status')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    const metrics = await screen.findByLabelText('Error observability metrics')
    expect(within(metrics).getByText('Errors')).toBeTruthy()
    expect(within(metrics).getByText('3')).toBeTruthy()
    const errorsSection = screen.getByRole('region', { name: 'Error messages' })
    expect(within(errorsSection).getByText('runner failed')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Session Health' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Provider usage' })).toBeNull()
  })

  test('renders latency observability content without error or cost metrics', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Observability', 'Latency')
    expect(screen.getByLabelText('Created from')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    const metrics = await screen.findByLabelText('Latency observability metrics')
    expect(within(metrics).getByText('Latency')).toBeTruthy()
    expect(within(metrics).getByText('410 ms')).toBeTruthy()
    const latencySection = screen.getByRole('region', { name: 'Provider latency' })
    expect(within(latencySection).getByText('qwen-plus')).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Error messages' })).toBeNull()
    expect(screen.queryByText('Estimated cost')).toBeNull()
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
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    expect(await screen.findByText('No Status Data Yet.')).toBeTruthy()
    expect(screen.getByText('No Provider Usage Groups Yet.')).toBeTruthy()
    expect(screen.getByText('No Error Messages Yet.')).toBeTruthy()
    expect(screen.getByText('No Sessions in This Filter Window.')).toBeTruthy()
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
    await chooseRadixSelectOption(user, screen.getByLabelText('Status'), 'Failed')
    await user.click(screen.getByRole('button', { name: 'Refresh Summary' }))

    const alerts = await screen.findAllByRole('alert')
    expect(
      alerts.some((node) =>
        node.textContent?.includes('observability unavailable'),
      ),
    ).toBe(true)
    expect(
      (screen.getByLabelText('Created from') as HTMLInputElement).value,
    ).toBe('2026-06-21T00:00:00Z')
    expect(screen.getByLabelText('Status').textContent).toContain('Failed')
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
    expect(screen.queryByRole('button', { name: 'Refresh runtime' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Refresh connections' })).toBeNull()

    expect(client.listProviderConnections).toHaveBeenCalled()
    expect((await screen.findAllByText('qwen-hosted')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('local-chat').length).toBeGreaterThan(0)
    expect(screen.getByText('API Key Configured / Last Four cret')).toBeTruthy()
    expect(screen.queryByText('sk-hosted-secret')).toBeNull()
    expect(screen.queryByLabelText('Connection ID')).toBeNull()
    expect(screen.queryByLabelText('Secret connection')).toBeNull()

    await chooseRadixSelectOption(user, screen.getByLabelText('Provider'), 'Qwen')
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Connection Type'),
      'Hosted',
    )
    fireEvent.change(screen.getByLabelText('Base URL'), {
      target: { value: 'https://dashscope.example.test/compatible-mode/v1' },
    })
    const capabilitiesCombobox = screen.getByRole('combobox', {
      name: 'Capabilities',
    })
    expect(
      screen.getByRole('button', { name: 'Remove Chat capability' }),
    ).toBeTruthy()
    const saveConnectionButton = screen.getByRole('button', {
      name: 'Save Connection',
    }) as HTMLButtonElement
    await user.click(
      screen.getByRole('button', {
        name: 'Remove Chat capability',
      }),
    )
    expect(saveConnectionButton.disabled).toBe(true)
    // Combobox input is the capability filter (no separate textbox).
    await user.type(capabilitiesCombobox, 'chat')
    await user.click(
      await screen.findByRole('option', {
        name: 'Add Chat capability',
      }),
    )
    await user.type(capabilitiesCombobox, 'dense')
    await user.click(
      await screen.findByRole('option', {
        name: 'Add Dense Embedding capability',
      }),
    )
    expect(saveConnectionButton.disabled).toBe(false)
    expect(
      screen.getByRole('button', { name: 'Remove Dense Embedding capability' }),
    ).toBeTruthy()
    fireEvent.change(screen.getByLabelText('API key'), {
      target: { value: 'sk-hosted-secret' },
    })
    await user.click(saveConnectionButton)

    expect(client.createProviderConnection).toHaveBeenCalledWith({
      api_key: 'sk-hosted-secret',
      base_url: 'https://dashscope.example.test/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding'],
      connection_type: 'hosted',
      metadata: null,
      provider: 'qwen',
    })
    expect((screen.getByLabelText('API key') as HTMLInputElement).value).toBe('')
    expect(screen.queryByText('sk-hosted-secret')).toBeNull()

    await openSettingsSubmodule(user, 'Runtime', 'Model Catalog')
    await user.click(screen.getByRole('button', { name: 'Refresh Catalog' }))

    expect(client.listProviderModels).toHaveBeenCalled()
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Model sync connection'),
      /Hosted Qwen/,
    )
    await user.click(screen.getByRole('button', { name: 'Sync Models' }))

    expect(client.syncProviderModels).toHaveBeenCalledWith('qwen-hosted')

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    expect(screen.queryByRole('button', { name: 'Save secret' })).toBeNull()

    await openSettingsSubmodule(user, 'Runtime', 'Global Defaults')
    await user.click(screen.getByRole('button', { name: 'Reload Global Defaults' }))

    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Global slot'),
      'Dense Embedding',
    )
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Global slot connection'),
      /Hosted Qwen/,
    )
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Global slot model'),
      'text-embedding-v4',
    )
    await user.click(screen.getByRole('button', { name: 'Save Global Slot' }))

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
    await user.click(screen.getByRole('button', { name: 'Save Chat Retrieval' }))

    expect(client.updateChatRetrievalSettings).toHaveBeenCalledWith({
      retrieval_limit: 7,
      rerank_enabled: true,
      rerank_candidate_limit: 12,
    })
  })

  test('deletes runtime connections only after exact connection ID confirmation', async () => {
    const user = userEvent.setup()
    const deleteProviderConnection = vi.fn(async () => ({ deleted: true }))
    const client = createClientStub({
      deleteProviderConnection,
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    const providerConnections = screen.getByRole('region', {
      name: 'Provider connections',
    })
    expect(
      await within(providerConnections).findByText('qwen-hosted'),
    ).toBeTruthy()

    await user.click(
      within(providerConnections).getByRole('button', {
        name: 'Delete qwen-hosted connection',
      }),
    )

    const confirmInput = screen.getByLabelText(
      'Confirm Connection ID',
    ) as HTMLInputElement
    const deleteButton = screen.getByRole('button', {
      name: 'Delete Connection',
    }) as HTMLButtonElement

    expect(deleteButton.disabled).toBe(true)
    await user.type(confirmInput, 'wrong-id')
    expect(deleteButton.disabled).toBe(true)
    await user.clear(confirmInput)
    await user.type(confirmInput, 'qwen-hosted')
    expect(deleteButton.disabled).toBe(false)

    await user.click(deleteButton)

    expect(deleteProviderConnection).toHaveBeenCalledWith('qwen-hosted')
    await waitFor(() => {
      expect(within(providerConnections).queryByText('qwen-hosted')).toBeNull()
    })
    expect(within(providerConnections).getByText('local-chat')).toBeTruthy()
  })

  test('checks runtime provider connections without syncing models', async () => {
    const user = userEvent.setup()
    const checkProviderConnection = vi.fn(async () => ({
      connection_id: 'qwen-hosted',
      message: 'provider model list succeeded',
      model_count: 2,
      ok: true,
    }))
    const syncProviderModels = vi.fn()
    const client = createClientStub({
      checkProviderConnection,
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      syncProviderModels,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Connections')
    const providerConnections = screen.getByRole('region', {
      name: 'Provider connections',
    })
    expect(
      await within(providerConnections).findByText('qwen-hosted'),
    ).toBeTruthy()

    await user.click(
      within(providerConnections).getByRole('button', {
        name: 'Check qwen-hosted connection',
      }),
    )

    expect(checkProviderConnection).toHaveBeenCalledWith('qwen-hosted')
    expect(syncProviderModels).not.toHaveBeenCalled()
    expect(
      await within(providerConnections).findByText(
        'Connection check passed: 2 provider models reachable.',
      ),
    ).toBeTruthy()
  })

  test('loads runtime connections on entry without calling unrelated runtime endpoints', async () => {
    const user = userEvent.setup()
    const listChatModels = vi.fn(async () => {
      throw new ApiClientError('chat models unavailable', {
        detail: 'chat models unavailable',
        status: 503,
      })
    })
    const listProviderModels = vi.fn(async () => {
      throw new ApiClientError('provider models unavailable', {
        detail: 'provider models unavailable',
        status: 503,
      })
    })
    const listRuntimeSlotDefaults = vi.fn(async () => {
      throw new ApiClientError('slot defaults unavailable', {
        detail: 'slot defaults unavailable',
        status: 503,
      })
    })
    const getChatRetrievalSettings = vi.fn(async () => {
      throw new ApiClientError('chat retrieval unavailable', {
        detail: 'chat retrieval unavailable',
        status: 503,
      })
    })
    const getProjectRuntimeSettings = vi.fn(async () => {
      throw new ApiClientError('project runtime unavailable', {
        detail: 'project runtime unavailable',
        status: 503,
      })
    })
    const client = createClientStub({
      getChatRetrievalSettings,
      getProjectRuntimeSettings,
      listChatModels,
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels,
      listRuntimeSlotDefaults,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Connections')

    expect(await screen.findByText('qwen-hosted')).toBeTruthy()
    expect(client.listProviderConnections).toHaveBeenCalledTimes(1)
    expect(listChatModels).not.toHaveBeenCalled()
    expect(listProviderModels).not.toHaveBeenCalled()
    expect(listRuntimeSlotDefaults).not.toHaveBeenCalled()
    expect(getChatRetrievalSettings).not.toHaveBeenCalled()
    expect(getProjectRuntimeSettings).not.toHaveBeenCalled()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  test('loads selected provider model catalog without syncing models', async () => {
    const user = userEvent.setup()
    const listProviderModels = vi.fn(
      async (params: Parameters<ApiClient['listProviderModels']>[0]) => {
        if (params?.connection_id === 'qwen-hosted') {
          return {
            items: providerModelsResponse.items.filter(
              (model) => model.connection_id === 'qwen-hosted',
            ),
          }
        }
        return { items: [] }
      },
    )
    const syncProviderModels = vi.fn()
    const client = createClientStub({
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels,
      syncProviderModels,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Model Catalog')
    await user.click(screen.getByRole('button', { name: 'Refresh Catalog' }))
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Model sync connection'),
      /Hosted Qwen/,
    )

    await waitFor(() =>
      expect(listProviderModels).toHaveBeenLastCalledWith({
        connection_id: 'qwen-hosted',
      }),
    )
    expect(syncProviderModels).not.toHaveBeenCalled()
    expect(await screen.findByText('qwen-plus')).toBeTruthy()
    expect(screen.getByText('text-embedding-v4')).toBeTruthy()
  })

  test('loads the first provider model catalog on entry without syncing models', async () => {
    const user = userEvent.setup()
    const listProviderModels = vi.fn(
      async (params: Parameters<ApiClient['listProviderModels']>[0]) => {
        if (params?.connection_id === 'qwen-hosted') {
          return {
            items: providerModelsResponse.items.filter(
              (model) => model.connection_id === 'qwen-hosted',
            ),
          }
        }
        return { items: [] }
      },
    )
    const syncProviderModels = vi.fn()
    const client = createClientStub({
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels,
      syncProviderModels,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Model Catalog')

    await waitFor(() =>
      expect(listProviderModels).toHaveBeenCalledWith({
        connection_id: 'qwen-hosted',
      }),
    )
    expect(syncProviderModels).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Model sync connection').textContent).toContain(
      'Hosted Qwen',
    )
    expect(await screen.findByText('qwen-plus')).toBeTruthy()
  })

  test('edits the selected model catalog connection without exposing the secret', async () => {
    const user = userEvent.setup()
    const upsertProviderConnection = vi.fn(
      async (
        connectionId: string,
        body: Parameters<ApiClient['upsertProviderConnection']>[1],
      ) => ({
        ...providerConnectionsResponse.items[0],
        base_url: body.base_url ?? null,
        capabilities: body.capabilities,
        connection_id: connectionId,
        connection_type: body.connection_type,
        metadata: body.metadata ?? null,
        provider: body.provider,
        updated_at: '2026-06-24T00:00:02Z',
      }),
    )
    const client = createClientStub({
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => ({ items: [] })),
      upsertProviderConnection,
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Model Catalog')
    await user.click(screen.getByRole('button', { name: 'Refresh Catalog' }))
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Model sync connection'),
      /Hosted Qwen/,
    )
    await user.click(screen.getByRole('button', { name: 'Edit connection' }))

    expect(
      screen.getByRole('heading', { level: 2, name: 'Connections' }),
    ).toBeTruthy()
    expect(screen.queryByText('sk-hosted-secret')).toBeNull()
    expect((screen.getByLabelText('API key') as HTMLInputElement).value).toBe(
      '',
    )

    await user.clear(screen.getByLabelText('Base URL'))
    await user.type(
      screen.getByLabelText('Base URL'),
      'https://dashscope.aliyuncs.com/compatible-mode/v1',
    )
    await user.type(screen.getByLabelText('API key'), 'sk-new-secret')
    await user.click(screen.getByRole('button', { name: 'Update Connection' }))

    expect(upsertProviderConnection).toHaveBeenCalledWith('qwen-hosted', {
      api_key: 'sk-new-secret',
      base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding', 'rerank'],
      connection_type: 'hosted',
      metadata: { label: 'Hosted Qwen' },
      provider: 'qwen',
    })
    expect((screen.getByLabelText('API key') as HTMLInputElement).value).toBe(
      '',
    )
    expect(screen.queryByText('sk-new-secret')).toBeNull()
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

    await openSettingsSubmodule(user, 'Runtime', 'Project Overrides')
    await user.click(screen.getByRole('button', { name: 'Reload project settings' }))

    const projectSettings = await screen.findByRole('region', {
      name: 'Project runtime settings',
    })
    expect(within(projectSettings).getAllByText('Dense Embedding').length).toBeGreaterThan(0)
    expect(within(projectSettings).getAllByText('Inherited').length).toBeGreaterThan(0)
    expect(within(projectSettings).getAllByText('Overridden').length).toBeGreaterThan(0)

    await chooseRadixSelectOption(user, screen.getByLabelText('Project slot'), 'Chat')
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Project slot connection'),
      /local-chat/,
    )
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Project slot model'),
      'llama3.1:8b',
    )
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
    await chooseRadixSelectOption(
      user,
      within(projectSettings).getByLabelText('Rerank'),
      'Off',
    )
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

    await user.click(screen.getByRole('button', { name: 'Reset Chat to global' }))

    expect(client.deleteProjectRuntimeSlotOverride).toHaveBeenCalledWith(
      projectId,
      'chat',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reset chat retrieval to global' }),
    )

    expect(client.deleteProjectChatRetrievalSettings).toHaveBeenCalledWith(projectId)
  })

  test('clears project runtime settings and override forms when switching projects', async () => {
    const user = userEvent.setup()
    const nextProject: Project = {
      ...projectSummary,
      id: '22222222-2222-4222-8222-222222222222',
      name: 'Second',
    }
    const client = createClientStub({
      getProjectRuntimeSettings: vi.fn(async () => projectRuntimeSettings),
      listProjects: vi.fn(async () => ({
        items: [projectSummary, nextProject],
      })),
      getChatRetrievalSettings: vi.fn(async () => ({
        max_limit: 50,
        rerank_candidate_limit: 10,
        rerank_enabled: true,
        retrieval_limit: 5,
      })),
      listChatModels: vi.fn(async () => chatModelsResponse),
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
      listRuntimeSlotDefaults: vi.fn(async () => runtimeSlotDefaultsResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Project Overrides')
    await user.click(screen.getByRole('button', { name: 'Reload project settings' }))
    const projectSettings = await screen.findByRole('region', {
      name: 'Project runtime settings',
    })
    expect(
      (await within(projectSettings).findAllByText('Overridden')).length,
    ).toBeGreaterThan(0)
    await chooseRadixSelectOption(user, screen.getByLabelText('Project slot'), 'Chat')
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Project slot connection'),
      /local-chat/,
    )
    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Project slot model'),
      'llama3.1:8b',
    )

    await user.click(await screen.findByRole('button', { name: /Project selector: Demo/ }))
    await user.click(screen.getByRole('option', { name: 'Select project Second' }))

    expect(
      await screen.findByRole('button', { name: /Project selector: Second/ }),
    ).toBeTruthy()
    const updatedProjectSettings = screen.getByRole('region', {
      name: 'Project runtime settings',
    })
    expect(within(updatedProjectSettings).getByText('No Project Runtime Settings Yet.')).toBeTruthy()
    expect(within(updatedProjectSettings).queryByText('overridden')).toBeNull()
    expect(screen.getByLabelText('Project slot connection').textContent).toContain(
      'Select Connection',
    )
    expect(screen.getByLabelText('Project slot model').textContent).toContain(
      'No Models Yet',
    )
  })

  test('ignores stale project runtime reloads after switching projects', async () => {
    const user = userEvent.setup()
    const nextProject: Project = {
      ...projectSummary,
      id: '22222222-2222-4222-8222-222222222222',
      name: 'Second',
    }
    const projectSettingsRequest = createDeferred<ProjectRuntimeSettings>()
    const getProjectRuntimeSettings = vi.fn(
      async () => await projectSettingsRequest.promise,
    )
    const client = createClientStub({
      getProjectRuntimeSettings,
      listProjects: vi.fn(async () => ({
        items: [projectSummary, nextProject],
      })),
      listProviderConnections: vi.fn(async () => providerConnectionsResponse),
      listProviderModels: vi.fn(async () => providerModelsResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await openSettingsSubmodule(user, 'Runtime', 'Project Overrides')
    await user.click(screen.getByRole('button', { name: 'Reload project settings' }))

    await waitFor(() =>
      expect(getProjectRuntimeSettings).toHaveBeenCalledWith(projectId),
    )

    await user.click(await screen.findByRole('button', { name: /Project selector: Demo/ }))
    await user.click(screen.getByRole('option', { name: 'Select project Second' }))

    expect(
      await screen.findByRole('button', { name: /Project selector: Second/ }),
    ).toBeTruthy()

    await act(async () => {
      projectSettingsRequest.resolve(projectRuntimeSettings)
      await projectSettingsRequest.promise
    })

    const updatedProjectSettings = screen.getByRole('region', {
      name: 'Project runtime settings',
    })
    expect(within(updatedProjectSettings).getByText('No Project Runtime Settings Yet.')).toBeTruthy()
    expect(within(updatedProjectSettings).queryByText('overridden')).toBeNull()
    expect(within(updatedProjectSettings).queryByText('local-chat')).toBeNull()
    expect(within(updatedProjectSettings).queryByText('llama3.1:8b')).toBeNull()
    const reloadProjectSettingsButton = screen.getByRole('button', {
      name: /^(Reload project settings|Refreshing\.\.\.)$/,
    }) as HTMLButtonElement
    expect(reloadProjectSettingsButton.disabled).toBe(false)
    expect(reloadProjectSettingsButton.textContent).toBe('Reload project settings')
    expect(screen.queryByRole('alert')).toBeNull()
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

    await openSettingsSubmodule(user, 'Runtime', 'Global Defaults')
    await user.click(screen.getByRole('button', { name: 'Reload Global Defaults' }))

    await chooseRadixSelectOption(
      user,
      screen.getByLabelText('Global slot'),
      'Dense Embedding',
    )
    await user.click(screen.getByLabelText('Global slot connection'))
    const hostedQwenOption = await screen.findByRole('option', {
      name: /Hosted Qwen \(Qwen\/Hosted\)/,
    })
    expect(hostedQwenOption).toBeTruthy()
    await user.click(hostedQwenOption)

    expect(
      screen.getByText(
        'Sync models for qwen-hosted before saving Dense Embedding.',
      ),
    ).toBeTruthy()
    const saveButton = screen.getByRole('button', {
      name: 'Save Global Slot',
    }) as HTMLButtonElement
    expect(saveButton.disabled).toBe(true)

    await user.click(saveButton)

    expect(upsertRuntimeSlotDefault).not.toHaveBeenCalled()
  })
})
