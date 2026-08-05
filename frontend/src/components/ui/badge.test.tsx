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
    expect(badge.className).toContain('tabular-nums')
    expect(badge.className).toContain('tracking-tight')
    expect(badge.className).toContain('shrink-0')
    expect(badge.className).toContain('max-[680px]:px-1')
    expect(badge.className).toContain('max-[680px]:py-0')
    expect(badge.className).toContain('max-[680px]:text-[0.625rem]')
    expect(badge.className).toContain('max-[680px]:tracking-tighter')
    expect(badge.className).toContain('leading-none')
  })

  test('renders destructive status badge through tokens', () => {
    render(<StatusBadge tone="danger">failed</StatusBadge>)

    const badge = screen.getByText('failed')
    expect(badge.getAttribute('data-tone')).toBe('danger')
    expect(badge.className).toContain('text-destructive')
  })

  test('primary tone uses foreground on tinted fill; success uses emerald contrast', () => {
    const { rerender } = render(<Badge tone="primary">12</Badge>)
    expect(screen.getByText('12').className).toContain('text-foreground')
    expect(screen.getByText('12').className).toContain('bg-primary/25')

    rerender(<Badge tone="success">ok</Badge>)
    expect(screen.getByText('ok').className).toContain('text-emerald-800')
    expect(screen.getByText('ok').className).toContain('dark:text-emerald-200')
    expect(screen.getByText('ok').className).toContain('bg-emerald-500/15')
  })
})
