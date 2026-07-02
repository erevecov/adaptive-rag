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
    expect(screen.getByRole('button', { name: 'ACTIVOS' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(container.querySelector('[data-slot="data-list-item"]')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'TRAIN' }))
    expect(onStatusFilterChange).toHaveBeenCalledWith('training')
    await user.click(screen.getByRole('button', { name: 'Abrir sesiÃ³n Architecture review' }))
    expect(onSelectSession).toHaveBeenCalledWith('session-1')
    expectNoLegacyHistoryClasses(container)
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
})
