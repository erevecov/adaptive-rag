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
