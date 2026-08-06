/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import { Select } from './select'

afterEach(() => {
  cleanup()
})

describe('Select', () => {
  installPointerEventMocks()

  test('renders a Radix trigger and portals selectable options', async () => {
    const user = userEvent.setup()
    const onValueChange = vi.fn()

    render(
      <label>
        Provider
        <Select
          onValueChange={onValueChange}
          options={[
            { label: 'Select provider', value: '' },
            { label: 'qwen', value: 'qwen' },
            { label: 'fake', value: 'fake' },
          ]}
          value="qwen"
        />
      </label>,
    )

    const trigger = screen.getByRole('combobox', { name: 'Provider' })

    expect(trigger.getAttribute('data-slot')).toBe('select-trigger')
    expect(trigger.className).toContain('focus-visible:ring-ring')
    expect(trigger.className).toContain('motion-safe:transition-colors')
    expect(trigger.className).toContain('hover:border-primary/40')
    expect(trigger.className).toContain('max-[680px]:hover:border-primary/80')
    expect(trigger.className).toContain('active:border-primary/50')
    expect(trigger.className).toContain('max-[680px]:active:border-primary/95')
    expect(trigger.className).toContain('data-[state=open]:border-primary/95')
    expect(trigger.className).toContain('data-[state=open]:bg-primary/35')
    expect(trigger.className).toContain('aria-invalid:border-destructive')
    expect(trigger.className).toContain('disabled:hover:border-input')
    expect(trigger.className).toContain('max-[680px]:min-h-11')
    expect(trigger.className).toContain('max-[680px]:gap-0.5')
    expect(trigger.className).toContain('max-[680px]:leading-snug')
    expect(
      trigger.querySelector('[aria-hidden="true"]')?.className,
    ).toContain('max-[680px]:size-5')
    expect(
      trigger.querySelector('[aria-hidden="true"]')?.className,
    ).toContain('motion-safe:transition-transform')
    expect(
      trigger.querySelector('[aria-hidden="true"]')?.className,
    ).toContain('group-data-[state=open]:rotate-180')
    expect(trigger.className).toContain('group')
    expect(trigger.getAttribute('data-state')).toBe('closed')
    await user.click(trigger)

    const option = await screen.findByRole('option', { name: 'fake' })

    expect(option.className).toContain('focus-visible:ring-inset')
    expect(option.className).toContain('focus-visible:ring-ring')
    expect(option.className).toContain('data-[highlighted]:bg-primary/15')
    expect(option.className).toContain('max-[680px]:data-[highlighted]:bg-primary/30')
    expect(option.className).toContain('active:bg-primary/20')
    expect(option.className).toContain('max-[680px]:active:bg-primary/65')
    expect(option.className).toContain('max-[680px]:min-h-11')
    expect(option.className).toContain('max-[680px]:text-[0.5625rem]')
    expect(option.className).toContain('max-[680px]:tracking-tighter')
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'focus-visible:ring-ring',
    )
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'max-[680px]:rounded-sm',
    )
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'max-[680px]:p-0.5',
    )
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'max-[680px]:tracking-tighter',
    )
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'max-[680px]:shadow-primary/95',
    )
    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(option.closest('[data-slot="select-content"]')).toBeTruthy()
    expect(trigger.parentElement?.contains(option)).toBe(false)

    await user.click(option)

    expect(onValueChange).toHaveBeenCalledWith('fake')
  })
})
