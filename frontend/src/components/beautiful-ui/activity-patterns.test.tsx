/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { AgentTaskList } from './agent-task-list'
import { CodeStream } from './code-stream'
import { LoadingGrid } from './loading-grid'
import { ReasoningTrace } from './reasoning-trace'
import { ToolActivity } from './tool-activity'

afterEach(() => {
  cleanup()
})

describe('LoadingGrid', () => {
  test('announces active work with caller-derived elapsed time', () => {
    render(<LoadingGrid label="Retrieving sources" elapsedMs={1_250} variant="dots" />)

    const loading = screen.getByRole('status', { name: 'Retrieving sources' })
    expect(loading.getAttribute('aria-live')).toBe('polite')
    expect(loading.getAttribute('data-variant')).toBe('dots')
    expect(loading.textContent).toContain('1.3s')
  })

  test('uses a motion-safe orbit mark for the orbit variant', () => {
    const { container } = render(<LoadingGrid label="Connecting" variant="orbit" />)

    expect(container.querySelector('[data-slot="loading-mark"]')?.className).toContain(
      'motion-safe:animate-spin',
    )
  })
})

describe('ReasoningTrace', () => {
  test('supports a controlled feature accordion with preserved summary and detail slots', async () => {
    const user = userEvent.setup()
    const onExpandedChange = vi.fn()
    const { rerender } = render(
      <ReasoningTrace
        empty={<p>Waiting for pipeline steps</p>}
        expanded={false}
        label="Chat Pipeline Steps"
        onExpandedChange={onExpandedChange}
        steps={[
          {
            elapsedLabel: '200 ms',
            id: 'retrieval',
            label: 'retrieval',
            status: 'running',
          },
        ]}
        summary={<span>Steps · 200 ms · 0 Sources</span>}
        toggleClassName="feature-summary"
        toggleLabel="Expand Chat Steps, retrieval, running, 200 ms"
      >
        <p>Feature-owned response details</p>
      </ReasoningTrace>,
    )

    const toggle = screen.getByRole('button', {
      name: 'Expand Chat Steps, retrieval, running, 200 ms',
    })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Waiting for pipeline steps')).toBeNull()
    await user.click(toggle)
    expect(onExpandedChange).toHaveBeenCalledWith(true)

    rerender(
      <ReasoningTrace
        empty={<p>Waiting for pipeline steps</p>}
        expanded
        label="Chat Pipeline Steps"
        onExpandedChange={onExpandedChange}
        steps={[
          {
            elapsedLabel: '200 ms',
            id: 'retrieval',
            label: 'retrieval',
            status: 'running',
          },
        ]}
        summary={<span>Steps · 200 ms · 0 Sources</span>}
        toggleClassName="feature-summary"
        toggleLabel="Collapse Chat Steps, Steps · 200 ms · 0 Sources"
      >
        <p>Feature-owned response details</p>
      </ReasoningTrace>,
    )

    expect(screen.getByText('200 ms')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /Collapse Chat Steps/ }).className,
    ).toContain('feature-summary')
    expect(screen.getByText('Feature-owned response details')).toBeTruthy()
  })

  test('exposes expansion state and failed step detail', async () => {
    const user = userEvent.setup()
    render(
      <ReasoningTrace
        label="Chat steps"
        steps={[
          {
            detail: 'Timed out',
            id: 'retrieval',
            label: 'Retrieval',
            status: 'failed',
          },
        ]}
      />,
    )

    const toggle = screen.getByRole('button', { name: /Chat steps/ })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    await user.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('Timed out')).toBeTruthy()
    expect(screen.getByText('failed').getAttribute('data-tone')).toBe('danger')
  })

  test('opens initially when requested', () => {
    render(
      <ReasoningTrace
        defaultExpanded
        label="Execution trace"
        steps={[{ id: 'answer', label: 'Answer', status: 'completed' }]}
      />,
    )

    expect(
      screen.getByRole('button', { name: /Execution trace/ }).getAttribute('aria-expanded'),
    ).toBe('true')
    expect(screen.getByText('completed').getAttribute('data-tone')).toBe('success')
  })

  test('preserves a feature step whose detail is independently collapsible', () => {
    render(
      <ReasoningTrace
        defaultExpanded
        label="Execution trace"
        steps={[
          {
            collapsibleDetail: true,
            detail: 'Provider usage',
            id: 'answer',
            label: 'Answer',
            status: 'completed',
          },
        ]}
      />,
    )

    const details = screen.getByText('Answer').closest('details')
    expect(details).not.toBeNull()
    expect(details?.hasAttribute('open')).toBe(false)
    expect(screen.getByText('Provider usage')).toBeTruthy()
  })

  test('uses phrasing content inside a collapsible step summary', () => {
    const { container } = render(
      <ReasoningTrace
        defaultExpanded
        label="Execution trace"
        steps={[
          {
            collapsibleDetail: true,
            detail: 'Provider usage',
            id: 'answer',
            label: 'Answer',
            status: 'completed',
          },
        ]}
      />,
    )

    const summary = container.querySelector('summary')
    expect(summary).not.toBeNull()
    expect(summary?.querySelector('div')).toBeNull()
    expect(summary?.querySelector(':scope > span')).not.toBeNull()
  })
})

