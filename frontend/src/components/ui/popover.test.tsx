/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import * as Popover from './popover'

installPointerEventMocks()

afterEach(() => {
  cleanup()
})

describe('Popover', () => {
  test('renders shared popover content through a Radix portal', async () => {
    const user = userEvent.setup()

    render(
      <Popover.Root>
        <Popover.Trigger>Open projects</Popover.Trigger>
        <Popover.Portal>
          <Popover.Content aria-label="Projects" role="listbox">
            <button role="option" type="button">
              Demo
            </button>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>,
    )

    const trigger = screen.getByRole('button', { name: 'Open projects' })

    expect(trigger.getAttribute('data-state')).toBe('closed')
    await user.click(trigger)

    const listbox = await screen.findByRole('listbox', { name: 'Projects' })

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(listbox.getAttribute('data-slot')).toBe('popover-content')
    expect(trigger.parentElement?.contains(listbox)).toBe(false)
  })
})
