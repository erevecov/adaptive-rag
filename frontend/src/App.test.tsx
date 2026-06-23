/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import App from './App'
import type {
  ApiClient,
  ChatObservabilitySummary,
  ChatResponseBody,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
  IngestionJob,
  IngestionJobListResponse,
  IngestionRunResponse,
  Project,
  ProjectListResponse,
  Source,
  SourceListResponse,
} from './lib/apiClient'
import { ApiClientError } from './lib/apiClient'

const projectId = '11111111-1111-4111-8111-111111111111'

afterEach(() => {
  cleanup()
})

function createClientStub(options: {
  askChat?: ApiClient['askChat']
  askChatStream?: ApiClient['askChatStream']
  createProject?: ApiClient['createProject']
  createSource?: ApiClient['createSource']
  enqueueIngestionJob?: ApiClient['enqueueIngestionJob']
  getChatObservabilitySummary?: ApiClient['getChatObservabilitySummary']
  getChatSession?: ApiClient['getChatSession']
  getIngestionJob?: ApiClient['getIngestionJob']
  getProject?: ApiClient['getProject']
  getSource?: ApiClient['getSource']
  listChatSessions?: ApiClient['listChatSessions']
  listIngestionJobs?: ApiClient['listIngestionJobs']
  listProjects?: ApiClient['listProjects']
  listSources?: ApiClient['listSources']
  retryIngestionJob?: ApiClient['retryIngestionJob']
  runNextIngestionJob?: ApiClient['runNextIngestionJob']
}): ApiClient {
  return {
    askChat: options.askChat ?? vi.fn(),
    askChatStream: options.askChatStream ?? vi.fn(),
    createProject: options.createProject ?? vi.fn(),
    createSource: options.createSource ?? vi.fn(),
    enqueueIngestionJob: options.enqueueIngestionJob ?? vi.fn(),
    getChatObservabilitySummary:
      options.getChatObservabilitySummary ?? vi.fn(),
    getChatSession: options.getChatSession ?? vi.fn(async () => emptySessionDetail),
    getIngestionJob: options.getIngestionJob ?? vi.fn(),
    getProject: options.getProject ?? vi.fn(),
    getSource: options.getSource ?? vi.fn(),
    listChatSessions: options.listChatSessions ?? vi.fn(),
    listIngestionJobs: options.listIngestionJobs ?? vi.fn(),
    listProjects: options.listProjects ?? vi.fn(),
    listSources: options.listSources ?? vi.fn(),
    retryIngestionJob: options.retryIngestionJob ?? vi.fn(),
    runNextIngestionJob: options.runNextIngestionJob ?? vi.fn(),
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
      created_at: '2026-06-21T00:00:00Z',
      error_message: null,
      message_count: 2,
      model_config: null,
      prompt_version: 'default',
      provider_usage_count: 1,
      retrieval_run_count: 1,
      session_id: 'session-123',
      status: 'succeeded',
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

const emptySessionDetail: ChatSessionDetailResponse = {
  messages: [],
  provider_usage: [],
  retrieval_runs: [],
  session: {
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    model_config: null,
    prompt_version: null,
    session_id: 'session-123',
    status: 'succeeded',
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
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    model_config: { chat_provider: 'qwen' },
    prompt_version: 'default',
    session_id: 'session-123',
    status: 'succeeded',
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

describe('App chat workspace', () => {
  test('renders with the local API fallback when no API base URL is configured', () => {
    render(<App />)

    expect(screen.getByLabelText('Project ID')).toBeTruthy()
    expect(screen.getByLabelText('Question')).toBeTruthy()
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

    await user.click(screen.getByRole('button', { name: 'Authoring' }))
    await user.click(screen.getByRole('button', { name: 'Refresh projects' }))
    expect(await screen.findByText('Demo')).toBeTruthy()

    await user.type(screen.getByLabelText('Project name'), 'Demo')
    await user.click(screen.getByRole('button', { name: 'Create project' }))

    expect(client.createProject).toHaveBeenCalledWith({ name: 'Demo' })
    expect(await screen.findByText(projectId)).toBeTruthy()

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
    expect((screen.getByLabelText('Project ID') as HTMLInputElement).value).toBe(
      projectId,
    )
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

    await user.click(screen.getByRole('button', { name: 'Authoring' }))
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
        retrieval_limit: 5,
      },
      expect.any(Object),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(client.askChat).not.toHaveBeenCalled()
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      limit: 5,
    })
    expect(
      screen.getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText('rag_search')).toBeTruthy()
    expect(screen.getAllByText('session-123')).toHaveLength(2)
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
      retrieval_limit: 5,
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
    expect(await screen.findByText('Canceled')).toBeTruthy()
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
    expect(client.listChatSessions).not.toHaveBeenCalled()
  })

  test('refreshes history and renders selected session detail read-only', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatSession: vi.fn(async () => sessionDetailResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Refresh history' }))
    await user.click(await screen.findByRole('button', { name: 'session-123' }))

    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      limit: 5,
    })
    expect(client.getChatSession).toHaveBeenCalledWith(projectId, 'session-123')
    expect(screen.getByText('The import failed because the worker was not running.')).toBeTruthy()
    expect(screen.getByText('rag_search')).toBeTruthy()
    expect(screen.getByText('deployment import failure')).toBeTruthy()
    expect(
      screen.getByText('Confirm the worker is running before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText('qwen / qwen-plus')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Replay' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
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

    await user.click(screen.getByRole('button', { name: 'Refresh history' }))
    await user.click(await screen.findByRole('button', { name: 'session-123' }))

    expect((await screen.findByRole('status')).textContent).toContain(
      'chat session not found',
    )
    expect(screen.getByRole('button', { name: 'session-123' })).toBeTruthy()
  })

  test('refreshes observability with filters and renders metric cards', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      getChatObservabilitySummary: vi.fn(async () => observabilitySummary),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.click(screen.getByRole('button', { name: 'Observability' }))
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

    await user.click(screen.getByRole('button', { name: 'Observability' }))
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

    await user.click(screen.getByRole('button', { name: 'Observability' }))
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

    await user.click(screen.getByRole('button', { name: 'Observability' }))
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

    await user.click(screen.getByRole('button', { name: 'Observability' }))
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
})
