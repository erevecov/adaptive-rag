/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { type ComponentProps } from 'react'
import { afterEach, describe, expect, test } from 'vitest'

import { Button, ButtonLabel, IconButton } from './button'

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

  test('primary variant uses a contrast focus ring against the fill', () => {
    render(<Button>Save</Button>)

    const tokens = classTokens(screen.getByRole('button', { name: 'Save' }))
    expect(tokens).toContain('focus-visible:ring-2')
    expect(tokens).toContain('focus-visible:ring-primary-foreground')
    expect(tokens).not.toContain('focus-visible:ring-primary-foreground/55')
    expect(tokens).toContain('motion-safe:transition-colors')
  })

  test('danger variant uses a contrast focus ring against the fill', () => {
    render(<Button variant="danger">Delete</Button>)

    const tokens = classTokens(screen.getByRole('button', { name: 'Delete' }))
    expect(tokens).toContain('focus-visible:ring-destructive-foreground')
    expect(tokens).not.toContain('focus-visible:ring-destructive-foreground/55')
  })

  test('secondary variant uses primary-tint hover for purple chrome', () => {
    render(<Button variant="secondary">Cancel</Button>)

    const tokens = classTokens(screen.getByRole('button', { name: 'Cancel' }))
    expect(tokens).toContain('hover:bg-primary/15')
    expect(tokens).toContain('max-[680px]:hover:bg-primary/60')
    expect(tokens).toContain('hover:border-primary/40')
    expect(tokens).toContain('active:bg-primary/20')
    expect(tokens).toContain('max-[680px]:active:bg-primary/95')
  })

  test('ghost variant uses primary-tint hover for purple chrome', () => {
    render(<Button variant="ghost">More</Button>)

    const tokens = classTokens(screen.getByRole('button', { name: 'More' }))
    expect(tokens).toContain('hover:bg-primary/15')
    expect(tokens).toContain('max-[680px]:hover:bg-primary/60')
    expect(tokens).toContain('active:bg-primary/20')
    expect(tokens).toContain('max-[680px]:active:bg-primary/95')
  })

  test('sizes grow to 44px touch targets at ≤680px', () => {
    render(
      <>
        <Button>Save</Button>
        <Button size="sm">Edit</Button>
        <IconButton label="More actions">
          <span aria-hidden="true">⋯</span>
        </IconButton>
      </>,
    )

    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:min-h-11',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:px-0.5',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:gap-0.5',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:rounded-sm',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:text-[0.5625rem]',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'tracking-tight',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Save' }))).toContain(
      'max-[680px]:tracking-tighter',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Edit' }))).toContain(
      'max-[680px]:min-h-11',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Edit' }))).toContain(
      'max-[680px]:px-0.5',
    )
    expect(classTokens(screen.getByRole('button', { name: 'Edit' }))).toContain(
      'max-[680px]:text-[0.5625rem]',
    )
    expect(classTokens(screen.getByRole('button', { name: 'More actions' }))).toContain(
      'max-[680px]:size-11',
    )
  })
})

describe('ButtonLabel', () => {
  test('reserves width with the longer label so busy text does not shift layout', () => {
    const { rerender } = render(
      <Button>
        <ButtonLabel busy={false} busyLabel="Creating..." idleLabel="Create" />
      </Button>,
    )

    const idle = screen.getByRole('button', { name: 'Create' })
    const reserve = idle.querySelector('[aria-hidden="true"]')
    expect(reserve?.textContent).toBe('Creating...')
    expect(reserve?.className).toMatch(/invisible/)

    rerender(
      <Button>
        <ButtonLabel busy busyLabel="Creating..." idleLabel="Create" />
      </Button>,
    )

    const busy = screen.getByRole('button', { name: 'Creating...' })
    expect(busy.querySelector('[aria-hidden="true"]')?.textContent).toBe('Creating...')
  })
})

describe('IconButton', () => {
  const hostileIconSizingClasses = [
    'size-12',
    'w-12',
    'h-12',
    'p-4',
    'px-4',
    'py-4',
    'pt-4',
    'pr-4',
    'pb-4',
    'pl-4',
    'ps-4',
    'pe-4',
    'min-h-12',
    'min-w-12',
    'max-h-12',
    'max-w-12',
    '[width:3rem]',
    '[height:3rem]',
    '[min-width:3rem]',
    '[min-height:3rem]',
    '[max-width:3rem]',
    '[max-height:3rem]',
    '[inline-size:3rem]',
    '[block-size:3rem]',
    '[min-inline-size:3rem]',
    '[min-block-size:3rem]',
    '[max-inline-size:3rem]',
    '[max-block-size:3rem]',
    '[padding:1rem]',
    '[padding-inline:1rem]',
    '[padding-block:1rem]',
    '[padding-top:1rem]',
    '[padding-right:1rem]',
    '[padding-bottom:1rem]',
    '[padding-left:1rem]',
    'hover:[width:3rem]',
    'hover:ps-4',
    'hover:pe-4',
    'hover:[padding-inline-start:1rem]',
    '[padding-inline-end:1rem]',
    '[padding-block-start:1rem]',
    '[padding-block-end:1rem]',
  ]

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
        <IconButton
          {...callerProps}
          className={`${hostileIconSizingClasses.join(' ')} rounded-full shadow-sm`}
          label="Open menu"
        >
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
    expect(tokens).toContain('rounded-full')
    expect(tokens).toContain('shadow-sm')
    for (const hostileClass of hostileIconSizingClasses) {
      expect(tokens).not.toContain(hostileClass)
    }
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
