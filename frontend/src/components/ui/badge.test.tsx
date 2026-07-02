/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Badge, StatusBadge } from './badge'

afterEach(() => {
  cleanup()
})

describe('Badge', () => {
  test('renders neutral badge with stable slot', () => {
    render(<Badge>chat</Badge>)

    const badge = screen.getByText('chat')
    expect(badge.getAttribute('data-slot')).toBe('badge')
    expect(badge.className).toContain('border-border')
  })

  test('renders destructive status badge through tokens', () => {
    render(<StatusBadge tone="danger">failed</StatusBadge>)

    const badge = screen.getByText('failed')
    expect(badge.getAttribute('data-tone')).toBe('danger')
    expect(badge.className).toContain('text-destructive')
  })
})
