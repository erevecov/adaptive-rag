import { describe, expect, test } from 'vitest'

import {
  applyChatStepEvent,
  formatStepDuration,
  parseChatStepsFromMetadata,
  summarizeCurrentStep,
  type ChatStepEvent,
} from './chatSteps'

describe('chatSteps', () => {
  test('applies start and terminal events to the latest matching running step', () => {
    const started: ChatStepEvent = {
      detail: { limit: 3, query: 'alpha' },
      id: 'retrieval',
      status: 'start',
    }
    const completed: ChatStepEvent = {
      detail: { limit: 3, query: 'alpha', result_count: 2 },
      elapsed_ms: 420,
      id: 'retrieval',
      status: 'done',
    }

    const steps = applyChatStepEvent(applyChatStepEvent([], started), completed)

    expect(steps).toEqual([
      {
        detail: { limit: 3, query: 'alpha', result_count: 2 },
        elapsed_ms: 420,
        id: 'retrieval',
        status: 'done',
      },
    ])
  })

  test('parses valid persisted metadata steps and drops malformed items', () => {
    const steps = parseChatStepsFromMetadata({
      steps: [
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
        { id: '', status: 'done' },
        { id: 'retrieval', status: 'unknown' },
        'not a step',
      ],
    })

    expect(steps).toHaveLength(1)
    expect(steps[0].id).toBe('answer')
    expect(steps[0].usage?.model).toBe('qwen-plus')
  })

  test('formats duration and current ticker labels without inventing values', () => {
    expect(formatStepDuration(2400)).toBe('2.4 s')
    expect(formatStepDuration(null)).toBe('running')

    expect(
      summarizeCurrentStep([
        { id: 'answer', status: 'done', elapsed_ms: 1000 },
        { id: 'retrieval', status: 'start' },
      ]),
    ).toEqual({
      elapsed: 'running',
      label: 'retrieval',
      status: 'start',
    })
  })
})
