/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import App from './App'
import type {
  ApiClient,
  ChatResponseBody,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
} from './lib/apiClient'
import { ApiClientError } from './lib/apiClient'

const projectId = '11111111-1111-4111-8111-111111111111'

afterEach(() => {
  cleanup()
})

function createClientStub(options: {
  askChat?: ApiClient['askChat']
  askChatStream?: ApiClient['askChatStream']
  getChatSession?: ApiClient['getChatSession']
  listChatSessions?: ApiClient['listChatSessions']
}): ApiClient {
  return {
    askChat: options.askChat ?? vi.fn(),
    askChatStream: options.askChatStream ?? vi.fn(),
    getChatSession: options.getChatSession ?? vi.fn(async () => emptySessionDetail),
    listChatSessions: options.listChatSessions ?? vi.fn(),
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
})
