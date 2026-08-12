/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type {
  ChatSessionDetailResponse,
  ChatSessionSummary,
  Source,
} from '@/lib/apiClient'
import {
  filterSessionDetailToTurn,
  SessionNavigationPanel,
  WorkspaceInspectorPanel,
} from './HistoryInspectorView'
import historySource from './HistoryInspectorView.tsx?raw'

afterEach(() => {
  cleanup()
})

const sessions: ChatSessionSummary[] = [
  {
    archived_at: null,
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    has_approved_training: true,
    has_pending_training: false,
    message_count: 2,
    model_config: null,
    prompt_version: 'v1',
    provider_usage_count: 1,
    retrieval_run_count: 1,
    session_id: 'session-1',
    status: 'succeeded',
    title: 'Architecture review',
    title_is_custom: true,
    tool_call_count: 1,
    total_estimated_cost_usd: 0.04,
    updated_at: '2026-06-21T00:01:00Z',
  },
]

const searchableSessions: ChatSessionSummary[] = Array.from(
  { length: 5 },
  (_, index) => ({
    ...sessions[0],
    session_id: `session-${index + 1}`,
    title: index === 0 ? 'Architecture review' : `Session ${index + 1}`,
  }),
)

const source: Source = {
  created_at: '2026-06-20T00:00:00Z',
  external_id: 'architecture.md',
  extra_metadata: { owner: 'docs' },
  id: 'source-1',
  workspace_id: 'workspace-1',
  source_type: 'markdown',
  tags: ['architecture'],
  updated_at: '2026-06-21T00:00:00Z',
}

const detail: ChatSessionDetailResponse = {
  messages: [
    {
      content: 'What changed?',
      created_at: '2026-06-21T00:00:00Z',
      message_id: 'message-user',
      metadata: null,
      role: 'user',
    },
    {
      content: 'The retrieval flow changed.',
      created_at: '2026-06-21T00:00:01Z',
      message_id: 'message-assistant',
      metadata: null,
      role: 'assistant',
    },
  ],
  provider_usage: [
    {
      created_at: '2026-06-21T00:00:02Z',
      currency: 'USD',
      error_message: null,
      estimated_cost_usd: 0.0123,
      input_count: null,
      input_tokens: 100,
      latency_ms: 250,
      model: 'qwen-plus',
      operation: 'chat',
      output_tokens: 40,
      provider: 'qwen',
      provider_request_id: 'request-1',
      provider_usage_id: 'usage-1',
      status: 'succeeded',
      total_tokens: 140,
      usage_source: 'provider_reported',
    },
  ],
  retrieval_runs: [
    {
      created_at: '2026-06-21T00:00:01Z',
      error_message: null,
      filters: null,
      latency_ms: 120,
      query: 'retrieval flow',
      retrieval_run_id: 'retrieval-1',
      retrieved_chunks: [
        {
          chunk_id: 'chunk-1',
          citation: {
            snippet: 'The retrieval flow changed.',
            source_external_id: 'architecture.md',
            source_id: 'source-1',
          },
          created_at: '2026-06-21T00:00:01Z',
          dense_score: 0.7,
          lexical_score: null,
          rank: 1,
          rerank_score: 0.9,
          retrieved_chunk_id: 'retrieved-1',
          rrf_score: null,
        },
      ],
      strategy: 'dense',
      tool_call_id: 'tool-1',
      top_k: 3,
      used_rerank: true,
    },
  ],
  session: {
    archived_at: null,
    created_at: '2026-06-21T00:00:00Z',
    error_message: null,
    model_config: null,
    prompt_version: 'v1',
    session_id: 'session-1',
    status: 'succeeded',
    title: 'Architecture review',
    title_is_custom: true,
    updated_at: '2026-06-21T00:01:00Z',
  },
  tool_calls: [
    {
      arguments: { query: 'retrieval flow' },
      created_at: '2026-06-21T00:00:01Z',
      error_message: null,
      latency_ms: 80,
      result_summary: { result_count: 1 },
      status: 'succeeded',
      tool_call_id: 'tool-1',
      tool_name: 'retrieve',
      updated_at: '2026-06-21T00:00:02Z',
    },
  ],
}

