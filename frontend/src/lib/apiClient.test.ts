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

function jobPayload({
  jobId = '33333333-3333-4333-8333-333333333333',
  projectId = '11111111-1111-4111-8111-111111111111',
  sourceId = '22222222-2222-4222-8222-222222222222',
  status = 'queued',
}: {
  jobId?: string
  projectId?: string
  sourceId?: string
  status?: string
}) {
  return {
    attempts: 0,
    created_at: '2026-06-23T00:00:00Z',
    id: jobId,
    job_type: 'ingest_source',
    last_error: status === 'blocked' ? 'missing content' : null,
    locked_by: null,
    locked_until: null,
    max_attempts: 3,
    payload_json: { source_id: sourceId },
    priority: 0,
    project_id: projectId,
    run_after: '2026-06-23T00:00:00Z',
    status,
    updated_at: '2026-06-23T00:00:00Z',
  }
}

describe('createApiClient', () => {
  test('creates and lists projects through the authoring API', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const createdAt = '2026-06-22T00:00:00Z'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        budget_config_json: null,
        created_at: createdAt,
        embedding_mode: 'dense',
        id: projectId,
        name: 'Demo',
        retrieval_contextualization_enabled: true,
        updated_at: createdAt,
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.createProject({ name: 'Demo' })

    expect(response.id).toBe(projectId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe('http://api.local/projects')
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      'content-type': 'application/json',
    })
    expect(calls[0].init?.body).toBe(JSON.stringify({ name: 'Demo' }))
  })

  test('lists projects and loads a project by id', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const createdAt = '2026-06-22T00:00:00Z'
    const project = {
      budget_config_json: null,
      created_at: createdAt,
      embedding_mode: 'dense',
      id: projectId,
      name: 'Demo',
      retrieval_contextualization_enabled: true,
      updated_at: createdAt,
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      return jsonResponse(String(input).endsWith('/projects') ? { items: [project] } : project)
    }
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch: fetchStub,
    })

    const listed = await client.listProjects()
    const loaded = await client.getProject(projectId)

    expect(listed.items).toHaveLength(1)
    expect(loaded.name).toBe('Demo')
    expect(String(calls[0].input)).toBe('http://api.local/projects')
    expect(String(calls[1].input)).toBe(
      `http://api.local/projects/${projectId}`,
    )
    expect(calls[0].init?.method).toBe('GET')
    expect(calls[1].init?.method).toBe('GET')
  })

  test('creates sources and lists sources with optional filters', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const createdAt = '2026-06-22T00:00:00Z'
    const source = {
      created_at: createdAt,
      external_id: 'notes.md',
      extra_metadata: { content: '# Notes' },
      id: sourceId,
      project_id: projectId,
      source_type: 'markdown',
      tags: ['docs'],
      updated_at: createdAt,
    }
    const { fetch, calls } = createFetchStub(jsonResponse(source))
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.createSource(projectId, {
      external_id: 'notes.md',
      extra_metadata: { content: '# Notes' },
      source_type: 'markdown',
      tags: ['docs'],
    })

    expect(response.id).toBe(sourceId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/sources`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.body).toBe(
      JSON.stringify({
        external_id: 'notes.md',
        extra_metadata: { content: '# Notes' },
        source_type: 'markdown',
        tags: ['docs'],
      }),
    )

    const listFetch = createFetchStub(jsonResponse({ items: [source] }))
    const listClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: listFetch.fetch,
    })

    await listClient.listSources(projectId, {
      external_id: 'notes.md',
      source_type: 'markdown',
      tag: 'docs',
    })

    expect(String(listFetch.calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/sources?source_type=markdown&external_id=notes.md&tag=docs`,
    )
  })

  test('loads a source by id', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        created_at: '2026-06-22T00:00:00Z',
        external_id: 'https://example.com/doc',
        extra_metadata: null,
        id: sourceId,
        project_id: projectId,
        source_type: 'url',
        tags: null,
        updated_at: '2026-06-22T00:00:00Z',
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.getSource(projectId, sourceId)

    expect(response.source_type).toBe('url')
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/sources/${sourceId}`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('enqueues ingestion jobs for sources', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const { fetch, calls } = createFetchStub(
      jsonResponse(jobPayload({ jobId, projectId, sourceId })),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.enqueueIngestionJob(projectId, sourceId, {
      max_attempts: 2,
      priority: 4,
    })

    expect(response.id).toBe(jobId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/sources/${sourceId}/ingestion-jobs`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.body).toBe(
      JSON.stringify({ max_attempts: 2, priority: 4 }),
    )
  })

  test('lists ingestion jobs with optional filters', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        items: [jobPayload({ projectId, sourceId })],
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    await client.listIngestionJobs(projectId, {
      job_type: 'ingest_source',
      source_id: sourceId,
      status: 'blocked',
    })

    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/ingestion-jobs?source_id=${sourceId}&status=blocked&job_type=ingest_source`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('loads and retries ingestion job detail', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      return jsonResponse(
        String(input).endsWith('/retry')
          ? jobPayload({ jobId, projectId, status: 'queued' })
          : {
              events: [
                {
                  created_at: '2026-06-23T00:00:00Z',
                  event_type: 'blocked',
                  extra_metadata: null,
                  id: '44444444-4444-4444-8444-444444444444',
                  job_id: jobId,
                  message: 'missing content',
                  project_id: projectId,
                },
              ],
              job: jobPayload({ jobId, projectId, status: 'blocked' }),
            },
      )
    }
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: fetchStub,
    })

    const detail = await client.getIngestionJob(projectId, jobId)
    const retried = await client.retryIngestionJob(projectId, jobId)

    expect(detail.events[0].event_type).toBe('blocked')
    expect(retried.status).toBe('queued')
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/ingestion-jobs/${jobId}`,
    )
    expect(String(calls[1].input)).toBe(
      `http://api.local/projects/${projectId}/ingestion-jobs/${jobId}/retry`,
    )
    expect(calls[1].init?.method).toBe('POST')
  })

  test('runs the next ingestion job', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        created_document_version: true,
        document_id: '55555555-5555-4555-8555-555555555555',
        document_version_id: '66666666-6666-4666-8666-666666666666',
        error_message: null,
        job_id: jobId,
        project_id: projectId,
        source_id: '22222222-2222-4222-8222-222222222222',
        status: 'processed',
        worker_id: 'frontend-test',
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.runNextIngestionJob(projectId, {
      lease_seconds: 60,
      worker_id: 'frontend-test',
    })

    expect(response.status).toBe('processed')
    expect(response.job_id).toBe(jobId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/projects/${projectId}/ingestion-jobs/run-next`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.body).toBe(
      JSON.stringify({ lease_seconds: 60, worker_id: 'frontend-test' }),
    )
  })

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

  test('manages runtime provider connections and secrets without readback', async () => {
    const connection = {
      base_url: 'https://dashscope.example.test/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding'],
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
    }
    const secretStatus = connection.secrets[0]
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      if (String(input).endsWith('/secrets/api_key')) {
        return jsonResponse(secretStatus)
      }
      return jsonResponse(
        init?.method === 'GET' ? { items: [connection] } : connection,
      )
    }
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: fetchStub,
    })

    const listed = await client.listProviderConnections()
    const saved = await client.upsertProviderConnection('qwen-hosted', {
      base_url: connection.base_url,
      capabilities: ['chat', 'dense_embedding'],
      connection_type: 'hosted',
      metadata: { label: 'Hosted Qwen' },
      provider: 'qwen',
    })
    const secret = await client.upsertProviderSecret(
      'qwen-hosted',
      'api_key',
      { value: 'sk-hosted-secret' },
    )

    expect(listed.items[0].secrets[0].last_four).toBe('cret')
    expect(saved.provider).toBe('qwen')
    expect(secret.configured).toBe(true)
    expect(String(calls[0].input)).toBe('http://api.local/runtime-settings/connections')
    expect(String(calls[1].input)).toBe(
      'http://api.local/runtime-settings/connections/qwen-hosted',
    )
    expect(calls[1].init?.method).toBe('PUT')
    expect(calls[1].init?.body).toBe(
      JSON.stringify({
        base_url: connection.base_url,
        capabilities: ['chat', 'dense_embedding'],
        connection_type: 'hosted',
        metadata: { label: 'Hosted Qwen' },
        provider: 'qwen',
      }),
    )
    expect(String(calls[2].input)).toBe(
      'http://api.local/runtime-settings/connections/qwen-hosted/secrets/api_key',
    )
    expect(calls[2].init?.method).toBe('PUT')
    expect(calls[2].init?.body).toBe(JSON.stringify({ value: 'sk-hosted-secret' }))
  })

  test('creates provider connections and syncs provider model catalog', async () => {
    const connection = {
      base_url: 'https://dashscope.example.test/compatible-mode/v1',
      capabilities: ['chat', 'dense_embedding'],
      connection_id: 'qwen-hosted-abc123',
      connection_type: 'hosted',
      created_at: '2026-06-24T00:00:00Z',
      metadata: { label: 'Hosted Qwen' },
      provider: 'qwen',
      secrets: [],
      updated_at: '2026-06-24T00:00:00Z',
    }
    const model = {
      capabilities: ['chat'],
      connection_id: connection.connection_id,
      created_at: '2026-06-24T00:00:00Z',
      last_seen_at: '2026-06-24T00:00:00Z',
      metadata: { object: 'model' },
      model_id: 'qwen-plus',
      pricing: null,
      updated_at: '2026-06-24T00:00:00Z',
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      const url = String(input)
      if (url.endsWith('/models/sync')) {
        return jsonResponse({
          connection_id: connection.connection_id,
          items: [model],
          synced_count: 1,
        })
      }
      if (url.includes('/runtime-settings/models')) {
        return jsonResponse({ items: [model] })
      }
      return jsonResponse(connection)
    }
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: fetchStub,
    })

    const created = await client.createProviderConnection({
      base_url: connection.base_url,
      capabilities: connection.capabilities,
      connection_type: connection.connection_type,
      metadata: connection.metadata,
      provider: connection.provider,
    })
    const synced = await client.syncProviderModels(connection.connection_id)
    const listed = await client.listProviderModels({
      capability: 'chat',
      connection_id: connection.connection_id,
    })

    expect(created.connection_id).toBe('qwen-hosted-abc123')
    expect(synced.synced_count).toBe(1)
    expect(listed.items[0].model_id).toBe('qwen-plus')
    expect(String(calls[0].input)).toBe(
      'http://api.local/runtime-settings/connections',
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(String(calls[1].input)).toBe(
      'http://api.local/runtime-settings/connections/qwen-hosted-abc123/models/sync',
    )
    expect(calls[1].init?.method).toBe('POST')
    expect(String(calls[2].input)).toBe(
      'http://api.local/runtime-settings/models?connection_id=qwen-hosted-abc123&capability=chat',
    )
  })

  test('manages global and project runtime settings', async () => {
    const projectId = '11111111-1111-4111-8111-111111111111'
    const slot = {
      connection_id: 'qwen-hosted',
      model_id: 'text-embedding-v4',
      parameters: null,
      slot: 'dense_embedding',
    }
    const projectSettings = {
      chat_models: [
        {
          connection_id: 'local-chat',
          is_default: true,
          model_id: 'llama3.1:8b',
          parameters: null,
          source: 'overridden',
        },
      ],
      project_id: projectId,
      slots: [
        {
          ...slot,
          source: 'inherited',
        },
      ],
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      const value = String(input)
      if (value.endsWith('/chat/models')) {
        return jsonResponse({
          connection_id: 'local-chat',
          created_at: '2026-06-24T00:00:00Z',
          is_default: true,
          model_id: 'llama3.1:8b',
          parameters: null,
          updated_at: '2026-06-24T00:00:00Z',
        })
      }
      if (value.includes('/projects/')) {
        return init?.method === 'DELETE'
          ? jsonResponse({ deleted: true })
          : jsonResponse(projectSettings)
      }
      return init?.method === 'GET'
        ? jsonResponse({ items: [slot] })
        : jsonResponse({
            ...slot,
            created_at: '2026-06-24T00:00:00Z',
            updated_at: '2026-06-24T00:00:00Z',
          })
    }
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch: fetchStub,
    })

    const globalSlots = await client.listRuntimeSlotDefaults()
    await client.upsertRuntimeSlotDefault('dense_embedding', {
      connection_id: 'qwen-hosted',
      model_id: 'text-embedding-v4',
    })
    await client.upsertChatModel({
      connection_id: 'local-chat',
      make_default: true,
      model_id: 'llama3.1:8b',
    })
    const effective = await client.getProjectRuntimeSettings(projectId)
    await client.upsertProjectRuntimeSlotOverride(projectId, 'chat', {
      connection_id: 'local-chat',
      model_id: 'llama3.1:8b',
    })
    const deleted = await client.deleteProjectRuntimeSlotOverride(
      projectId,
      'chat',
    )

    expect(globalSlots.items[0].slot).toBe('dense_embedding')
    expect(effective.chat_models[0].source).toBe('overridden')
    expect(deleted.deleted).toBe(true)
    expect(String(calls[1].input)).toBe(
      'http://api.local/runtime-settings/slots/dense_embedding',
    )
    expect(calls[1].init?.method).toBe('PUT')
    expect(String(calls[2].input)).toBe(
      'http://api.local/runtime-settings/chat/models',
    )
    expect(calls[2].init?.method).toBe('POST')
    expect(String(calls[3].input)).toBe(
      `http://api.local/projects/${projectId}/runtime-settings`,
    )
    expect(String(calls[4].input)).toBe(
      `http://api.local/projects/${projectId}/runtime-settings/slots/chat`,
    )
    expect(calls[4].init?.method).toBe('PUT')
    expect(calls[5].init?.method).toBe('DELETE')
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
