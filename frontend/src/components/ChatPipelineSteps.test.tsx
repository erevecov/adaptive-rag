/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test } from 'vitest'

import { ChatPipelineSteps } from './ChatPipelineSteps'
import { STEPPER_EXPANDED_STORAGE_KEY } from '../lib/stepperPreference'

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
  })

  afterEach(() => {
    cleanup()
  })

  test('defaults to collapsed streaming ticker and persists expansion', async () => {
    const user = userEvent.setup()

    render(
      <ChatPipelineSteps
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

    const stepper = screen.getByRole('region', { name: 'Chat pipeline steps' })
    expect(within(stepper).getByText('retrieval')).toBeTruthy()
    expect(within(stepper).queryByText('alpha')).toBeNull()

    await user.click(
      within(stepper).getByRole('button', { name: 'Expand chat steps' }),
    )

    expect(localStorage.getItem(STEPPER_EXPANDED_STORAGE_KEY)).toBe('true')
    expect(within(stepper).getByText('alpha')).toBeTruthy()
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

    const stepper = screen.getByRole('region', { name: 'Chat pipeline steps' })
    expect(
      within(stepper).getByRole('button', {
        name: 'Expand chat steps, 2.4 s, 2 sources',
      }),
    ).toBeTruthy()

    await user.click(
      within(stepper).getByRole('button', {
        name: 'Expand chat steps, 2.4 s, 2 sources',
      }),
    )

    const answerRow = within(stepper).getByText('answer').closest('details')
    expect(answerRow).not.toBeNull()
    expect(answerRow?.hasAttribute('open')).toBe(false)
    expect(within(stepper).getAllByText('qwen-plus').length).toBeGreaterThan(0)
    expect(within(stepper).getByText('$0.0012')).toBeTruthy()
    expect(within(stepper).getByText('144 tokens')).toBeTruthy()
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

    const stepper = screen.getByRole('region', { name: 'Chat pipeline steps' })
    expect(stepper.getAttribute('data-slot')).toBe('chat-pipeline-steps')

    await user.click(
      within(stepper).getByRole('button', {
        name: 'Expand chat steps, 900 ms, 1 source',
      }),
    )

    expect(container.querySelector('.chat-pipeline-steps')).toBeNull()
    expect(container.querySelector('.pipeline-summary-button')).toBeNull()
    expect(container.querySelector('.pipeline-step-list')).toBeNull()
    expect(container.querySelector('.pipeline-step-row')).toBeNull()
    expect(container.querySelector('.pipeline-detail-chip')).toBeNull()
    expect(container.querySelector('[data-slot="chat-pipeline-step-list"]')).toBeTruthy()
    expect(container.querySelector('[data-slot="chat-pipeline-step-row"]')).toBeTruthy()
  })
})
