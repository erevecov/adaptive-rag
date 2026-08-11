/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test } from 'vitest'

import { ChatPipelineSteps } from './ChatPipelineSteps'
import chatPipelineStepsSource from './ChatPipelineSteps.tsx?raw'
import { resetOpenDetailsInstanceIdForTests } from '../lib/detailsAccordion'

function installLocalStorage() {
  const entries = new Map<string, string>()
  const storage = {
    get length() {
      return entries.size
    },
    clear() {
      entries.clear()
    },
    getItem(key: string) {
      return entries.get(key) ?? null
    },
    key(index: number) {
      return Array.from(entries.keys())[index] ?? null
    },
    removeItem(key: string) {
      entries.delete(key)
    },
    setItem(key: string, value: string) {
      entries.set(key, value)
    },
  } satisfies Storage

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage,
  })
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: storage,
  })
}

describe('ChatPipelineSteps', () => {
  beforeEach(() => {
    installLocalStorage()
    resetOpenDetailsInstanceIdForTests()
  })

  afterEach(() => {
    cleanup()
    resetOpenDetailsInstanceIdForTests()
  })

  test('defaults to collapsed streaming ticker and expands without global persistence', async () => {
    const user = userEvent.setup()

    render(
      <ChatPipelineSteps
        instanceId="stream-a"
        isStreaming
        sourceCount={0}
        steps={[
          {
            detail: { limit: 3, query: 'alpha' },
            id: 'retrieval',
            status: 'start',
          },
        ]}
      />,
    )

    const stepper = screen.getByRole('region', { name: 'Chat Pipeline Steps' })
    expect(stepper.getAttribute('data-slot')).toBe('reasoning-trace')
    expect(within(stepper).getByText('retrieval')).toBeTruthy()
    expect(within(stepper).queryByText('alpha')).toBeNull()

    await user.click(
      within(stepper).getByRole('button', {
        name: /Expand Chat Steps, retrieval, running/,
      }),
    )

    expect(within(stepper).getByText('alpha')).toBeTruthy()
    expect(
      within(stepper).getByRole('button', { name: /Collapse Chat Steps/ }).getAttribute(
        'aria-expanded',
      ),
    ).toBe('true')
  })

  test('only one Details panel is open at a time (accordion)', async () => {
    const user = userEvent.setup()
    render(
      <>
        <ChatPipelineSteps
          instanceId="turn-1"
          isStreaming={false}
          sourceCount={1}
          steps={[
            {
              detail: { sources: 1 },
              elapsed_ms: 1000,
              id: 'answer',
              status: 'done',
            },
          ]}
        />
        <ChatPipelineSteps
          instanceId="turn-2"
          isStreaming={false}
          sourceCount={2}
          steps={[
            {
              detail: { sources: 2 },
              elapsed_ms: 2000,
              id: 'retrieval',
              status: 'done',
            },
          ]}
        />
      </>,
    )

    const steppers = screen.getAllByRole('region', {
      name: 'Chat Pipeline Steps',
    })
    expect(steppers).toHaveLength(2)

    await user.click(
      within(steppers[0]!).getByRole('button', {
        name: 'Expand Chat Steps, 1.0 s, 1 Source',
      }),
    )
    expect(within(steppers[0]!).getByText('answer')).toBeTruthy()
    expect(within(steppers[1]!).queryByText('retrieval')).toBeNull()

    await user.click(
      within(steppers[1]!).getByRole('button', {
        name: 'Expand Chat Steps, 2.0 s, 2 Sources',
      }),
    )
    // First closed; second open.
    expect(within(steppers[0]!).queryByText('answer')).toBeNull()
    expect(within(steppers[1]!).getByText('retrieval')).toBeTruthy()
  })

  test('marks streaming toggle aria-expanded false when collapsed', () => {
    render(
      <ChatPipelineSteps
        isStreaming
        sourceCount={0}
        steps={[
          {
            detail: { limit: 3 },
            id: 'retrieval',
            status: 'start',
          },
        ]}
      />,
    )

    const toggle = screen.getByRole('button', {
      name: /Expand Chat Steps, retrieval, running/,
    })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
  })

  test('renders finished response as compact details and keeps step rows closed', async () => {
    const user = userEvent.setup()
    render(
      <ChatPipelineSteps
        isStreaming={false}
        sourceCount={2}
        steps={[
          {
            detail: { sources: 2 },
            elapsed_ms: 2400,
            id: 'answer',
            status: 'done',
            usage: {
              cost_source: 'provider_reported',
              estimated_cost_usd: 0.0012,
              input_tokens: 120,
              model: 'qwen-plus',
              output_tokens: 24,
              provider: 'qwen',
              slot: 'chat',
              total_tokens: 144,
            },
          },
        ]}
      />,
    )

    const stepper = screen.getByRole('region', { name: 'Chat Pipeline Steps' })
    expect(
      within(stepper).getByRole('button', {
        name: 'Expand Chat Steps, 2.4 s, 2 Sources',
      }),
    ).toBeTruthy()

    await user.click(
      within(stepper).getByRole('button', {
        name: 'Expand Chat Steps, 2.4 s, 2 Sources',
      }),
    )

    const usageDetails = within(stepper).getByText('Usage').closest('details')
    expect(usageDetails).not.toBeNull()
    expect(usageDetails?.hasAttribute('open')).toBe(false)
    expect(within(stepper).getAllByText('qwen-plus')).toHaveLength(1)
    await user.click(within(stepper).getByText('Usage'))
    expect(usageDetails?.hasAttribute('open')).toBe(true)
    expect(within(stepper).getByText('$0.0012')).toBeTruthy()
    expect(within(stepper).getByText('144 Tokens')).toBeTruthy()
  })

  test('keeps baseline query result and model chips outside collapsed usage without duplicating the model', async () => {
    const user = userEvent.setup()
    render(
      <ChatPipelineSteps
        isStreaming={false}
        sourceCount={0}
        steps={[
          {
            detail: {
              query: 'retrieval fidelity query',
              result_count: 7,
            },
            elapsed_ms: 1250,
            id: 'retrieval',
            status: 'done',
            usage: {
              estimated_cost_usd: 0.0025,
              input_tokens: 80,
              model: 'qwen-fidelity',
              output_tokens: 20,
              provider: 'qwen',
              slot: 'chat',
              total_tokens: 100,
            },
          },
        ]}
      />,
    )

    const stepper = screen.getByRole('region', { name: 'Chat Pipeline Steps' })
    await user.click(
      within(stepper).getByRole('button', {
        name: 'Expand Chat Steps, 1.3 s, 0 Sources',
      }),
    )

    const row = within(stepper)
      .getByText('retrieval')
      .closest('[data-slot="reasoning-trace-step"]')
    expect(row).not.toBeNull()
    const rowQueries = within(row as HTMLElement)
    expect(rowQueries.getByText('retrieval fidelity query').closest('details')).toBeNull()
    expect(rowQueries.getByText('7').closest('details')).toBeNull()
    expect(rowQueries.getAllByText('qwen-fidelity')).toHaveLength(1)
    expect(rowQueries.getByText('qwen-fidelity').closest('details')).toBeNull()

    const usageDetails = rowQueries.getByText('Usage').closest('details')
    expect(usageDetails).not.toBeNull()
    expect(usageDetails?.hasAttribute('open')).toBe(false)
    await user.click(rowQueries.getByText('Usage'))
    expect(usageDetails?.hasAttribute('open')).toBe(true)
    expect(rowQueries.getAllByText('qwen-fidelity')).toHaveLength(1)
    expect(rowQueries.getByText('$0.0025')).toBeTruthy()
  })

  test('uses tokenized slots instead of legacy pipeline classes', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <ChatPipelineSteps
        isStreaming={false}
        sourceCount={1}
        steps={[
          {
            detail: { sources: 1 },
            elapsed_ms: 900,
            id: 'retrieval',
            status: 'done',
          },
        ]}
      />,
    )

    const stepper = screen.getByRole('region', { name: 'Chat Pipeline Steps' })
    expect(stepper.getAttribute('data-slot')).toBe('reasoning-trace')

    await user.click(
      within(stepper).getByRole('button', {
        name: 'Expand Chat Steps, 900 ms, 1 Source',
      }),
    )

    expect(container.querySelector('.chat-pipeline-steps')).toBeNull()
    expect(container.querySelector('.pipeline-summary-button')).toBeNull()
    expect(container.querySelector('.pipeline-step-list')).toBeNull()
    expect(container.querySelector('.pipeline-step-row')).toBeNull()
    expect(container.querySelector('.pipeline-detail-chip')).toBeNull()
    expect(container.querySelector('[data-slot="reasoning-trace-list"]')).toBeTruthy()
    expect(container.querySelector('[data-slot="reasoning-trace-step"]')).toBeTruthy()
  })

  test('delegates stepper toggle semantics to the real ReasoningTrace pattern', () => {
    expect(chatPipelineStepsSource).toContain('ReasoningTrace')
    expect(chatPipelineStepsSource).toContain('./beautiful-ui')
    expect(chatPipelineStepsSource).not.toContain('<button')
  })
  test('pipeline summary is borderless subtle text, not a chrome button', () => {
    expect(chatPipelineStepsSource).toContain('PIPELINE_SUMMARY_TEXT_CLASS')
    expect(chatPipelineStepsSource).toContain('hover:bg-transparent')
    expect(chatPipelineStepsSource).toContain('text-muted-foreground')
    expect(chatPipelineStepsSource).toContain('toggleClassName')
  })


})
