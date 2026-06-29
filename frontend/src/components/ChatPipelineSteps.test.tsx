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

  test('renders collapsed streaming ticker and persists expansion', async () => {
    const user = userEvent.setup()
    localStorage.setItem(STEPPER_EXPANDED_STORAGE_KEY, 'false')

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

  test('renders finished details with usage, cost and sources', () => {
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
    expect(within(stepper).getByText('details - 2.4 s - 2 sources')).toBeTruthy()
    expect(within(stepper).getByText('qwen-plus')).toBeTruthy()
    expect(within(stepper).getByText('$0.0012')).toBeTruthy()
    expect(within(stepper).getByText('144 tokens')).toBeTruthy()
  })
})