describe('ToolActivity', () => {
  test('expands each tool detail independently', async () => {
    const user = userEvent.setup()
    render(
      <ToolActivity
        label="Tool activity"
        items={[
          {
            detail: 'Found three sources',
            id: 'search',
            label: 'Search sources',
            meta: '3 results',
            status: 'completed',
          },
          {
            detail: 'Request is pending',
            id: 'fetch',
            label: 'Fetch document',
            status: 'running',
          },
        ]}
      />,
    )

    const searchToggle = screen.getByRole('button', { name: /Search sources/ })
    const fetchToggle = screen.getByRole('button', { name: /Fetch document/ })
    expect(searchToggle.getAttribute('aria-expanded')).toBe('false')
    expect(fetchToggle.getAttribute('aria-expanded')).toBe('false')

    await user.click(searchToggle)

    expect(screen.getByText('Found three sources')).toBeTruthy()
    expect(searchToggle.getAttribute('aria-expanded')).toBe('true')
    expect(fetchToggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Request is pending')).toBeNull()
  })

  test('wraps long tool identifiers and query metadata without losing accessible content', () => {
    const label = 'tool-with-an-extremely-long-unbroken-identifier-that-must-wrap'
    const query = 'query-with-an-extremely-long-unbroken-value-that-must-remain-visible'
    render(
      <ToolActivity
        label="Tool activity"
        items={[
          {
            detail: 'Stored detail',
            id: 'long-tool',
            label,
            meta: query,
            status: 'completed',
          },
        ]}
      />,
    )

    const toggle = screen.getByRole('button', {
      name: `${label}, ${query}, completed`,
    })
    expect(toggle.className).toContain('min-w-0')
    expect(toggle.className).toContain('whitespace-normal')
    expect(screen.getByText(label).className).toContain('break-words')
    expect(screen.getByText(query).className).toContain('break-words')
    expect(toggle.className).toContain('max-[680px]:min-h-11')
  })
})

describe('AgentTaskList', () => {
  test('uses the supplied empty label when no tasks exist', () => {
    render(<AgentTaskList emptyLabel="No ingestion jobs" label="Ingestion" tasks={[]} />)

    expect(screen.getByRole('status').textContent).toContain('No ingestion jobs')
  })

  test('renders completed and failed task states', () => {
    render(
      <AgentTaskList
        emptyLabel="No tasks"
        label="Background work"
        tasks={[
          { id: 'index', label: 'Index handbook', status: 'completed' },
          { id: 'extract', label: 'Extract entities', status: 'failed' },
        ]}
      />,
    )

    expect(screen.getByText('completed').getAttribute('data-tone')).toBe('success')
    expect(screen.getByText('failed').getAttribute('data-tone')).toBe('danger')
    expect(screen.getByText('failed').className).toContain('rounded-[2px]')
    expect(screen.getByText('failed').className).not.toContain('rounded-md')
    expect(screen.getByText('failed').className).not.toContain('max-[680px]:rounded-sm')
  })

  test('renders operational task states with exact labels and only animates running work', () => {
    const { container } = render(
      <AgentTaskList
        emptyLabel="No tasks"
        label="Operational work"
        tasks={[
          { id: 'queued', label: 'Queued job', status: 'queued', statusLabel: 'Queued' },
          { id: 'running', label: 'Running job', status: 'running', statusLabel: 'Running' },
          { id: 'succeeded', label: 'Succeeded job', status: 'succeeded', statusLabel: 'Succeeded' },
          { id: 'failed', label: 'Failed job', status: 'failed', statusLabel: 'Failed' },
          { id: 'blocked', label: 'Blocked job', status: 'blocked', statusLabel: 'Blocked' },
          {
            id: 'dead-letter',
            label: 'Dead-letter job',
            status: 'dead_letter',
            statusLabel: 'Dead letter',
          },
          { id: 'canceled', label: 'Canceled job', status: 'canceled', statusLabel: 'Canceled' },
        ]}
      />,
    )

    const rows = Array.from(container.querySelectorAll('[data-slot="agent-task-row"]'))
    expect(rows.map((row) => row.getAttribute('data-status'))).toEqual([
      'queued',
      'running',
      'succeeded',
      'failed',
      'blocked',
      'dead_letter',
      'canceled',
    ])
    expect(rows.map((row) => row.querySelector('[data-slot="badge"]')?.textContent)).toEqual([
      'Queued',
      'Running',
      'Succeeded',
      'Failed',
      'Blocked',
      'Dead letter',
      'Canceled',
    ])
    expect(
      rows.map((row) => row.querySelector('[data-slot="badge"]')?.getAttribute('data-tone')),
    ).toEqual(['neutral', 'primary', 'success', 'danger', 'danger', 'danger', 'neutral'])
    expect(
      rows.map((row) =>
        row
          .querySelector('[data-slot="agent-task-status-icon"]')
          ?.getAttribute('class')
          ?.includes('motion-safe:animate-spin'),
      ),
    ).toEqual([false, true, false, false, false, false, false])
    expect(
      [rows[0], rows[6]].map((row) =>
        row
          .querySelector('[data-slot="agent-task-status-icon"]')
          ?.getAttribute('class')
          ?.includes('lucide-circle'),
      ),
    ).toEqual([true, true])
  })
})

describe('CodeStream', () => {
  test('displays a line number for each line of multiline code', () => {
    const { container } = render(
      <CodeStream code={'const answer = 42\nreturn answer'} copyLabel="Copy code" />,
    )

    expect(
      Array.from(container.querySelectorAll('[data-slot="code-stream-line-number"]')).map(
        (line) => line.textContent,
      ),
    ).toEqual(['1', '2'])
  })

  test('copies the exact code through its callback', async () => {
    const user = userEvent.setup()
    const onCopy = vi.fn()
    render(
      <CodeStream
        code="const answer = 42"
        copyLabel="Copy code"
        filename="answer.ts"
        language="typescript"
        onCopy={onCopy}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Copy code' }))

    expect(onCopy).toHaveBeenCalledWith('const answer = 42')
    expect(screen.getByLabelText('Code: answer.ts').textContent).toContain('const answer = 42')
    expect(screen.getByText('typescript')).toBeTruthy()
  })
})

test('bordered activity containers retain the global square chrome', () => {
  const { container } = render(
    <>
      <ReasoningTrace
        defaultExpanded
        label="Trace"
        steps={[{ id: 'retrieve', label: 'Retrieve', status: 'running' }]}
      />
      <ToolActivity
        label="Tools"
        items={[{ id: 'search', label: 'Search', status: 'completed' }]}
      />
      <AgentTaskList
        emptyLabel="No tasks"
        label="Tasks"
        tasks={[{ id: 'index', label: 'Index', status: 'completed' }]}
      />
    </>,
  )

  for (const selector of [
    '[data-slot="reasoning-trace-list"]',
    '[data-slot="tool-activity"]',
    '[data-slot="agent-task-list"] ul',
  ]) {
    expect(container.querySelector(selector)?.className).toContain('rounded-[2px]')
  }
})