function expectNoLegacyHistoryClasses(container: HTMLElement) {
  expect(container.querySelector('.session-list')).toBeNull()
  expect(container.querySelector('.session-row')).toBeNull()
  expect(container.querySelector('.session-filter')).toBeNull()
  expect(container.querySelector('.workspace-inspector')).toBeNull()
  expect(container.querySelector('.detail-panel')).toBeNull()
  expect(container.querySelector('.minimap-list')).toBeNull()
  expect(container.querySelector('.source-viewer')).toBeNull()
}

describe('SessionNavigationPanel', () => {
  test('offers CommandSearch only for session lists with at least five items', async () => {
    const user = userEvent.setup()
    const onSelectSession = vi.fn()
    const { rerender } = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={onSelectSession}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={searchableSessions}
        state="succeeded"
        statusFilter="active"
      />,
    )

    const searchbox = screen.getByRole('searchbox', {
      name: 'Search sessions',
    })
    const search = searchbox.closest('[data-slot="command-search"]')
    expect(search).toBeTruthy()
    expect(within(search as HTMLElement).queryByRole('list')).toBeNull()
    expect(
      within(screen.getByRole('list', { name: 'Workspace Sessions' })).getByRole(
        'button',
        { name: /Open session Architecture review/ },
      ),
    ).toBeTruthy()
    await user.type(searchbox, 'Architecture')
    await user.click(
      within(search as HTMLElement).getByRole('button', {
        name: /^Architecture review/,
      }),
    )
    expect(onSelectSession).toHaveBeenCalledWith('session-1')

    rerender(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={onSelectSession}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={searchableSessions.slice(0, 4)}
        state="succeeded"
        statusFilter="active"
      />,
    )

    expect(
      screen.queryByRole('searchbox', { name: 'Search sessions' }),
    ).toBeNull()
  })

  test('renders session filters and rows with tokenized primitives', async () => {
    const user = userEvent.setup()
    const onStatusFilterChange = vi.fn()
    const onSelectSession = vi.fn()
    const { container } = render(
      <SessionNavigationPanel
        canLoadMore
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={onSelectSession}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={onStatusFilterChange}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={sessions}
        state="succeeded"
        statusFilter="active"
      />,
    )

    expect(screen.getByRole('complementary', { name: 'Sessions' })).toBeTruthy()
    // Scroll starts at the first session (chrome fixed above list).
    const listScroll = container.querySelector('[data-slot="session-list-scroll"]')
    expect(listScroll).toBeTruthy()
    expect(listScroll?.className).toMatch(/scrollbar-chat/)
    expect(listScroll?.className).toMatch(/overflow-y-auto/)
    expect(listScroll?.className).toMatch(/min-h-0/)
    // Flush right via parent pr-0, not negative margins (layout-safe).
    expect(listScroll?.className).not.toMatch(/-mr-/)
    expect(
      container.querySelector('[data-slot="session-list-chrome"]'),
    ).toBeTruthy()
    expect(
      listScroll?.contains(
        container.querySelector('[data-slot="data-list"]') as Node,
      ),
    ).toBe(true)
    expect(
      listScroll?.contains(
        container.querySelector('[data-slot="session-list-chrome"]') as Node,
      ),
    ).toBe(false)
    expect(container.querySelector('[data-slot="segmented-control"]')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: 'Active sessions' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(screen.getByRole('button', { name: 'Training sessions' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Archived sessions' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Active sessions' }).textContent).toMatch(
      /Active/i,
    )
    expect(screen.getByRole('button', { name: 'New chat' }).className).toMatch(
      /border-dashed/,
    )
    expect(container.querySelector('[data-slot="data-list-item"]')).toBeTruthy()
    const selectedRow = container.querySelector(
      '[data-slot="data-list-item"][data-selected]',
    )
    expect(selectedRow?.className).toMatch(/bg-primary\/15/)
    expect(selectedRow?.className).not.toMatch(/bg-muted text-foreground/)
    expect(
      screen.getByRole('button', { name: 'Active sessions' }).className,
    ).toMatch(/max-\[680px\]:min-h-11/)
    expect(
      screen.getByRole('button', { name: /Options for Architecture review/ })
        .className,
    ).toMatch(/max-\[680px\]:size-11/)
    expect(
      screen.getByRole('button', { name: /Options for Architecture review/ })
        .className,
    ).toMatch(/hover:bg-primary\/15/)
    const actions = container.querySelector(
      '[data-slot="session-row-actions"]',
    )
    expect(actions).toBeTruthy()
    // ⋮ must stay visible/clickable without hover (no opacity-0 / pointer-events-none).
    expect(actions?.className).not.toMatch(/opacity-0|pointer-events-none/)
    expect(
      screen.getByRole('button', { name: /Options for Architecture review/ }),
    ).toBeTruthy()
    const age = container.querySelector('[data-slot="session-row-age"]')
    expect(age).toBeTruthy()
    expect(age?.className).toMatch(/tabular-nums/)
    expect((age?.textContent ?? '').length).toBeGreaterThan(0)
    // beflow title fade: mask activates on group-hover
    const titleEl = container.querySelector('[data-slot="session-row-title"]')
    expect(titleEl?.className).toMatch(/mask-image:linear-gradient/)
    expect(titleEl?.className).toMatch(/group-hover/)

    await user.click(screen.getByRole('button', { name: 'Training sessions' }))
    expect(onStatusFilterChange).toHaveBeenCalledWith('training')
    await user.click(
      screen.getByRole('button', {
        name: 'Open session Architecture review (approved training)',
      }),
    )
    expect(onSelectSession).toHaveBeenCalledWith('session-1')
    expectNoLegacyHistoryClasses(container)
  })

  test('renders session action menus through Radix dropdown primitives', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn(async () => undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    render(
      <SessionNavigationPanel
        canLoadMore
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={sessions}
        state="succeeded"
        statusFilter="active"
      />,
    )

    const trigger = screen.getByRole('button', {
      name: /Options for Architecture review/,
    })

    expect(trigger.getAttribute('data-state')).toBe('closed')

    await user.click(trigger)

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(screen.getByRole('menu').getAttribute('data-slot')).toBe(
      'session-actions-menu',
    )
    expect(screen.getByRole('menu').className).toContain('max-[680px]:p-0.5')
    expect(screen.getByRole('menu').className).toContain('tracking-tight')
    // beflow-parity session menu: copy id, rename, archive
    expect(
      screen.getByRole('menuitem', { name: 'Copy session ID' }),
    ).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Rename' })).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Archive' })).toBeTruthy()

    await user.click(screen.getByRole('menuitem', { name: 'Copy session ID' }))
    expect(writeText).toHaveBeenCalledWith('session-1')
    expect(await screen.findByText('Session ID copied.')).toBeTruthy()
  })

  test('session action menu items keep DS primary highlight classes', async () => {
    const user = userEvent.setup()
    render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={sessions}
        state="succeeded"
        statusFilter="active"
      />,
    )

    await user.click(
      screen.getByRole('button', { name: /Options for Architecture review/ }),
    )
    const copyItem = screen.getByRole('menuitem', { name: 'Copy session ID' })
    expect(copyItem.className).toMatch(/hover:bg-primary\/15/)
    expect(copyItem.className).not.toMatch(/hover:bg-accent/)
  })

  test('rename focuses the input at the end; blur saves when dirty', async () => {
    const user = userEvent.setup()
    const onRenameSession = vi.fn()
    render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={onRenameSession}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId="session-1"
        sessions={sessions}
        state="succeeded"
        statusFilter="active"
      />,
    )

    await user.click(
      screen.getByRole('button', { name: /Options for Architecture review/ }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))

    const input = (await screen.findByLabelText(
      'New session name',
    )) as HTMLInputElement

    await vi.waitFor(() => {
      expect(document.activeElement).toBe(input)
    })
    expect(input.selectionStart).toBe(input.value.length)
    expect(input.selectionEnd).toBe(input.value.length)
    expect(input.value).toBe('Architecture review')

    // Unchanged blur cancels without save.
    await user.click(document.body)
    expect(screen.queryByLabelText('New session name')).toBeNull()
    expect(onRenameSession).not.toHaveBeenCalled()

    await user.click(
      screen.getByRole('button', { name: /Options for Architecture review/ }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))
    const dirty = (await screen.findByLabelText(
      'New session name',
    )) as HTMLInputElement
    await user.clear(dirty)
    await user.type(dirty, 'Renamed session')
    await user.click(document.body)
    expect(onRenameSession).toHaveBeenCalledWith('session-1', 'Renamed session')
    expect(screen.queryByLabelText('New session name')).toBeNull()
  })

  test('uses the shared DropdownMenu wrapper for session actions', () => {
    expect(historySource).toContain('@/components/ui/dropdown-menu')
    expect(historySource).not.toContain('@radix-ui/react-dropdown-menu')
  })

  test('uses lucide icons instead of inline SVG icon functions', () => {
    expect(historySource).toContain('lucide-react')
    expect(historySource).not.toContain('<svg')
    expect(historySource).not.toContain('function XIcon')
    expect(historySource).not.toContain('function PlusIcon')
    expect(historySource).not.toContain('function MoreVerticalIcon')
    expect(historySource).not.toContain('function BrainIcon')
    expect(historySource).not.toContain('ui-icon')
  })

  test('renders EmptyState copy per session filter', () => {
    const { container, unmount } = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId={null}
        sessions={[]}
        state="succeeded"
        statusFilter="training"
      />,
    )

    const empty = container.querySelector('[data-slot="session-list-empty"]')
    expect(empty).toBeTruthy()
    expect(empty?.getAttribute('data-status-filter')).toBe('training')
    expect(empty?.textContent).toContain('No training sessions yet.')
    expect(empty?.querySelector('[data-slot="empty-state"]')).toBeTruthy()
    unmount()

    const archived = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId={null}
        sessions={[]}
        state="succeeded"
        statusFilter="archived"
      />,
    )
    const archivedEmpty = archived.container.querySelector(
      '[data-slot="session-list-empty"]',
    )
    expect(archivedEmpty?.getAttribute('data-status-filter')).toBe('archived')
    expect(archivedEmpty?.textContent).toContain(
      'No archived conversations yet.',
    )
    archived.unmount()

    const active = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMore={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onUnarchiveSession={vi.fn()}
        selectedSessionId={null}
        sessions={[]}
        state="succeeded"
        statusFilter="active"
      />,
    )
    const activeEmpty = active.container.querySelector(
      '[data-slot="session-list-empty"]',
    )
    expect(activeEmpty?.getAttribute('data-status-filter')).toBe('active')
    expect(activeEmpty?.textContent).toContain('No conversations yet.')
    active.unmount()
  })
})

