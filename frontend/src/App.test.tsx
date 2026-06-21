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
  listChatSessions?: ApiClient['listChatSessions']
}): ApiClient {
  return {
    askChat: options.askChat ?? vi.fn(),
    getChatSession: vi.fn(async () => emptySessionDetail),
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

describe('App chat workspace', () => {
  test('renders with the local API fallback when no API base URL is configured', () => {
    render(<App />)

    expect(screen.getByLabelText('Project ID')).toBeTruthy()
    expect(screen.getByLabelText('Question')).toBeTruthy()
  })

  test('submits a chat question and renders response details', async () => {
    const user = userEvent.setup()
    const client = createClientStub({
      askChat: vi.fn(async () => chatResponse),
      listChatSessions: vi.fn(async () => sessionListResponse),
    })

    render(<App apiClient={client} initialProjectId={projectId} />)

    await user.type(screen.getByLabelText('Question'), 'How do I retry?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(chatResponse.answer)).toBeTruthy()
    expect(client.askChat).toHaveBeenCalledWith(projectId, {
      message: 'How do I retry?',
      retrieval_limit: 5,
    })
    expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
      limit: 5,
    })
    expect(
      screen.getByText('Restart the worker before retrying the import.'),
    ).toBeTruthy()
    expect(screen.getByText('rag_search')).toBeTruthy()
    expect(screen.getAllByText('session-123')).toHaveLength(2)
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
})
