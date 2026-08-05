/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import * as DropdownMenu from './dropdown-menu'

afterEach(() => {
  cleanup()
})

describe('DropdownMenu', () => {
  installPointerEventMocks()

  test('renders shared menu content and item slots through a Radix portal', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <DropdownMenu.Root>
        <DropdownMenu.Trigger>Open actions</DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content>
            <DropdownMenu.Item onSelect={onSelect}>Archive</DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>,
    )

    const trigger = screen.getByRole('button', { name: 'Open actions' })

    expect(trigger.getAttribute('data-state')).toBe('closed')
    await user.click(trigger)

    const menu = await screen.findByRole('menu')
    const archiveItem = screen.getByRole('menuitem', { name: 'Archive' })

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(menu.getAttribute('data-slot')).toBe('dropdown-menu-content')
    expect(archiveItem.getAttribute('data-slot')).toBe('dropdown-menu-item')
    expect(archiveItem.className).toContain('focus-visible:ring-2')
    expect(archiveItem.className).toContain('focus-visible:ring-inset')
    expect(trigger.parentElement?.contains(menu)).toBe(false)

    await user.click(archiveItem)

    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