describe('WorkspaceInspectorPanel', () => {
  test('full session Context omits the Messages / turn dump', () => {
    render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    expect(screen.getByRole('region', { name: 'Session Context' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Selected Session Detail' })).toBeNull()
    expect(screen.queryByLabelText('Session Messages')).toBeNull()
    expect(screen.queryByText('No Messages In This Session.')).toBeNull()
  })

  test('shows loading skeletons instead of empty copy while detail loads', () => {
    render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={null}
        detailError={null}
        detailState="loading"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )
    expect(
      screen.getByLabelText('Loading Session Context').getAttribute('data-slot'),
    ).toBe('loading-grid')
    expect(
      screen.getByLabelText('Loading Action Stepper').getAttribute('data-slot'),
    ).toBe('loading-grid')
    // Messages panel only mounts in turn-focused mode (Ver detalles).
    expect(screen.queryByLabelText('Loading Session Detail')).toBeNull()
    expect(screen.queryByText('Select A Session To Inspect Model, Prompt And Usage Context.')).toBeNull()
    expect(screen.queryByText('No Stored Internal Actions For This Session.')).toBeNull()
  })

  test('maps blocked provider usage to a terminal failed trace step', () => {
    const blockedDetail: ChatSessionDetailResponse = {
      ...detail,
      provider_usage: [
        {
          ...detail.provider_usage[0],
          provider_usage_id: 'usage-blocked',
          status: 'blocked',
        },
      ],
    }
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={blockedDetail}
        detailError={null}
        detailState="succeeded"
        focusedTurn={{ question: 'What changed?', turnId: 'message-assistant' }}
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClearFocusedTurn={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const trace = container.querySelector('[data-slot="reasoning-trace"]')
    expect(trace).toBeTruthy()
    const providerStep = within(trace as HTMLElement)
      .getByText('qwen-plus')
      .closest('[data-slot="reasoning-trace-step"]')
    expect(providerStep?.getAttribute('data-status')).toBe('failed')
    expect(container.querySelector('[data-status="running"]')).toBeNull()
  })

  test('keeps one authoritative trace DOM with visible count and exact milliseconds', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const toggle = screen.getByRole('button', {
      name: 'Pipeline activity · 3 Steps',
    })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(container.querySelector('[data-slot="internal-action-records"]')).toBeNull()
    expect(screen.queryByText('retrieve')).toBeNull()

    await user.click(toggle)

    expect(screen.getAllByText('retrieve')).toHaveLength(1)
    expect(screen.getByText('80 ms')).toBeTruthy()
    expect(screen.queryByText('0.1s')).toBeNull()
  })

  test('filters session detail to a single turn window', () => {
    const multiTurn: ChatSessionDetailResponse = {
      ...detail,
      messages: [
        {
          content: 'First question?',
          created_at: '2026-06-21T00:00:00Z',
          message_id: 'user-1',
          metadata: null,
          role: 'user',
        },
        {
          content: 'First answer.',
          created_at: '2026-06-21T00:00:01Z',
          message_id: 'assistant-1',
          metadata: null,
          role: 'assistant',
        },
        {
          content: 'Second question?',
          created_at: '2026-06-21T00:01:00Z',
          message_id: 'user-2',
          metadata: null,
          role: 'user',
        },
        {
          content: 'Second answer.',
          created_at: '2026-06-21T00:01:01Z',
          message_id: 'assistant-2',
          metadata: null,
          role: 'assistant',
        },
      ],
      tool_calls: [
        {
          arguments: { query: 'first' },
          created_at: '2026-06-21T00:00:00.500Z',
          error_message: null,
          latency_ms: 10,
          result_summary: null,
          status: 'succeeded',
          tool_call_id: 'tool-first',
          tool_name: 'retrieve_first_turn',
          updated_at: '2026-06-21T00:00:00.600Z',
        },
        {
          arguments: { query: 'second' },
          created_at: '2026-06-21T00:01:00.500Z',
          error_message: null,
          latency_ms: 10,
          result_summary: null,
          status: 'succeeded',
          tool_call_id: 'tool-second',
          tool_name: 'retrieve_second_turn',
          updated_at: '2026-06-21T00:01:00.600Z',
        },
      ],
      retrieval_runs: [
        {
          created_at: '2026-06-21T00:00:00.500Z',
          error_message: null,
          filters: null,
          latency_ms: 5,
          query: 'first',
          retrieval_run_id: 'run-1',
          retrieved_chunks: [],
          strategy: 'dense',
          tool_call_id: 'tool-first',
          top_k: 3,
          used_rerank: false,
        },
        {
          created_at: '2026-06-21T00:01:00.500Z',
          error_message: null,
          filters: null,
          latency_ms: 5,
          query: 'second',
          retrieval_run_id: 'run-2',
          retrieved_chunks: [],
          strategy: 'dense',
          tool_call_id: 'tool-second',
          top_k: 3,
          used_rerank: false,
        },
      ],
      provider_usage: [
        {
          ...detail.provider_usage[0],
          created_at: '2026-06-21T00:00:02Z',
          provider_usage_id: 'usage-1',
        },
        {
          ...detail.provider_usage[0],
          created_at: '2026-06-21T00:01:02Z',
          provider_usage_id: 'usage-2',
        },
      ],
    }

    const scoped = filterSessionDetailToTurn(multiTurn, 'assistant-1')
    expect(scoped).not.toBeNull()
    expect(scoped?.messages.map((message) => message.message_id)).toEqual([
      'user-1',
      'assistant-1',
    ])
    expect(scoped?.tool_calls.map((call) => call.tool_name)).toEqual([
      'retrieve_first_turn',
    ])
    expect(scoped?.retrieval_runs.map((run) => run.retrieval_run_id)).toEqual([
      'run-1',
    ])
    expect(
      scoped?.provider_usage.map((usage) => usage.provider_usage_id),
    ).toEqual(['usage-1'])
  })

  test('turn-focused Context shows only that turn and Ver sesión completa clears focus', async () => {
    const user = userEvent.setup()
    const onClearFocusedTurn = vi.fn()
    const multiTurn: ChatSessionDetailResponse = {
      ...detail,
      messages: [
        {
          content: 'First question?',
          created_at: '2026-06-21T00:00:00Z',
          message_id: 'user-1',
          metadata: null,
          role: 'user',
        },
        {
          content: 'First answer with unique tool.',
          created_at: '2026-06-21T00:00:01Z',
          message_id: 'assistant-1',
          metadata: null,
          role: 'assistant',
        },
        {
          content: 'Second question?',
          created_at: '2026-06-21T00:01:00Z',
          message_id: 'user-2',
          metadata: null,
          role: 'user',
        },
        {
          content: 'Second answer later.',
          created_at: '2026-06-21T00:01:01Z',
          message_id: 'assistant-2',
          metadata: null,
          role: 'assistant',
        },
      ],
      tool_calls: [
        {
          arguments: { query: 'first' },
          created_at: '2026-06-21T00:00:00.500Z',
          error_message: null,
          latency_ms: 10,
          result_summary: null,
          status: 'succeeded',
          tool_call_id: 'tool-first',
          tool_name: 'retrieve_first_turn_only',
          updated_at: '2026-06-21T00:00:00.600Z',
        },
        {
          arguments: { query: 'second' },
          created_at: '2026-06-21T00:01:00.500Z',
          error_message: null,
          latency_ms: 10,
          result_summary: null,
          status: 'succeeded',
          tool_call_id: 'tool-second',
          tool_name: 'retrieve_second_turn_only',
          updated_at: '2026-06-21T00:01:00.600Z',
        },
      ],
      retrieval_runs: [],
      provider_usage: detail.provider_usage,
    }

    const { rerender } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={multiTurn}
        detailError={null}
        detailState="succeeded"
        focusedTurn={{ turnId: 'assistant-1', question: 'First question?' }}
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClearFocusedTurn={onClearFocusedTurn}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const turnHeader = screen.getByRole('region', { name: 'Detalles del turno' })
    expect(turnHeader).toBeTruthy()
    expect(within(turnHeader).getByText('First question?')).toBeTruthy()
    expect(screen.queryByText('This thread')).toBeNull()
    // Tool appears in pipeline + detail tool list when focused (both turn-scoped).
    expect(screen.getAllByText('retrieve_first_turn_only').length).toBeGreaterThan(0)
    expect(screen.queryByText('retrieve_second_turn_only')).toBeNull()
    expect(screen.getByText('First answer with unique tool.')).toBeTruthy()
    expect(screen.queryByText('Second answer later.')).toBeNull()
    expect(
      screen.getByRole('region', { name: 'Selected Session Detail' }).textContent,
    ).toMatch(/Turn messages/)

    await user.click(screen.getByRole('button', { name: 'Ver sesión completa' }))
    expect(onClearFocusedTurn).toHaveBeenCalledTimes(1)

    rerender(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={multiTurn}
        detailError={null}
        detailState="succeeded"
        focusedTurn={null}
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClearFocusedTurn={onClearFocusedTurn}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    expect(screen.getByText('This thread')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: /Pipeline activity/ }),
    )
    expect(screen.getAllByText('retrieve_first_turn_only').length).toBeGreaterThan(0)
    expect(screen.getAllByText('retrieve_second_turn_only').length).toBeGreaterThan(0)
    expect(screen.queryByRole('region', { name: 'Detalles del turno' })).toBeNull()
    // Full session overview must not remount the Messages / turn dump.
    expect(screen.queryByRole('region', { name: 'Selected Session Detail' })).toBeNull()
  })

  test('renders context details and source viewer with tokenized sections', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()
    const onStartNewSession = vi.fn()
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        liveContextSteps={[
          {
            id: 'context',
            status: 'done',
            detail: {
              total_messages: 22,
              kept_recent: 8,
              summarized_messages: 14,
              used_summary: true,
              summary:
                'Pinned user-stated facts (authoritative for this thread): - USER_FACT: Remember that my favorite color is cerulean-periwinkle-42. Please acknowledge. Exchange log - User: Remember that my favorite color is cerulean-periwinkle-42. Assistant: Got it.',
              summary_preview: 'Pinned user-stated facts…',
            },
          },
        ]}
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={onOpenSource}
        onStartNewSession={onStartNewSession}
        sourceViewer={{
          citationSnippet: 'The retrieval flow changed.',
          error: null,
          source,
          sourceId: 'source-1',
          state: 'succeeded',
        }}
      />,
    )

    expect(screen.getByRole('complementary', { name: 'Workspace Inspector' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    const sessionContext = screen.getByRole('region', { name: 'Session Context' })
    expect(sessionContext).toBeTruthy()
    // Ordered hierarchy: identity → model → usage → context packing
    expect(within(sessionContext).getByText('This thread')).toBeTruthy()
    expect(within(sessionContext).getByText('Continuing')).toBeTruthy()
    expect(
      sessionContext.querySelector('[data-slot="session-context-identity"]'),
    ).toBeTruthy()
    expect(
      sessionContext.querySelector('[data-slot="session-context-model"]'),
    ).toBeTruthy()
    expect(
      sessionContext.querySelector('[data-slot="session-context-usage"]'),
    ).toBeTruthy()
    expect(
      sessionContext.querySelector('[data-slot="session-context-window"]'),
    ).toBeTruthy()
    expect(within(sessionContext).getByText('Architecture review')).toBeTruthy()
    expect(
      sessionContext.querySelector('[title="session-1"]')?.textContent,
    ).toMatch(/session-1/)
    expect(within(sessionContext).getByText('Context window')).toBeTruthy()
    expect(within(sessionContext).getByText('8 recent + 14 summarized')).toBeTruthy()
    expect(
      within(sessionContext).getByText(/cerulean-periwinkle-42/),
    ).toBeTruthy()
    const contextWindowCard = sessionContext.querySelector(
      '[data-slot="context-window-card"]',
    )
    expect(contextWindowCard?.getAttribute('data-expanded')).toBe('false')
    // Pipeline activity is collapsed by default (progressive disclosure)
    expect(
      container.querySelector('[data-slot="context-action-stepper-details"]'),
    ).toBeTruthy()
    expect(
      container.querySelector('[data-slot="context-action-stepper-details"]')?.hasAttribute(
        'open',
      ),
    ).toBe(false)
    // Full overview: no message dump (turn list lives under Ver detalles only).
    expect(screen.queryByRole('region', { name: 'Selected Session Detail' })).toBeNull()
    expect(screen.queryByLabelText('assistant message')).toBeNull()
    expect(container.querySelector('[data-slot="reasoning-trace"]')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'New thread' }))
    expect(onStartNewSession).toHaveBeenCalledTimes(1)

    // Source Viewer is already open via citation path (not via Messages dump).
    const sourceViewer = screen.getByRole('region', { name: 'Source Viewer' })
    expect(within(sourceViewer).getByText('architecture.md')).toBeTruthy()
    expect(within(sourceViewer).getByText('The retrieval flow changed.')).toBeTruthy()
    // View Source buttons live under turn-scoped Messages (Ver detalles), not overview.
    expect(
      screen.queryByRole('button', { name: 'View Source architecture.md' }),
    ).toBeNull()
    expect(onOpenSource).not.toHaveBeenCalled()
    expectNoLegacyHistoryClasses(container)
  })

  test('composes turn retrieval and pipeline records through inspector patterns', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        focusedTurn={{
          question: 'What changed?',
          turnId: 'message-assistant',
        }}
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClearFocusedTurn={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={onOpenSource}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    expect(
      container.querySelector('[data-slot="reasoning-trace"]'),
    ).toBeTruthy()
    expect(container.querySelector('[data-slot="records-grid"]')).toBeTruthy()
    const context = screen.getByRole('list', {
      name: 'Retrieved context',
    })
    expect(context.getAttribute('data-slot')).toBe('context-chunk-list')

    await user.click(
      within(context).getByRole('button', {
        name: 'View Source architecture.md',
      }),
    )
    expect(onOpenSource).toHaveBeenCalledWith(
      'source-1',
      'The retrieval flow changed.',
    )
  })

  test('context window expands and collapses the condensed summary', async () => {
    const user = userEvent.setup()
    const longSummary = [
      'Pinned user-stated facts (authoritative for this thread):',
      '- USER_FACT: Remember that my favorite color is cerulean-periwinkle-42.',
      'Exchange log:',
      '- User: Remember that my favorite color is cerulean-periwinkle-42. Please acknowledge.',
      '- Assistant: Got it, I will remember that.',
      '- User: Filler question about unrelated topics that still needs room.',
    ].join('\n')

    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        liveContextSteps={[
          {
            id: 'context',
            status: 'done',
            detail: {
              total_messages: 22,
              kept_recent: 8,
              summarized_messages: 14,
              used_summary: true,
              summary: longSummary,
              summary_preview: `${longSummary.slice(0, 237)}...`,
            },
          },
        ]}
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const expand = screen.getByRole('button', { name: 'Expandir' })
    expect(expand.getAttribute('aria-expanded')).toBe('false')
    expect(
      container.querySelector('[data-slot="context-window-card"]')?.getAttribute(
        'data-expanded',
      ),
    ).toBe('false')
    expect(
      container
        .querySelector('[data-slot="context-window-summary"]')
        ?.className,
    ).toMatch(/line-clamp-3/)

    await user.click(expand)

    expect(screen.getByRole('button', { name: 'Contraer' }).getAttribute('aria-expanded')).toBe(
      'true',
    )
    expect(
      container.querySelector('[data-slot="context-window-card"]')?.getAttribute(
        'data-expanded',
      ),
    ).toBe('true')
    expect(
      container
        .querySelector('[data-slot="context-window-summary"]')
        ?.className,
    ).toMatch(/whitespace-pre-wrap/)
    expect(screen.getByText(/Filler question about unrelated topics/)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Contraer' }))
    expect(screen.getByRole('button', { name: 'Expandir' })).toBeTruthy()
    expect(
      container.querySelector('[data-slot="context-window-card"]')?.getAttribute(
        'data-expanded',
      ),
    ).toBe('false')
  })


  test('shows a warning badge when the source is soft-deleted', () => {
    const deletedSource: Source = {
      ...source,
      deleted_at: '2026-06-22T12:00:00Z',
    }
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: deletedSource,
          sourceId: deletedSource.id,
          state: 'succeeded',
        }}
      />,
    )

    const viewer = screen.getByRole('region', { name: 'Source Viewer' })
    const badge = within(viewer).getByText('Deleted', {
      selector: '[data-slot="badge"]',
    })
    expect(badge.getAttribute('data-slot')).toBe('badge')
    expect(badge.getAttribute('data-tone')).toBe('danger')
    expect(within(viewer).getByText('Deleted', { selector: 'dt' })).toBeTruthy()
    expectNoLegacyHistoryClasses(container)
  })

  test('renders minimap tab navigation without legacy lists', async () => {
    const user = userEvent.setup()
    const onNavigateMessage = vi.fn()
    const { container } = render(
      <WorkspaceInspectorPanel
        activeTab="minimap"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="overlay"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={onNavigateMessage}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'assistant: The retrieval flow changed.' }))
    expect(onNavigateMessage).toHaveBeenCalledWith('message-assistant')
    expect(within(screen.getByRole('navigation', { name: 'Conversation Minimap' })).getByText('2 Messages')).toBeTruthy()
    expectNoLegacyHistoryClasses(container)
  })

  test('truncates long minimap aria-labels', () => {
    const longContent = 'x'.repeat(140)
    const longDetail: ChatSessionDetailResponse = {
      ...detail,
      messages: [
        {
          content: longContent,
          created_at: '2026-06-21T00:00:00Z',
          message_id: 'message-long',
          metadata: null,
          role: 'user',
        },
      ],
    }
    render(
      <WorkspaceInspectorPanel
        activeTab="minimap"
        detail={longDetail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const button = screen.getByRole('button', { name: /^user: / })
    const label = button.getAttribute('aria-label') ?? ''
    expect(label.startsWith('user: ')).toBe(true)
    expect(label.length).toBeLessThanOrEqual('user: '.length + 96)
    expect(label.endsWith('…')).toBe(true)
  })

  test('overlay Escape closes inspector and focuses close control on open', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="overlay"
        onActiveTabChange={vi.fn()}
        onClose={onClose}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    expect(screen.getByRole('dialog', { name: 'Workspace Inspector' })).toBeTruthy()
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Close Right Sidebar' }),
    )

    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  test('inline Escape does not close the inspector', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="inline"
        onActiveTabChange={vi.fn()}
        onClose={onClose}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    expect(
      screen.getByRole('complementary', { name: 'Workspace Inspector' }),
    ).toBeTruthy()
    await user.keyboard('{Escape}')
    expect(onClose).not.toHaveBeenCalled()
  })

  test('overlay Tab cycles within the inspector dialog', async () => {
    const user = userEvent.setup()
    render(
      <WorkspaceInspectorPanel
        activeTab="context"
        detail={detail}
        detailError={null}
        detailState="succeeded"
        layout="overlay"
        onActiveTabChange={vi.fn()}
        onClose={vi.fn()}
        onNavigateMessage={vi.fn()}
        onOpenSource={vi.fn()}
        sourceViewer={{
          citationSnippet: null,
          error: null,
          source: null,
          sourceId: null,
          state: 'idle',
        }}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Workspace Inspector' })
    const close = screen.getByRole('button', { name: 'Close Right Sidebar' })
    expect(document.activeElement).toBe(close)

    await user.tab()
    expect(dialog.contains(document.activeElement)).toBe(true)

    // Tabbing repeatedly must keep focus inside the dialog (trap / wrap).
    for (let i = 0; i < 20; i += 1) {
      await user.tab()
      expect(dialog.contains(document.activeElement)).toBe(true)
    }
  })
})
