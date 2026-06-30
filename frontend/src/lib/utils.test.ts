import { describe, expect, test } from 'vitest'

import { cn } from './utils'

describe('cn', () => {
  test('combines conditional classes and resolves Tailwind conflicts', () => {
    const result = cn(
      'px-2 text-sm',
      false && 'hidden',
      ['px-4', 'font-medium'],
      { 'text-foreground': true },
    )

    expect(result).toBe('text-sm px-4 font-medium text-foreground')
  })
})
