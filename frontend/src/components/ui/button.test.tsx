/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Button, IconButton } from './button'

afterEach(() => {
  cleanup()
})

describe('Button', () => {
  test('renders the primary variant by default', () => {
    render(<Button>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button.className).toContain('bg-primary')
    expect(button.className).toContain('text-primary-foreground')
  })

  test('merges caller classes after variant classes', () => {
    render(<Button className="px-8">Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button.className).toContain('px-8')
  })
})

describe('IconButton', () => {
  test('uses the provided label as the accessible name', () => {
    render(
      <IconButton label="Open menu">
        <span aria-hidden="true">M</span>
      </IconButton>,
    )

    expect(screen.getByRole('button', { name: 'Open menu' })).toBeTruthy()
  })
})
