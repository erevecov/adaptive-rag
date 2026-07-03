/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import controlSource from './control.tsx?raw'
import { Input, Textarea } from './control'

function classTokens(element: Element): string[] {
  return element.className.split(/\s+/).filter(Boolean)
}

function expectSharedControlTokens(element: Element): void {
  const tokens = classTokens(element)
  expect(tokens).toContain('w-full')
  expect(tokens).toContain('rounded-md')
  expect(tokens).toContain('border')
  expect(tokens).toContain('border-input')
  expect(tokens).toContain('bg-background')
  expect(tokens).toContain('px-3')
  expect(tokens).toContain('py-2')
  expect(tokens).toContain('text-sm')
  expect(tokens).toContain('text-foreground')
  expect(tokens).toContain('transition-colors')
  expect(tokens).toContain('placeholder:text-muted-foreground')
  expect(tokens).toContain('focus-visible:outline-none')
  expect(tokens).toContain('focus-visible:ring-2')
  expect(tokens).toContain('focus-visible:ring-ring')
  expect(tokens).toContain('focus-visible:ring-offset-2')
  expect(tokens).toContain('focus-visible:ring-offset-background')
  expect(tokens).toContain('disabled:cursor-not-allowed')
  expect(tokens).toContain('disabled:opacity-50')
}

afterEach(() => {
  cleanup()
})

describe('control primitives', () => {
  test('does not keep a native select primitive after Radix Select migration', () => {
    expect(controlSource).not.toContain('NativeSelect')
    expect(controlSource).not.toContain('<select')
  })

  test('Input uses tokenized control classes and a stable slot', () => {
    render(<Input aria-label="Connection id" className="h-12" />)

    const input = screen.getByRole('textbox', { name: 'Connection id' })
    const tokens = classTokens(input)
    expect(input.getAttribute('data-slot')).toBe('input')
    expectSharedControlTokens(input)
    expect(tokens).toContain('h-12')
    expect(tokens).not.toContain('h-9')
  })

  test('Textarea uses tokenized control classes and a stable slot', () => {
    render(<Textarea aria-label="Prompt" className="min-h-32" />)

    const textarea = screen.getByRole('textbox', { name: 'Prompt' })
    const tokens = classTokens(textarea)
    expect(textarea.getAttribute('data-slot')).toBe('textarea')
    expectSharedControlTokens(textarea)
    expect(tokens).toContain('resize-y')
    expect(tokens).toContain('min-h-32')
    expect(tokens).not.toContain('min-h-24')
  })

  test.each([
    {
      label: 'Disabled input',
      render: () => <Input aria-label="Disabled input" disabled />,
      role: 'textbox',
      slot: 'input',
    },
    {
      label: 'Disabled textarea',
      render: () => <Textarea aria-label="Disabled textarea" disabled />,
      role: 'textbox',
      slot: 'textarea',
    },
  ])('$slot exposes disabled state and disabled token classes', (control) => {
    render(control.render())

    const element = screen.getByRole(control.role, { name: control.label })
    const tokens = classTokens(element)
    expect(element.getAttribute('data-slot')).toBe(control.slot)
    expect(element.hasAttribute('disabled')).toBe(true)
    expect(tokens).toContain('disabled:cursor-not-allowed')
    expect(tokens).toContain('disabled:opacity-50')
  })
})
