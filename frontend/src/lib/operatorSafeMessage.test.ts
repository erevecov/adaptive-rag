import { describe, expect, test } from 'vitest'

import { operatorSafeMessage } from './operatorSafeMessage'

describe('operatorSafeMessage', () => {
  test('redacts api keys and bearer tokens', () => {
    expect(
      operatorSafeMessage('failed with sk-abcdefghijklmnop and Bearer abc.def.ghi'),
    ).toBe('failed with [redacted] and [redacted]')
  })

  test('falls back when empty', () => {
    expect(operatorSafeMessage('')).toMatch(/Request failed/)
  })
})
