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
    expect(trigger.className).toContain('focus-visible:ring-ring')
    await user.click(trigger)

    const menu = await screen.findByRole('menu')
    const archiveItem = screen.getByRole('menuitem', { name: 'Archive' })

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(menu.getAttribute('data-slot')).toBe('dropdown-menu-content')
    expect(menu.className).toContain('focus-visible:ring-ring')
    expect(archiveItem.getAttribute('data-slot')).toBe('dropdown-menu-item')
    expect(archiveItem.className).toContain('focus-visible:ring-2')
    expect(archiveItem.className).toContain('focus-visible:ring-inset')
    expect(archiveItem.className).toContain('data-[highlighted]:bg-primary/15')
    expect(archiveItem.className).toContain('max-[680px]:min-h-11')
    expect(trigger.parentElement?.contains(menu)).toBe(false)

    await user.click(archiveItem)

    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  test('asChild trigger does not force default focus ring on the host', () => {
    render(
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button className="custom-trigger" type="button">
            Custom
          </button>
        </DropdownMenu.Trigger>
      </DropdownMenu.Root>,
    )

    const trigger = screen.getByRole('button', { name: 'Custom' })
    expect(trigger.className).toContain('custom-trigger')
    expect(trigger.className).not.toContain('focus-visible:ring-ring')
  })
})
