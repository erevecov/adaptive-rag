import { describe, expect, test } from 'vitest'

import { cn } from './utils'

describe('cn', () => {
  test('combines conditional classes and resolves Tailwind conflicts', () => {
    const shouldHide = new Date(0).getTime() > 0

    const result = cn(
      'px-2 text-sm',
      shouldHide && 'hidden',
      ['px-4', 'font-medium'],
      { 'text-foreground': true },
    )

    expect(result).toBe('text-sm px-4 font-medium text-foreground')
  })
})
