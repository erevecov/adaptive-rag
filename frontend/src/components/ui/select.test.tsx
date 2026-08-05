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
    expect(trigger.className).toContain('aria-invalid:border-destructive')
    expect(trigger.className).toContain('max-[680px]:min-h-11')
    expect(trigger.getAttribute('data-state')).toBe('closed')
    await user.click(trigger)

    const option = await screen.findByRole('option', { name: 'fake' })

    expect(option.className).toContain('focus-visible:ring-inset')
    expect(option.className).toContain('focus-visible:ring-ring')
    expect(option.className).toContain('data-[highlighted]:bg-primary/15')
    expect(option.className).toContain('max-[680px]:min-h-11')
    expect(option.closest('[data-slot="select-content"]')?.className).toContain(
      'focus-visible:ring-ring',
    )
    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(option.closest('[data-slot="select-content"]')).toBeTruthy()
    expect(trigger.parentElement?.contains(option)).toBe(false)

    await user.click(option)

    expect(onValueChange).toHaveBeenCalledWith('fake')
  })
})
