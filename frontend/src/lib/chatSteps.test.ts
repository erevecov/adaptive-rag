import { describe, expect, test } from 'vitest'

import {
  applyChatStepEvent,
  formatStepDuration,
  parseChatAttachmentsFromMetadata,
  parseChatStepsFromMetadata,
  summarizeContextWindow,
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

  test('parses valid persisted attachment refs from user message metadata', () => {
    const refs = parseChatAttachmentsFromMetadata({
      attachments: [
        {
          id: 'att-1',
          filename: 'architecture.png',
          kind: 'image',
          mime: 'image/png',
        },
        {
          id: 'att-2',
          filename: 'notes.md',
          kind: 'document',
          mime: 'text/markdown',
        },
      ],
    })

    expect(refs).toEqual([
      {
        id: 'att-1',
        filename: 'architecture.png',
        kind: 'image',
        mime: 'image/png',
      },
      {
        id: 'att-2',
        filename: 'notes.md',
        kind: 'document',
        mime: 'text/markdown',
      },
    ])
  })

  test('returns no attachment refs when metadata is missing or not a list', () => {
    expect(parseChatAttachmentsFromMetadata(null)).toEqual([])
    expect(parseChatAttachmentsFromMetadata({})).toEqual([])
    expect(parseChatAttachmentsFromMetadata({ attachments: 'nope' })).toEqual([])
    expect(parseChatAttachmentsFromMetadata({ attachments: [] })).toEqual([])
  })

  test('drops malformed attachment refs and keeps valid ones', () => {
    const refs = parseChatAttachmentsFromMetadata({
      attachments: [
        { id: 'att-1', filename: 'ok.pdf', kind: 'document', mime: 'application/pdf' },
        { id: '', filename: 'no-id.png', kind: 'image', mime: 'image/png' },
        { id: 'att-2', kind: 'image', mime: 'image/png' },
        { id: 'att-3', filename: 'no-kind.png', mime: 'image/png' },
        { id: 'att-4', filename: 'no-mime.png', kind: 'image' },
        { id: 'att-5', filename: 42, kind: 'document', mime: 'text/plain' },
        'not a ref',
      ],
    })

    expect(refs).toEqual([
      { id: 'att-1', filename: 'ok.pdf', kind: 'document', mime: 'application/pdf' },
    ])
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

  test('summarizes context window packing from the context step', () => {
    expect(
      summarizeContextWindow([
        {
          id: 'context',
          status: 'done',
          detail: {
            total_messages: 22,
            kept_recent: 8,
            summarized_messages: 14,
            summary: 'Pinned facts full text for expand',
            summary_preview: 'Pinned facts…',
          },
        },
      ]),
    ).toEqual({
      keptRecent: 8,
      label: '8 recent + 14 summarized',
      summaryFull: 'Pinned facts full text for expand',
      summaryPreview: 'Pinned facts…',
      summarizedMessages: 14,
      totalMessages: 22,
    })
    expect(summarizeContextWindow([])).toBeNull()
  })

  test('falls back summaryFull to summary_preview when full summary missing', () => {
    expect(
      summarizeContextWindow([
        {
          id: 'context',
          status: 'done',
          detail: {
            total_messages: 10,
            kept_recent: 4,
            summarized_messages: 6,
            summary_preview: 'Legacy preview only',
          },
        },
      ])?.summaryFull,
    ).toBe('Legacy preview only')
  })
})
