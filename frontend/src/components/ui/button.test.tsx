/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { type ComponentProps } from 'react'
import { afterEach, describe, expect, test } from 'vitest'

import { Button, IconButton } from './button'

function classTokens(element: Element): string[] {
  return element.className.split(/\s+/).filter(Boolean)
}

afterEach(() => {
  cleanup()
})

describe('Button', () => {
  test('renders the primary variant by default', () => {
    render(<Button>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(classTokens(button)).toContain('bg-primary')
    expect(classTokens(button)).toContain('text-primary-foreground')
    expect(button.getAttribute('data-slot')).toBe('button')
  })

  test('merges caller classes after variant classes and removes conflicts', () => {
    render(<Button className="px-8">Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    const tokens = classTokens(button)
    expect(tokens).toContain('px-8')
    expect(tokens).not.toContain('px-4')
  })

  test('keeps the stable slot marker when callers pass data attributes', () => {
    render(<Button data-slot="icon-button">Save</Button>)

    expect(screen.getByRole('button', { name: 'Save' }).getAttribute('data-slot')).toBe(
      'button',
    )
  })
})

describe('IconButton', () => {
  test('uses the provided label as the accessible name and marks its slot', () => {
    const callerProps = {
      'aria-label': 'Wrong label',
      'aria-labelledby': 'hostile-label',
      'aria-hidden': true,
      'data-slot': 'custom-icon-button',
      role: 'link',
      size: 'sm',
      tabIndex: -1,
      title: 'Wrong title',
    } as unknown as ComponentProps<typeof IconButton>

    render(
      <>
        <span id="hostile-label">Wrong menu label</span>
        <IconButton {...callerProps} className="size-12 p-4" label="Open menu">
          <span aria-hidden="true">M</span>
        </IconButton>
      </>,
    )

    const button = screen.getByRole('button', { name: 'Open menu' })
    const tokens = classTokens(button)
    expect(button.getAttribute('role')).toBeNull()
    expect(button.hasAttribute('aria-hidden')).toBe(false)
    expect(button.hasAttribute('tabindex')).toBe(false)
    expect(button.getAttribute('data-slot')).toBe('icon-button')
    expect(button.getAttribute('title')).toBe('Open menu')
    expect(tokens).toContain('size-9')
    expect(tokens).toContain('p-0')
    expect(tokens).not.toContain('size-12')
    expect(tokens).not.toContain('p-4')
    expect(tokens).not.toContain('px-3')
  })

  test('allows callers to choose the icon button variant', () => {
    render(
      <IconButton label="Delete item" variant="danger">
        <span aria-hidden="true">D</span>
      </IconButton>,
    )

    const tokens = classTokens(screen.getByRole('button', { name: 'Delete item' }))
    expect(tokens).toContain('bg-destructive')
    expect(tokens).not.toContain('bg-secondary')
  })
})
