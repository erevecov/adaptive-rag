/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { NavSection, SidebarItem } from './nav'

afterEach(() => {
  cleanup()
})

describe('NavSection', () => {
  test('renders compact uppercase section titles', () => {
    render(<NavSection title="Activos">child</NavSection>)

    const title = screen.getByRole('heading', { name: 'Activos' })
    expect(title.getAttribute('data-slot')).toBe('nav-section-title')
    expect(title.className).toContain('uppercase')
    expect(title.className).toContain('tracking-wide')
    expect(title.className).toContain('font-semibold')
  })
})

describe('SidebarItem', () => {
  test('marks the active item as the current page', () => {
    render(<SidebarItem active>Projects</SidebarItem>)

    const item = screen.getByRole('button', { name: 'Projects' })
    expect(item.getAttribute('aria-current')).toBe('page')
    expect(item.getAttribute('data-active')).toBe('')
    expect(item.className).toContain('data-[active]:bg-primary/10')
    expect(item.className).toContain('data-[active]:text-foreground')
    expect(item.className).toContain('max-[680px]:min-h-11')
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
