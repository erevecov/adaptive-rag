/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { SidebarItem } from './nav'

afterEach(() => {
  cleanup()
})

describe('SidebarItem', () => {
  test('marks the active item as the current page', () => {
    render(<SidebarItem active>Projects</SidebarItem>)

    const item = screen.getByRole('button', { name: 'Projects' })
    expect(item.getAttribute('aria-current')).toBe('page')
    expect(item.getAttribute('data-active')).toBe('')
  })

  test('does not expose aria-current when inactive', () => {
    render(<SidebarItem>Projects</SidebarItem>)

    expect(
      screen.getByRole('button', { name: 'Projects' }).hasAttribute('aria-current'),
    ).toBe(false)
  })

  test('passes the disabled state to the button element', () => {
    render(<SidebarItem disabled>Projects</SidebarItem>)

    expect(
      (screen.getByRole('button', { name: 'Projects' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  test('uses type button by default', () => {
    render(<SidebarItem>Projects</SidebarItem>)

    expect(screen.getByRole('button', { name: 'Projects' }).getAttribute('type')).toBe(
      'button',
    )
  })
})
