/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import { Select } from './select'

installPointerEventMocks()

afterEach(() => {
  cleanup()
})

describe('Select', () => {
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
    expect(trigger.getAttribute('data-state')).toBe('closed')
    await user.click(trigger)

    const option = await screen.findByRole('option', { name: 'fake' })

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(option.closest('[data-slot="select-content"]')).toBeTruthy()
    expect(trigger.parentElement?.contains(option)).toBe(false)

    await user.click(option)

    expect(onValueChange).toHaveBeenCalledWith('fake')
  })
})
