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

const source: Source = {
  created_at: '2026-06-20T00:00:00Z',
  external_id: 'architecture.md',
  extra_metadata: { owner: 'docs' },
  id: 'source-1',
  project_id: 'project-1',
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
  test('renders session filters and rows with tokenized primitives', async () => {
    const user = userEvent.setup()
    const onStatusFilterChange = vi.fn()
    const onSelectSession = vi.fn()
    const { container } = render(
      <SessionNavigationPanel
        canLoadMore
        error={null}
        onArchiveSession={vi.fn()}
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

    expect(screen.getByRole('complementary', { name: 'Sesiones' })).toBeTruthy()
    expect(container.querySelector('[data-slot="segmented-control"]')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: 'Sesiones activas' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(screen.getByRole('button', { name: 'Sesiones con entrenamiento' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Sesiones archivadas' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Sesiones activas' }).textContent).toMatch(
      /Activos/i,
    )
    expect(screen.getByRole('button', { name: 'Nuevo chat' }).className).toMatch(
      /border-dashed/,
    )
    expect(container.querySelector('[data-slot="data-list-item"]')).toBeTruthy()
    const actions = container.querySelector(
      '[data-slot="session-row-actions"]',
    )
    expect(actions).toBeTruthy()
    // ⋮ must stay visible/clickable without hover (no opacity-0 / pointer-events-none).
    expect(actions?.className).not.toMatch(/opacity-0|pointer-events-none/)
    expect(
      screen.getByRole('button', { name: /Opciones de Architecture review/ }),
    ).toBeTruthy()
    const age = container.querySelector('[data-slot="session-row-age"]')
    expect(age).toBeTruthy()
    expect(age?.className).toMatch(/tabular-nums/)
    expect((age?.textContent ?? '').length).toBeGreaterThan(0)
    // beflow title fade: mask activates on group-hover
    const titleEl = container.querySelector('[data-slot="session-row-title"]')
    expect(titleEl?.className).toMatch(/mask-image:linear-gradient/)
    expect(titleEl?.className).toMatch(/group-hover/)

    await user.click(screen.getByRole('button', { name: 'Sesiones con entrenamiento' }))
    expect(onStatusFilterChange).toHaveBeenCalledWith('training')
    await user.click(
      screen.getByRole('button', {
        name: 'Abrir sesión Architecture review (entrenamiento aprobado)',
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
      name: /Opciones de Architecture review/,
    })

    expect(trigger.getAttribute('data-state')).toBe('closed')

    await user.click(trigger)

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(screen.getByRole('menu').getAttribute('data-slot')).toBe(
      'session-actions-menu',
    )
    // beflow-parity session menu: copy id, rename, archive
    expect(
      screen.getByRole('menuitem', { name: 'Copiar ID de sesión' }),
    ).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Renombrar' })).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Archivar' })).toBeTruthy()

    await user.click(screen.getByRole('menuitem', { name: 'Copiar ID de sesión' }))
    expect(writeText).toHaveBeenCalledWith('session-1')
    expect(await screen.findByText('ID de sesión copiado.')).toBeTruthy()
  })

  test('rename focuses the input at the end and cancels on blur', async () => {
    const user = userEvent.setup()
    const onRenameSession = vi.fn()
    render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
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
      screen.getByRole('button', { name: /Opciones de Architecture review/ }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Renombrar' }))

    const input = (await screen.findByLabelText(
      'Nuevo nombre de sesión',
    )) as HTMLInputElement

    await vi.waitFor(() => {
      expect(document.activeElement).toBe(input)
    })
    expect(input.selectionStart).toBe(input.value.length)
    expect(input.selectionEnd).toBe(input.value.length)
    expect(input.value).toBe('Architecture review')

    await user.click(document.body)
    expect(screen.queryByLabelText('Nuevo nombre de sesión')).toBeNull()
    expect(onRenameSession).not.toHaveBeenCalled()
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
    expect(empty?.textContent).toContain('Aún no hay entrenamiento.')
    expect(empty?.querySelector('[data-slot="empty-state"]')).toBeTruthy()
    unmount()

    const archived = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
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
      'Aún no hay conversaciones archivadas.',
    )
    archived.unmount()

    const active = render(
      <SessionNavigationPanel
        canLoadMore={false}
        error={null}
        onArchiveSession={vi.fn()}
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
    expect(activeEmpty?.textContent).toContain('Aún no hay conversaciones.')
    active.unmount()
  })
})

describe('WorkspaceInspectorPanel', () => {
  test('renders context details and source viewer with tokenized sections', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()
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
        onOpenSource={onOpenSource}
        sourceViewer={{
          citationSnippet: 'The retrieval flow changed.',
          error: null,
          source,
          sourceId: 'source-1',
          state: 'succeeded',
        }}
      />,
    )

    expect(screen.getByRole('complementary', { name: 'Workspace inspector' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Context' }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByRole('region', { name: 'Session context' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Selected session detail' })).toBeTruthy()
    expect(screen.getByLabelText('assistant message').getAttribute('tabindex')).toBe('-1')
    expect(container.querySelector('[data-slot="data-list"]')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'View source architecture.md' }))
    expect(onOpenSource).toHaveBeenCalledWith(
      'source-1',
      'The retrieval flow changed.',
    )
    expectNoLegacyHistoryClasses(container)
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

    const viewer = screen.getByRole('region', { name: 'Source viewer' })
    const badge = within(viewer).getByText('eliminada')
    expect(badge.getAttribute('data-slot')).toBe('badge')
    expect(badge.getAttribute('data-tone')).toBe('warning')
    expect(within(viewer).getByText('Deleted')).toBeTruthy()
    expect(within(viewer).getByText('2026-06-22T12:00:00Z')).toBeTruthy()
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
    expect(within(screen.getByRole('navigation', { name: 'Conversation minimap' })).getByText('2 turns')).toBeTruthy()
    expectNoLegacyHistoryClasses(container)
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

    expect(screen.getByRole('dialog', { name: 'Workspace inspector' })).toBeTruthy()
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Close right sidebar' }),
    )

    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
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

    const dialog = screen.getByRole('dialog', { name: 'Workspace inspector' })
    const close = screen.getByRole('button', { name: 'Close right sidebar' })
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
