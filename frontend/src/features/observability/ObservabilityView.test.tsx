/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { ChatObservabilitySummary } from '@/lib/apiClient'
import { ObservabilityPanel } from './ObservabilityView'

afterEach(() => {
  cleanup()
})

const summary: ChatObservabilitySummary = {
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
  project_id: 'project-1',
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

function renderObservabilityPanel(
  overrides: Partial<React.ComponentProps<typeof ObservabilityPanel>> = {},
) {
  const props: React.ComponentProps<typeof ObservabilityPanel> = {
    activeSubmodule: 'summary',
    createdAtFrom: '',
    createdAtTo: '',
    error: null,
    onCreatedAtFromChange: vi.fn(),
    onCreatedAtToChange: vi.fn(),
    onProjectIdChange: vi.fn(),
    onRefresh: vi.fn(),
    onStatusChange: vi.fn(),
    onSubmoduleChange: vi.fn(),
    projectId: 'project-1',
    state: 'idle',
    status: '',
    summary,
    ...overrides,
  }

  return {
    props,
    view: render(<ObservabilityPanel {...props} />),
  }
}

function expectNoLegacyObservabilityClasses(container: HTMLElement) {
  expect(container.querySelector('.observability-panel')).toBeNull()
  expect(container.querySelector('.observability-filters')).toBeNull()
  expect(container.querySelector('.metric-card')).toBeNull()
  expect(container.querySelector('.breakdown-card')).toBeNull()
  expect(container.querySelector('.observability-table')).toBeNull()
  expect(container.querySelector('.table-scroll')).toBeNull()
}

describe('ObservabilityPanel', () => {
  test('renders tokenized filters, status, and local view switcher', async () => {
    const user = userEvent.setup()
    const { props, view } = renderObservabilityPanel({ summary: null })

    expect(screen.getByRole('region', { name: 'Observability summary' })).toBeTruthy()
    expect(screen.getByLabelText('Project ID').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Status').getAttribute('data-slot')).toBe(
      'native-select',
    )
    expect(
      view.container.querySelector('[data-slot="segmented-control"]'),
    ).toBeTruthy()
    expect(screen.getByText('Ready').getAttribute('data-slot')).toBe('badge')
    expect(
      view.container.querySelector('[data-slot="empty-state"]'),
    ).toBeTruthy()
    expectNoLegacyObservabilityClasses(view.container)

    await user.click(screen.getByRole('button', { name: 'Latency' }))
    expect(props.onSubmoduleChange).toHaveBeenCalledWith('latency')
  })

  test('matches empty-state copy to the active observability view', () => {
    const { view } = renderObservabilityPanel({
      activeSubmodule: 'latency',
      summary: null,
    })

    expect(screen.getByRole('region', { name: 'Observability latency' })).toBeTruthy()
    expect(screen.getByText(/No latency groups available yet/)).toBeTruthy()
    expectNoLegacyObservabilityClasses(view.container)
  })

  test('summary view renders metric cards and data-list breakdowns', () => {
    const { view } = renderObservabilityPanel()

    const metrics = screen.getByLabelText('Chat observability metrics')
    expect(within(metrics).getByText('12')).toBeTruthy()
    expect(within(metrics).getByText('$0.1234')).toBeTruthy()
    expect(within(metrics).getByText('410 ms')).toBeTruthy()

    const statusSection = screen.getByRole('region', {
      name: 'Status breakdown',
    })
    expect(
      within(statusSection).getByText('10 sessions').getAttribute('data-slot'),
    ).toBe('badge')
    expect(
      statusSection.querySelector('[data-slot="data-list-item"]'),
    ).toBeTruthy()

    expect(screen.getByRole('region', { name: 'Provider usage' })).toBeTruthy()
    expect(
      view.container.querySelector('[data-slot="table-scroll"]'),
    ).toBeTruthy()
    expect(view.container.querySelector('[data-slot="table"]')).toBeTruthy()
    expectNoLegacyObservabilityClasses(view.container)
  })

  test('cost and latency views use table primitives with stable headers', () => {
    const { view, view: { rerender } } = renderObservabilityPanel({
      activeSubmodule: 'costs',
    })

    expect(screen.getByRole('region', { name: 'Provider usage' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Operation' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Tokens' })).toBeTruthy()
    expect(screen.getByText('1,840')).toBeTruthy()

    rerender(
      <ObservabilityPanel
        activeSubmodule="latency"
        createdAtFrom=""
        createdAtTo=""
        error={null}
        onCreatedAtFromChange={vi.fn()}
        onCreatedAtToChange={vi.fn()}
        onProjectIdChange={vi.fn()}
        onRefresh={vi.fn()}
        onStatusChange={vi.fn()}
        onSubmoduleChange={vi.fn()}
        projectId="project-1"
        state="idle"
        status=""
        summary={summary}
      />,
    )

    expect(screen.getByRole('region', { name: 'Provider latency' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Avg' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Max' })).toBeTruthy()
    expect(screen.getByText('420 ms')).toBeTruthy()
    expectNoLegacyObservabilityClasses(view.container)
  })

  test('error state keeps filter values and exposes alert semantics', () => {
    renderObservabilityPanel({
      createdAtFrom: '2026-06-21T00:00:00Z',
      error: 'observability unavailable',
      state: 'failed',
      status: 'failed',
      summary: null,
    })

    expect((screen.getByLabelText('Created from') as HTMLInputElement).value).toBe(
      '2026-06-21T00:00:00Z',
    )
    expect((screen.getByLabelText('Status') as HTMLSelectElement).value).toBe(
      'failed',
    )
    expect(screen.getByRole('alert').textContent).toContain(
      'observability unavailable',
    )
  })
})
