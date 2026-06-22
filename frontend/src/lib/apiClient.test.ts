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

function sseResponse(chunks: string[], init?: ResponseInit): Response {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    }),
    {
      headers: { 'content-type': 'text/event-stream' },
      status: init?.status ?? 200,
      statusText: init?.statusText,
    },
  )
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

  test('loads chat observability summaries with encoded optional query params', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
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
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.getChatObservabilitySummary(projectId, {
      created_at_from: '2026-06-21T00:00:00Z',
      created_at_to: '2026-06-22T00:00:00Z',
      status: 'failed',
    })

    expect(response.provider_usage.groups[0].latency_ms.p95).toBe(410)
    expect(response.errors.top_messages[0].message).toBe('runner failed')
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat/observability/summary?created_at_from=2026-06-21T00%3A00%3A00Z&created_at_to=2026-06-22T00%3A00%3A00Z&status=failed`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('omits empty chat observability summary query params', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        errors: {
          provider_error_count: 0,
          session_error_count: 0,
          top_messages: [],
        },
        filters: {
          created_at_from: null,
          created_at_to: null,
          status: null,
        },
        project_id: projectId,
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
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    await client.getChatObservabilitySummary(projectId, {
      created_at_from: '',
      created_at_to: null,
      status: '',
    })

    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat/observability/summary`,
    )
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

  test('streams chat SSE events and resolves the final response', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch, calls } = createFetchStub(
      sseResponse([
        'event: session_started\ndata: {"session_id":"session-stream"}\n\n',
        'event: tool_call\ndata: {"name":"retrieval.search","query":"alpha"',
        ',"limit":3,"result_count":1}\n\n',
        'event: answer_delta\ndata: {"text":"Partial answer"}\n\n',
        'event: final\ndata: {"answer":"Final answer","citations":[],"tool_calls":[],"session_id":"session-stream"}\n\n',
      ]),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })
    const deltas: string[] = []
    const toolCalls: string[] = []
    const sessions: string[] = []

    const response = await client.askChatStream(
      projectId,
      {
        message: 'What changed?',
        retrieval_limit: 3,
      },
      {
        onAnswerDelta: (text) => deltas.push(text),
        onSessionStarted: (sessionId) => sessions.push(sessionId),
        onToolCall: (toolCall) => toolCalls.push(toolCall.query),
      },
    )

    expect(response).toEqual({
      answer: 'Final answer',
      citations: [],
      tool_calls: [],
      session_id: 'session-stream',
    })
    expect(deltas).toEqual(['Partial answer'])
    expect(toolCalls).toEqual(['alpha'])
    expect(sessions).toEqual(['session-stream'])
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/chat/stream`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      accept: 'text/event-stream',
      'content-type': 'application/json',
    })
  })

  test('raises structured errors for chat stream error events', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const { fetch } = createFetchStub(
      sseResponse(['event: error\ndata: {"detail":"runner failed"}\n\n']),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(
      client.askChatStream(projectId, { message: 'What changed?' }, {}),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 200,
      detail: 'runner failed',
    } satisfies Partial<ApiClientError>)
  })
})
