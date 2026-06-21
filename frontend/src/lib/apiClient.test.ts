import { describe, expect, test } from 'vitest'

import { ApiClientError, createApiClient } from './apiClient'

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'content-type': 'application/json' },
    status: init?.status ?? 200,
    statusText: init?.statusText,
  })
}

function createFetchStub(response: Response): {
  fetch: typeof fetch
  calls: Array<{ input: RequestInfo | URL; init?: RequestInit }>
} {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []

  return {
    calls,
    fetch: async (input, init) => {
      calls.push({ input, init })
      return response
    },
  }
}

describe('createApiClient', () => {
  test('posts chat requests with stable JSON payloads', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sessionId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        answer: 'Use the cited source.',
        citations: [],
        tool_calls: [],
        session_id: sessionId,
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.askChat(projectId, {
      message: 'What changed?',
      retrieval_limit: 3,
      metadata_filter: {
        tags: ['release-notes'],
      },
    })

    expect(response.session_id).toBe(sessionId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      'content-type': 'application/json',
    })
    expect(calls[0].init?.body).toBe(
      JSON.stringify({
        message: 'What changed?',
        retrieval_limit: 3,
        metadata_filter: {
          tags: ['release-notes'],
        },
      }),
    )
  })

  test('lists sessions with encoded optional query params', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        items: [],
        next_cursor: 'next-page',
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    const response = await client.listChatSessions(projectId, {
      status: 'failed',
      limit: 10,
      cursor: '2026-06-21T00:00:00Z|abc',
    })

    expect(response.next_cursor).toBe('next-page')
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat/sessions?status=failed&limit=10&cursor=2026-06-21T00%3A00%3A00Z%7Cabc`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('loads a session detail without mutating history', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sessionId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        session: {
          session_id: sessionId,
          status: 'succeeded',
          created_at: '2026-06-21T00:00:00Z',
          updated_at: '2026-06-21T00:00:01Z',
          model_config: null,
          prompt_version: null,
          error_message: null,
        },
        messages: [],
        tool_calls: [],
        retrieval_runs: [],
        provider_usage: [],
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.getChatSession(projectId, sessionId)

    expect(response.session.session_id).toBe(sessionId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat/sessions/${sessionId}`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('raises structured errors for non-success responses', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch } = createFetchStub(
      jsonResponse(
        {
          detail: 'chat session not found',
        },
        { status: 404, statusText: 'Not Found' },
      ),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(
      client.getChatSession(projectId, 'missing-session'),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 404,
      detail: 'chat session not found',
    } satisfies Partial<ApiClientError>)
  })
})
