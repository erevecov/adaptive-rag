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
  expect(tokens).toContain('tracking-tight')
  expect(tokens).toContain('text-foreground')
  expect(tokens).toContain('motion-safe:transition-colors')
  expect(tokens).toContain('placeholder:text-muted-foreground')
  expect(tokens).toContain('hover:border-primary/40')
  expect(tokens).toContain('max-[680px]:hover:border-primary/55')
  expect(tokens).toContain('active:border-primary/50')
  expect(tokens).toContain('max-[680px]:active:border-primary/70')
  expect(tokens).toContain('focus-visible:outline-none')
  expect(tokens).toContain('focus-visible:ring-2')
  expect(tokens).toContain('focus-visible:ring-ring')
  expect(tokens).toContain('focus-visible:ring-offset-2')
  expect(tokens).toContain('focus-visible:ring-offset-background')
  expect(tokens).toContain('disabled:cursor-not-allowed')
  expect(tokens).toContain('disabled:opacity-50')
  expect(tokens).toContain('disabled:hover:border-input')
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

  test('Input grows to 44px touch height at ≤680px', () => {
    render(<Input aria-label="Project id" />)

    expect(
      classTokens(screen.getByRole('textbox', { name: 'Project id' })),
    ).toContain('max-[680px]:min-h-11')
  })

  test('Input marks invalid fields with destructive border and focus ring', () => {
    render(<Input aria-invalid="true" aria-label="Broken field" />)

    const tokens = classTokens(screen.getByRole('textbox', { name: 'Broken field' }))
    expect(tokens).toContain('aria-invalid:border-destructive')
    expect(tokens).toContain('aria-invalid:hover:border-destructive')
    expect(tokens).toContain('aria-invalid:focus-visible:ring-destructive')
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
    expect(tokens).toContain('max-[680px]:min-h-28')
    expect(tokens).toContain('max-[680px]:px-0.5')
    expect(tokens).toContain('max-[680px]:border-primary/95')
    expect(tokens).toContain('max-[680px]:py-0.5')
    expect(tokens).toContain('max-[680px]:text-base')
    expect(tokens).toContain('max-[680px]:leading-snug')
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
    expect(tokens).toContain('disabled:hover:border-input')
  })
})
