import { describe, expect, test } from 'vitest'

import { ApiClientError, createApiClient } from './apiClient'

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'content-type': 'application/json' },
    status: init?.status ?? 200,
    statusText: init?.statusText,
  })
}

function createFetchStub(...responses: Response[]): {
  fetch: typeof fetch
  calls: Array<{ input: RequestInfo | URL; init?: RequestInit }>
} {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
  let index = 0

  return {
    calls,
    fetch: async (input, init) => {
      calls.push({ input, init })
      const response = responses[Math.min(index, responses.length - 1)]
      index += 1
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
  workspaceId = '11111111-1111-4111-8111-111111111111',
  sourceId = '22222222-2222-4222-8222-222222222222',
  status = 'queued',
}: {
  jobId?: string
  workspaceId?: string
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
    workspace_id: workspaceId,
    run_after: '2026-06-23T00:00:00Z',
    status,
    updated_at: '2026-06-23T00:00:00Z',
  }
}

describe('createApiClient', () => {
  test('uses cookie credentials and session CSRF after resolving a human user', async () => {
    const currentUser = {
      display_name: 'Viewer',
      email: 'viewer@example.com',
      id: '11111111-1111-4111-8111-111111111111',
      last_workspace_id: null,
      must_change_password: false,
      system_role: 'user',
    }
    const { fetch, calls } = createFetchStub(
      jsonResponse(currentUser),
      jsonResponse({ csrf_token: 'csrf-secret' }),
      jsonResponse(currentUser),
    )
    const client = createApiClient({ baseUrl: 'http://api.local', fetch })

    await client.getCurrentUser()
    await client.updateCurrentUserPreferences({ last_workspace_id: null })

    expect(calls.map((call) => String(call.input))).toEqual([
      'http://api.local/auth/me',
      'http://api.local/auth/csrf',
      'http://api.local/auth/me/preferences',
    ])
    expect(calls[0].init?.credentials).toBe('include')
    expect(calls[2].init?.credentials).toBe('include')
    expect(calls[2].init?.headers).toEqual({
      'content-type': 'application/json',
      'X-CSRF-Token': 'csrf-secret',
    })
  })

  test('logs in and changes a mandatory password through human auth routes', async () => {
    const user = {
      display_name: 'Viewer',
      email: 'viewer@example.com',
      id: '11111111-1111-4111-8111-111111111111',
      last_workspace_id: null,
      must_change_password: true,
      system_role: 'user',
    }
    const { fetch, calls } = createFetchStub(
      jsonResponse(user),
      jsonResponse({ csrf_token: 'csrf-secret' }),
      jsonResponse({ ...user, must_change_password: false }),
    )
    const client = createApiClient({ baseUrl: 'http://api.local', fetch })

    await client.login({
      email: 'viewer@example.com',
      password: 'temporary correct horse password',
    })
    await client.changePassword({
      new_password: 'permanent correct horse password',
    })

    expect(String(calls[0].input)).toBe('http://api.local/auth/login')
    expect(String(calls[1].input)).toBe('http://api.local/auth/csrf')
    expect(String(calls[2].input)).toBe('http://api.local/auth/change-password')
    expect(calls[2].init?.headers).toMatchObject({
      'X-CSRF-Token': 'csrf-secret',
    })
  })

  test('single-flights concurrent CSRF bootstrap requests', async () => {
    const currentUser = {
      display_name: 'Viewer',
      email: 'viewer@example.com',
      id: '11111111-1111-4111-8111-111111111111',
      last_workspace_id: null,
      must_change_password: false,
      system_role: 'user',
    }
    let csrfFetches = 0
    let csrfRelease: (() => void) | undefined
    const csrfGate = new Promise<void>((resolve) => {
      csrfRelease = resolve
    })
    const fetch: typeof globalThis.fetch = async (input, init) => {
      const url = String(input)
      if (url.endsWith('/auth/me') && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse(currentUser)
      }
      if (url.endsWith('/auth/csrf')) {
        csrfFetches += 1
        await csrfGate
        return jsonResponse({ csrf_token: 'csrf-shared' })
      }
      if (url.endsWith('/auth/me/preferences')) {
        const headers = new Headers(init?.headers)
        expect(headers.get('X-CSRF-Token')).toBe('csrf-shared')
        return jsonResponse(currentUser)
      }
      throw new Error(`unexpected url ${url}`)
    }
    const client = createApiClient({ baseUrl: 'http://api.local', fetch })

    await client.getCurrentUser()
    const pending = Promise.all([
      client.updateCurrentUserPreferences({ last_workspace_id: null }),
      client.updateCurrentUserPreferences({ last_workspace_id: null }),
    ])
    await Promise.resolve()
    expect(csrfFetches).toBe(1)
    csrfRelease?.()
    await pending
    expect(csrfFetches).toBe(1)
  })

  test('refreshes CSRF and retries once after csrf_failed', async () => {
    const currentUser = {
      display_name: 'Viewer',
      email: 'viewer@example.com',
      id: '11111111-1111-4111-8111-111111111111',
      last_workspace_id: null,
      must_change_password: false,
      system_role: 'user',
    }
    const tokensSeen: Array<string | null> = []
    let csrfFetches = 0
    let preferenceAttempts = 0
    const fetch: typeof globalThis.fetch = async (input, init) => {
      const url = String(input)
      if (url.endsWith('/auth/me') && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse(currentUser)
      }
      if (url.endsWith('/auth/csrf')) {
        csrfFetches += 1
        return jsonResponse({
          csrf_token: csrfFetches === 1 ? 'csrf-stale' : 'csrf-fresh',
        })
      }
      if (url.endsWith('/auth/me/preferences')) {
        preferenceAttempts += 1
        const headers = new Headers(init?.headers)
        const token = headers.get('X-CSRF-Token')
        tokensSeen.push(token)
        if (preferenceAttempts === 1) {
          return jsonResponse(
            { detail: { code: 'csrf_failed', message: 'CSRF validation failed' } },
            { status: 403 },
          )
        }
        return jsonResponse(currentUser)
      }
      throw new Error(`unexpected url ${url}`)
    }
    const client = createApiClient({ baseUrl: 'http://api.local', fetch })

    await client.getCurrentUser()
    const updated = await client.updateCurrentUserPreferences({
      last_workspace_id: null,
    })

    expect(updated.email).toBe('viewer@example.com')
    expect(csrfFetches).toBe(2)
    expect(tokensSeen).toEqual(['csrf-stale', 'csrf-fresh'])
  })

  test('uses the human user-management endpoints without exposing API keys', async () => {
    const user = {
      created_at: '2026-08-11T00:00:00Z',
      display_name: 'Workspace Viewer',
      email: 'viewer@example.com',
      id: '22222222-2222-4222-8222-222222222222',
      is_active: true,
      last_workspace_id: null,
      memberships: [
        {
          role: 'viewer',
          workspace_id: '11111111-1111-4111-8111-111111111111',
          workspace_name: 'Research',
        },
      ],
      must_change_password: true,
      system_role: 'user',
      updated_at: '2026-08-11T00:00:00Z',
    }
    const member = {
      created_at: user.created_at,
      display_name: user.display_name,
      email: user.email,
      id: '33333333-3333-4333-8333-333333333333',
      is_active: true,
      role: 'viewer',
      updated_at: user.updated_at,
      user_id: user.id,
      workspace_id: '11111111-1111-4111-8111-111111111111',
    }
    const { fetch, calls } = createFetchStub(
      jsonResponse({ items: [user] }),
      jsonResponse({ temporary_password: 'one-time-password', user }),
      jsonResponse(member),
      new Response(null, { status: 204 }),
    )
    const client = createApiClient({
      authToken: 'technical-test-token',
      baseUrl: 'http://api.local',
      fetch,
    })

    await client.listUsers()
    await client.createUser({
      display_name: user.display_name,
      email: user.email,
      initial_workspace_id: member.workspace_id,
      initial_workspace_role: 'viewer',
      system_role: 'user',
    })
    await client.addWorkspaceMember(member.workspace_id, {
      email: user.email,
      role: 'viewer',
    })
    await client.removeWorkspaceMember(member.workspace_id, user.id)

    expect(calls.map((call) => String(call.input))).toEqual([
      'http://api.local/admin/users',
      'http://api.local/admin/users',
      `http://api.local/workspaces/${member.workspace_id}/members`,
      `http://api.local/workspaces/${member.workspace_id}/members/${user.id}`,
    ])
    expect(calls[1].init?.body).not.toContain('access_token')
    expect(calls[2].init?.body).toBe(
      JSON.stringify({ email: user.email, role: 'viewer' }),
    )
  })

  test('lists background jobs with stable filters and mutates one job', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const { fetch, calls } = createFetchStub(
      jsonResponse({ items: [], next_cursor: null }),
      jsonResponse({ id: jobId }),
    )
    const client = createApiClient({ baseUrl: 'http://api.local', fetch })

    await client.listBackgroundJobs(workspaceId, {
      cursor: 'next',
      limit: 50,
      queue: 'ingestion',
      status: 'running',
    })
    await client.cancelBackgroundJob(workspaceId, jobId, { version: 3 })

    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/jobs?status=running&queue=ingestion&limit=50&cursor=next`,
    )
    expect(String(calls[1].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/jobs/${jobId}/cancel`,
    )
    expect(calls[1].init?.body).toBe(JSON.stringify({ version: 3 }))
  })

  test('attaches bearer auth headers to JSON requests', async () => {
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        display_name: 'Viewer',
        id: '11111111-1111-4111-8111-111111111111',
        must_change_password: false,
        last_workspace_id: null,
        email: 'viewer@example.com',
        system_role: 'user',
      }),
    )
    const client = createApiClient({
      authToken: 'viewer-token',
      baseUrl: 'http://api.local/',
      fetch,
    })

    await client.getCurrentUser()

    expect(String(calls[0].input)).toBe('http://api.local/auth/me')
    expect(calls[0].init?.headers).toEqual({
      Authorization: 'Bearer viewer-token',
    })
  })

  test('manages users, memberships and knowledge proposals', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const userId = '22222222-2222-4222-8222-222222222222'
    const proposalId = '33333333-3333-4333-8333-333333333333'
    const createdAt = '2026-06-28T00:00:00Z'
    const user = {
      created_at: createdAt,
      display_name: 'Viewer',
      id: userId,
      is_active: true,
      last_workspace_id: null,
      email: 'viewer@example.com',
      system_role: 'user',
      updated_at: createdAt,
    }
    const currentUser = {
      display_name: 'Viewer',
      id: userId,
      must_change_password: false,
      last_workspace_id: workspaceId,
      email: 'viewer@example.com',
      system_role: 'user',
    }
    const membership = {
      created_at: createdAt,
      id: '44444444-4444-4444-8444-444444444444',
      workspace_id: workspaceId,
      role: 'viewer',
      updated_at: createdAt,
      user_id: userId,
    }
    const proposal = {
      approved_source_id: null,
      created_at: createdAt,
      id: proposalId,
      origin_message_id: null,
      origin_session_id: null,
      workspace_id: workspaceId,
      proposed_text: 'New knowledge',
      refined_text: null,
      review_note: null,
      reviewed_at: null,
      reviewed_by_user_id: null,
      status: 'pending',
      submitted_by_user_id: userId,
      updated_at: createdAt,
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      const url = String(input)
      if (url.endsWith('/auth/me/preferences')) {
        return jsonResponse(currentUser)
      }
      if (url.endsWith('/admin/users')) {
        return jsonResponse(init?.method === 'GET' ? { items: [user] } : user)
      }
      if (url.includes('/memberships')) {
        return jsonResponse(
          init?.method === 'GET' ? { items: [membership] } : membership,
        )
      }
      return jsonResponse(
        init?.method === 'GET' ? { items: [proposal] } : proposal,
      )
    }
    const client = createApiClient({
      authToken: 'root-token',
      baseUrl: 'http://api.local',
      fetch: fetchStub,
    })

    await client.createUser({
      display_name: 'Viewer',
      email: 'viewer@example.com',
      initial_workspace_id: workspaceId,
      initial_workspace_role: 'viewer',
      system_role: 'user',
    })
    await client.listUsers()
    await client.updateCurrentUserPreferences({ last_workspace_id: workspaceId })
    await client.upsertWorkspaceMembership(workspaceId, userId, { role: 'viewer' })
    await client.listWorkspaceMemberships(workspaceId)
    await client.submitKnowledgeProposal(workspaceId, {
      proposed_text: 'New knowledge',
    })
    await client.listKnowledgeProposals(workspaceId, { status: 'pending' })
    await client.refineKnowledgeProposal(workspaceId, proposalId, {
      refined_text: 'Refined knowledge',
    })
    await client.approveKnowledgeProposal(workspaceId, proposalId, {
      review_note: 'accepted',
    })
    await client.rejectKnowledgeProposal(workspaceId, proposalId, {
      reason: 'not supported',
    })

    expect(String(calls[0].input)).toBe('http://api.local/admin/users')
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      Authorization: 'Bearer root-token',
      'content-type': 'application/json',
    })
    expect(String(calls[2].input)).toBe('http://api.local/auth/me/preferences')
    expect(calls[2].init?.method).toBe('PATCH')
    expect(calls[2].init?.body).toBe(
      JSON.stringify({ last_workspace_id: workspaceId }),
    )
    expect(String(calls[3].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/memberships/${userId}`,
    )
    expect(String(calls[5].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/knowledge-proposals`,
    )
    expect(String(calls[6].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/knowledge-proposals?status=pending`,
    )
    expect(String(calls[7].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/knowledge-proposals/${proposalId}/refine`,
    )
    expect(String(calls[8].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/knowledge-proposals/${proposalId}/approve`,
    )
    expect(String(calls[9].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/knowledge-proposals/${proposalId}/reject`,
    )
  })

  test('creates and lists workspaces through the authoring API', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const createdAt = '2026-06-22T00:00:00Z'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        budget_config_json: null,
        created_at: createdAt,
        embedding_mode: 'dense',
        id: workspaceId,
        name: 'Demo',
        retrieval_contextualization_enabled: true,
        updated_at: createdAt,
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.createWorkspace({ name: 'Demo' })

    expect(response.id).toBe(workspaceId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe('http://api.local/workspaces')
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      'content-type': 'application/json',
    })
    expect(calls[0].init?.body).toBe(JSON.stringify({ name: 'Demo' }))
  })

  test('deletes workspace, source, membership and revokes token', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const userId = '33333333-3333-4333-8333-333333333333'
    const createdAt = '2026-06-22T00:00:00Z'
    const workspace = {
      budget_config_json: null,
      created_at: createdAt,
      deleted_at: createdAt,
      embedding_mode: 'dense_sparse',
      id: workspaceId,
      name: 'Demo',
      retrieval_contextualization_enabled: true,
      updated_at: createdAt,
    }
    const source = {
      created_at: createdAt,
      deleted_at: createdAt,
      external_id: 'notes.md',
      extra_metadata: null,
      id: sourceId,
      workspace_id: workspaceId,
      source_type: 'markdown',
      tags: null,
      updated_at: createdAt,
    }
    const user = {
      created_at: createdAt,
      display_name: 'Temp',
      id: userId,
      is_active: false,
      last_workspace_id: null,
      email: 'temp',
      system_role: 'user',
      updated_at: createdAt,
    }

    const { fetch: deleteWorkspaceFetch, calls: deleteWorkspaceCalls } =
      createFetchStub(jsonResponse(workspace))
    const deleteWorkspaceClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: deleteWorkspaceFetch,
    })
    await deleteWorkspaceClient.deleteWorkspace(workspaceId)
    expect(String(deleteWorkspaceCalls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}`,
    )
    expect(deleteWorkspaceCalls[0].init?.method).toBe('DELETE')

    const { fetch: deleteSourceFetch, calls: deleteSourceCalls } =
      createFetchStub(jsonResponse(source))
    const deleteSourceClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: deleteSourceFetch,
    })
    await deleteSourceClient.deleteSource(workspaceId, sourceId)
    expect(String(deleteSourceCalls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/sources/${sourceId}`,
    )
    expect(deleteSourceCalls[0].init?.method).toBe('DELETE')

    const { fetch: membershipFetch, calls: membershipCalls } = createFetchStub(
      new Response(null, { status: 204 }),
    )
    const membershipClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: membershipFetch,
    })
    await membershipClient.deleteWorkspaceMembership(workspaceId, userId)
    expect(String(membershipCalls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/memberships/${userId}`,
    )
    expect(membershipCalls[0].init?.method).toBe('DELETE')

    const { fetch: deactivateFetch, calls: deactivateCalls } =
      createFetchStub(jsonResponse(user))
    const deactivateClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: deactivateFetch,
    })
    await deactivateClient.deactivateUser(userId)
    expect(String(deactivateCalls[0].input)).toBe(
      `http://api.local/admin/users/${userId}/deactivate`,
    )
    expect(deactivateCalls[0].init?.method).toBe('POST')

    const { fetch: revokeFetch, calls: revokeCalls } = createFetchStub(
      jsonResponse({ revoked: true }),
    )
    const revokeClient = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: revokeFetch,
    })
    await revokeClient.revokeAccessToken({ access_token: 'temp-token' })
    expect(String(revokeCalls[0].input)).toBe(
      'http://api.local/admin/access-tokens/revoke',
    )
    expect(revokeCalls[0].init?.method).toBe('POST')
    expect(revokeCalls[0].init?.body).toBe(
      JSON.stringify({ access_token: 'temp-token' }),
    )
  })

  test('lists workspaces and loads a workspace by id', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const createdAt = '2026-06-22T00:00:00Z'
    const workspace = {
      budget_config_json: null,
      created_at: createdAt,
      embedding_mode: 'dense',
      id: workspaceId,
      name: 'Demo',
      retrieval_contextualization_enabled: true,
      updated_at: createdAt,
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      return jsonResponse(String(input).endsWith('/workspaces') ? { items: [workspace] } : workspace)
    }
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch: fetchStub,
    })

    const listed = await client.listWorkspaces()
    const loaded = await client.getWorkspace(workspaceId)

    expect(listed.items).toHaveLength(1)
    expect(loaded.name).toBe('Demo')
    expect(String(calls[0].input)).toBe('http://api.local/workspaces')
    expect(String(calls[1].input)).toBe(
      `http://api.local/workspaces/${workspaceId}`,
    )
    expect(calls[0].init?.method).toBe('GET')
    expect(calls[1].init?.method).toBe('GET')
  })

  test('creates sources and lists sources with optional filters', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const createdAt = '2026-06-22T00:00:00Z'
    const source = {
      created_at: createdAt,
      external_id: 'notes.md',
      extra_metadata: { content: '# Notes' },
      id: sourceId,
      workspace_id: workspaceId,
      source_type: 'markdown',
      tags: ['docs'],
      updated_at: createdAt,
    }
    const { fetch, calls } = createFetchStub(jsonResponse(source))
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.createSource(workspaceId, {
      external_id: 'notes.md',
      extra_metadata: { content: '# Notes' },
      source_type: 'markdown',
      tags: ['docs'],
    })

    expect(response.id).toBe(sourceId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/sources`,
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

    await listClient.listSources(workspaceId, {
      external_id: 'notes.md',
      source_type: 'markdown',
      tag: 'docs',
    })

    expect(String(listFetch.calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/sources?source_type=markdown&external_id=notes.md&tag=docs`,
    )
  })

  test('loads a source by id', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        created_at: '2026-06-22T00:00:00Z',
        external_id: 'https://example.com/doc',
        extra_metadata: null,
        id: sourceId,
        workspace_id: workspaceId,
        source_type: 'url',
        tags: null,
        updated_at: '2026-06-22T00:00:00Z',
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.getSource(workspaceId, sourceId)

    expect(response.source_type).toBe('url')
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/sources/${sourceId}`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('enqueues ingestion jobs for sources', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const { fetch, calls } = createFetchStub(
      jsonResponse(jobPayload({ jobId, workspaceId, sourceId })),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.enqueueIngestionJob(workspaceId, sourceId, {
      max_attempts: 2,
      priority: 4,
    })

    expect(response.id).toBe(jobId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/sources/${sourceId}/ingestion-jobs`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.body).toBe(
      JSON.stringify({ max_attempts: 2, priority: 4 }),
    )
  })

  test('lists ingestion jobs with optional filters', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sourceId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        items: [jobPayload({ workspaceId, sourceId })],
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    await client.listIngestionJobs(workspaceId, {
      job_type: 'ingest_source',
      source_id: sourceId,
      status: 'blocked',
    })

    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/ingestion-jobs?source_id=${sourceId}&status=blocked&job_type=ingest_source`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('loads and retries ingestion job detail', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      return jsonResponse(
        String(input).endsWith('/retry')
          ? jobPayload({ jobId, workspaceId, status: 'queued' })
          : {
              events: [
                {
                  created_at: '2026-06-23T00:00:00Z',
                  event_type: 'blocked',
                  extra_metadata: null,
                  id: '44444444-4444-4444-8444-444444444444',
                  job_id: jobId,
                  message: 'missing content',
                  workspace_id: workspaceId,
                },
              ],
              job: jobPayload({ jobId, workspaceId, status: 'blocked' }),
            },
      )
    }
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch: fetchStub,
    })

    const detail = await client.getIngestionJob(workspaceId, jobId)
    const retried = await client.retryIngestionJob(workspaceId, jobId)

    expect(detail.events[0].event_type).toBe('blocked')
    expect(retried.status).toBe('queued')
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/ingestion-jobs/${jobId}`,
    )
    expect(String(calls[1].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/ingestion-jobs/${jobId}/retry`,
    )
    expect(calls[1].init?.method).toBe('POST')
  })

  test('runs the next ingestion job', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const jobId = '33333333-3333-4333-8333-333333333333'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        created_document_version: true,
        document_id: '55555555-5555-4555-8555-555555555555',
        document_version_id: '66666666-6666-4666-8666-666666666666',
        error_message: null,
        job_id: jobId,
        workspace_id: workspaceId,
        source_id: '22222222-2222-4222-8222-222222222222',
        status: 'processed',
        worker_id: 'frontend-test',
      }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })

    const response = await client.runNextIngestionJob(workspaceId, {
      lease_seconds: 60,
      worker_id: 'frontend-test',
    })

    expect(response.status).toBe('processed')
    expect(response.job_id).toBe(jobId)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/ingestion-jobs/run-next`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.body).toBe(
      JSON.stringify({ lease_seconds: 60, worker_id: 'frontend-test' }),
    )
  })

  test('posts chat requests with stable JSON payloads', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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

    const response = await client.askChat(workspaceId, {
      message: 'What changed?',
      retrieval_limit: 3,
      metadata_filter: {
        tags: ['release-notes'],
      },
    })

    expect(response.session_id).toBe(sessionId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat`,
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
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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

    const response = await client.listChatSessions(workspaceId, {
      archived: true,
      status: 'failed',
      limit: 10,
      cursor: '2026-06-21T00:00:00Z|abc',
    })

    expect(response.next_cursor).toBe('next-page')
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat/sessions?status=failed&archived=true&limit=10&cursor=2026-06-21T00%3A00%3A00Z%7Cabc`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('renames archives and unarchives chat sessions', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const sessionId = '22222222-2222-4222-8222-222222222222'
    const { fetch, calls } = createFetchStub(
      jsonResponse({
        session_id: sessionId,
        title: 'Renamed session',
        title_is_custom: true,
      }),
      new Response(null, { status: 204 }),
      new Response(null, { status: 204 }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    const renamed = await client.updateChatSessionTitle(
      workspaceId,
      sessionId,
      'Renamed session',
    )
    await client.archiveChatSession(workspaceId, sessionId)
    await client.unarchiveChatSession(workspaceId, sessionId)

    expect(renamed.title).toBe('Renamed session')
    expect(calls.map((call) => String(call.input))).toEqual([
      `http://api.local/workspaces/${workspaceId}/chat/sessions/${sessionId}/title`,
      `http://api.local/workspaces/${workspaceId}/chat/sessions/${sessionId}/archive`,
      `http://api.local/workspaces/${workspaceId}/chat/sessions/${sessionId}/unarchive`,
    ])
    expect(calls.map((call) => call.init?.method)).toEqual([
      'PATCH',
      'POST',
      'POST',
    ])
    expect(calls[0].init?.body).toBe(JSON.stringify({ title: 'Renamed session' }))
  })

  test('loads chat observability summaries with encoded optional query params', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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
        workspace_id: workspaceId,
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

    const response = await client.getChatObservabilitySummary(workspaceId, {
      created_at_from: '2026-06-21T00:00:00Z',
      created_at_to: '2026-06-22T00:00:00Z',
      status: 'failed',
    })

    expect(response.provider_usage.groups[0].latency_ms.p95).toBe(410)
    expect(response.errors.top_messages[0].message).toBe('runner failed')
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat/observability/summary?created_at_from=2026-06-21T00%3A00%3A00Z&created_at_to=2026-06-22T00%3A00%3A00Z&status=failed`,
    )
    expect(calls[0].init?.method).toBe('GET')
  })

  test('omits empty chat observability summary query params', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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
        workspace_id: workspaceId,
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

    await client.getChatObservabilitySummary(workspaceId, {
      created_at_from: '',
      created_at_to: null,
      status: '',
    })

    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat/observability/summary`,
    )
  })

  test('loads a session detail without mutating history', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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

    const response = await client.getChatSession(workspaceId, sessionId)

    expect(response.session.session_id).toBe(sessionId)
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat/sessions/${sessionId}`,
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
    const checkResponse = {
      connection_id: 'qwen-hosted',
      message: 'provider model list succeeded',
      model_count: 2,
      ok: true,
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    const fetchStub: typeof fetch = async (input, init) => {
      calls.push({ input, init })
      if (String(input).endsWith('/secrets/api_key')) {
        return jsonResponse(secretStatus)
      }
      if (String(input).endsWith('/connections/qwen-hosted/check')) {
        return jsonResponse(checkResponse)
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
    const checked = await client.checkProviderConnection('qwen-hosted')

    expect(listed.items[0].secrets[0].last_four).toBe('cret')
    expect(saved.provider).toBe('qwen')
    expect(secret.configured).toBe(true)
    expect(checked).toEqual(checkResponse)
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
    expect(String(calls[3].input)).toBe(
      'http://api.local/runtime-settings/connections/qwen-hosted/check',
    )
    expect(calls[3].init?.method).toBe('POST')
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
      api_key: 'sk-inline-secret',
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
    expect(calls[0].init?.body).toBe(
      JSON.stringify({
        api_key: 'sk-inline-secret',
        base_url: connection.base_url,
        capabilities: connection.capabilities,
        connection_type: connection.connection_type,
        metadata: connection.metadata,
        provider: connection.provider,
      }),
    )
    expect(String(calls[1].input)).toBe(
      'http://api.local/runtime-settings/connections/qwen-hosted-abc123/models/sync',
    )
    expect(calls[1].init?.method).toBe('POST')
    expect(String(calls[2].input)).toBe(
      'http://api.local/runtime-settings/models?connection_id=qwen-hosted-abc123&capability=chat',
    )
  })

  test('manages global and workspace runtime settings', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const slot = {
      connection_id: 'qwen-hosted',
      model_id: 'text-embedding-v4',
      parameters: null,
      slot: 'dense_embedding',
    }
    const chatRetrieval = {
      max_limit: 50,
      rerank_candidate_limit: 10,
      rerank_enabled: true,
      retrieval_limit: 5,
    }
    const workspaceSettings = {
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
        ...chatRetrieval,
        source: 'workspace',
      },
      workspace_id: workspaceId,
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
      if (
        value.includes('/workspaces/') &&
        value.endsWith('/runtime-settings/chat/retrieval')
      ) {
        return init?.method === 'DELETE'
          ? jsonResponse({ deleted: true })
          : jsonResponse({
              ...(JSON.parse(String(init?.body)) as object),
              max_limit: 50,
              source: 'workspace',
            })
      }
      if (value.endsWith('/runtime-settings/chat/retrieval')) {
        return jsonResponse(
          init?.method === 'PUT'
            ? {
                ...chatRetrieval,
                ...(JSON.parse(String(init.body)) as object),
              }
            : chatRetrieval,
        )
      }
      if (value.includes('/workspaces/')) {
        return init?.method === 'DELETE'
          ? jsonResponse({ deleted: true })
          : jsonResponse(workspaceSettings)
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
    const globalRetrieval = await client.getChatRetrievalSettings()
    await client.updateChatRetrievalSettings({
      retrieval_limit: 7,
      rerank_enabled: true,
      rerank_candidate_limit: 12,
    })
    const effective = await client.getWorkspaceRuntimeSettings(workspaceId)
    await client.upsertWorkspaceRuntimeSlotOverride(workspaceId, 'chat', {
      connection_id: 'local-chat',
      model_id: 'llama3.1:8b',
    })
    const deleted = await client.deleteWorkspaceRuntimeSlotOverride(
      workspaceId,
      'chat',
    )
    const workspaceRetrieval = await client.upsertWorkspaceChatRetrievalSettings(
      workspaceId,
      {
        retrieval_limit: 4,
        rerank_enabled: false,
        rerank_candidate_limit: 8,
      },
    )
    const deletedWorkspaceRetrieval =
      await client.deleteWorkspaceChatRetrievalSettings(workspaceId)

    expect(globalSlots.items[0].slot).toBe('dense_embedding')
    expect(globalRetrieval.rerank_candidate_limit).toBe(10)
    expect(effective.chat_models[0].source).toBe('overridden')
    expect(effective.chat_retrieval.source).toBe('workspace')
    expect(deleted.deleted).toBe(true)
    expect(workspaceRetrieval.source).toBe('workspace')
    expect(workspaceRetrieval.retrieval_limit).toBe(4)
    expect(deletedWorkspaceRetrieval.deleted).toBe(true)
    expect(String(calls[1].input)).toBe(
      'http://api.local/runtime-settings/slots/dense_embedding',
    )
    expect(calls[1].init?.method).toBe('PUT')
    expect(String(calls[2].input)).toBe(
      'http://api.local/runtime-settings/chat/models',
    )
    expect(calls[2].init?.method).toBe('POST')
    expect(String(calls[3].input)).toBe(
      'http://api.local/runtime-settings/chat/retrieval',
    )
    expect(calls[3].init?.method).toBe('GET')
    expect(String(calls[4].input)).toBe(
      'http://api.local/runtime-settings/chat/retrieval',
    )
    expect(calls[4].init?.method).toBe('PUT')
    expect(String(calls[5].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/runtime-settings`,
    )
    expect(String(calls[6].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/runtime-settings/slots/chat`,
    )
    expect(calls[6].init?.method).toBe('PUT')
    expect(calls[7].init?.method).toBe('DELETE')
    expect(String(calls[8].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/runtime-settings/chat/retrieval`,
    )
    expect(calls[8].init?.method).toBe('PUT')
    expect(calls[9].init?.method).toBe('DELETE')
  })

  test('raises structured errors for non-success responses', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
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
      client.getChatSession(workspaceId, 'missing-session'),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 404,
      detail: 'chat session not found',
      } satisfies Partial<ApiClientError>)
  })

  test('uses structured detail messages for API error text', async () => {
    const { fetch } = createFetchStub(
      jsonResponse(
        {
          detail: {
            code: 'provider_model_sync_failed',
            message: 'provider model list failed with status 401',
          },
        },
        { status: 422, statusText: 'Unprocessable Entity' },
      ),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(client.syncProviderModels('qwen-hosted')).rejects.toMatchObject({
      detail: {
        code: 'provider_model_sync_failed',
        message: 'provider model list failed with status 401',
      },
      message: 'provider model list failed with status 401',
      name: 'ApiClientError',
      status: 422,
    } satisfies Partial<ApiClientError>)
  })

  test('streams chat SSE events and resolves the final response', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const { fetch, calls } = createFetchStub(
      sseResponse([
        'event: session_started\ndata: {"session_id":"session-stream"}\n\n',
        'event: step\ndata: {"id":"answer","status":"start"}\n\n',
        'event: tool_call\ndata: {"name":"retrieval.search","query":"alpha"',
        ',"limit":3,"result_count":1}\n\n',
        'event: step\ndata: {"detail":{"result_count":1},"elapsed_ms":42,',
        '"id":"retrieval","status":"done"}\n\n',
        'event: answer_delta\ndata: {"text":"Partial answer"}\n\n',
        'event: final\ndata: {"answer":"Final answer","citations":[],"tool_calls":[],"session_id":"session-stream"}\n\n',
      ]),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local/',
      fetch,
    })
    const deltas: string[] = []
    const steps: string[] = []
    const toolCalls: string[] = []
    const sessions: string[] = []

    const response = await client.askChatStream(
      workspaceId,
      {
        message: 'What changed?',
        retrieval_limit: 3,
      },
      {
        onAnswerDelta: (text) => deltas.push(text),
        onSessionStarted: (sessionId) => sessions.push(sessionId),
        onToolCall: (toolCall) => toolCalls.push(toolCall.query ?? ''),
        onStep: (step) => {
          steps.push(`${step.id}:${step.status}:${step.elapsed_ms ?? 'running'}`)
        },
      },
    )

    expect(response).toEqual({
      answer: 'Final answer',
      citations: [],
      tool_calls: [],
      session_id: 'session-stream',
    })
    expect(deltas).toEqual(['Partial answer'])
    expect(steps).toEqual(['answer:start:running', 'retrieval:done:42'])
    expect(toolCalls).toEqual(['alpha'])
    expect(sessions).toEqual(['session-stream'])
    expect(calls).toHaveLength(1)
    expect(String(calls[0].input)).toBe(
      `http://api.local/workspaces/${workspaceId}/chat/stream`,
    )
    expect(calls[0].init?.method).toBe('POST')
    expect(calls[0].init?.headers).toEqual({
      accept: 'text/event-stream',
      'content-type': 'application/json',
    })
  })

  test('raises structured errors for chat stream error events', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const { fetch } = createFetchStub(
      sseResponse([
        'event: error\ndata: {"code":"provider_rate_limited","detail":"runner failed","message":"runner failed","retryable":true}\n\n',
      ]),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(
      client.askChatStream(workspaceId, { message: 'What changed?' }, {}),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 200,
      code: 'provider_rate_limited',
      retryable: true,
      message: 'runner failed',
      detail: {
        code: 'provider_rate_limited',
        detail: 'runner failed',
        message: 'runner failed',
        retryable: true,
      },
    } satisfies Partial<ApiClientError>)
  })

  test('accepts legacy stream error events with detail only', async () => {
    const workspaceId = '11111111-1111-4111-8111-111111111111'
    const { fetch } = createFetchStub(
      sseResponse(['event: error\ndata: {"detail":"legacy failure"}\n\n']),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(
      client.askChatStream(workspaceId, { message: 'What changed?' }, {}),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      message: 'legacy failure',
      code: null,
      retryable: false,
    } satisfies Partial<ApiClientError>)
  })

  test('lists and mutates user memories', async () => {
    const memory = {
      content: 'Prefer concise answers',
      created_at: '2026-08-05T00:00:00Z',
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      workspace_id: null,
      reviewed_at: null,
      reviewed_by_user_id: null,
      status: 'proposed',
      user_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    }
    const { fetch, calls } = createFetchStub(
      jsonResponse({ items: [memory] }),
      jsonResponse({ ...memory, content: 'Edited' }),
      jsonResponse({ ...memory, status: 'approved' }),
      jsonResponse({ ...memory, status: 'rejected' }),
    )
    const client = createApiClient({
      baseUrl: 'http://api.local',
      fetch,
    })

    await expect(client.listUserMemories({ status: 'proposed' })).resolves.toEqual({
      items: [memory],
    })
    expect(String(calls[0].input)).toBe(
      'http://api.local/users/me/memories?status=proposed',
    )

    await expect(
      client.updateUserMemory(memory.id, { content: 'Edited' }),
    ).resolves.toMatchObject({ content: 'Edited' })
    expect(calls[1].init?.method).toBe('PATCH')

    await expect(client.approveUserMemory(memory.id)).resolves.toMatchObject({
      status: 'approved',
    })
    expect(String(calls[2].input)).toContain('/approve')

    await expect(client.rejectUserMemory(memory.id)).resolves.toMatchObject({
      status: 'rejected',
    })
    expect(String(calls[3].input)).toContain('/reject')
  })
})
