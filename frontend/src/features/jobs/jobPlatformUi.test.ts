import { describe, expect, test } from 'vitest'

import {
  decodeJobFilters,
  encodeJobFilters,
  jobActions,
  jobStatusLabel,
  jobStatusTone,
} from './jobPlatformUi'

describe('job platform URL filters', () => {
  test('encodes and decodes stable job filters', () => {
    const query = encodeJobFilters({
      cursor: null,
      queue: 'system',
      status: 'dead_letter',
    })

    expect(query).toBe('status=dead_letter&queue=system')
    expect(decodeJobFilters(query)).toEqual({
      cursor: null,
      job_type: null,
      limit: null,
      queue: 'system',
      status: 'dead_letter',
    })
  })
})

describe('job platform status guards', () => {
  test('only actionable states expose their authorized operations', () => {
    expect(jobActions('blocked', true)).toEqual(['unblock', 'cancel'])
    expect(jobActions('dead_letter', true)).toEqual(['retry'])
    expect(jobActions('running', false)).toEqual([])
    expect(jobActions('unknown-state', true)).toEqual([])
  })

  test('unknown statuses stay neutral and readable', () => {
    expect(jobStatusTone('unknown-state')).toBe('neutral')
    expect(jobStatusLabel('dead_letter')).toBe('Dead letter')
    expect(jobStatusLabel('unknown-state')).toBe('Unknown state')
  })
})
