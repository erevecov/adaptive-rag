/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import * as Popover from './popover'

afterEach(() => {
  cleanup()
})

describe('Popover', () => {
  installPointerEventMocks()

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
    expect(trigger.className).toContain('focus-visible:ring-ring')
    expect(trigger.className).toContain('max-[680px]:min-h-11')
    expect(trigger.className).toContain('max-[680px]:rounded-sm')
    expect(trigger.className).toContain('max-[680px]:tracking-tighter')
    expect(trigger.className).toContain('hover:bg-primary/15')
    expect(trigger.className).toContain('max-[680px]:hover:bg-primary/20')
    expect(trigger.className).toContain('active:bg-primary/20')
    expect(trigger.className).toContain('max-[680px]:active:bg-primary/95')
    expect(trigger.className).toContain('motion-safe:transition-colors')
    await user.click(trigger)

    const listbox = await screen.findByRole('listbox', { name: 'Projects' })

    expect(trigger.getAttribute('data-state')).toBe('open')
    expect(listbox.getAttribute('data-slot')).toBe('popover-content')
    expect(listbox.className).toContain('focus-visible:ring-ring')
    expect(listbox.className).toContain('p-1')
    expect(listbox.className).toContain('max-[680px]:p-0.5')
    expect(listbox.className).toContain('max-[680px]:rounded-sm')
    expect(listbox.className).toContain('max-[680px]:tracking-tighter')
    expect(listbox.className).toContain('max-[680px]:shadow-primary/95')
    expect(trigger.parentElement?.contains(listbox)).toBe(false)
  })

  test('asChild trigger does not force default focus ring on the host', () => {
    render(
      <Popover.Root>
        <Popover.Trigger asChild>
          <button className="custom-trigger" type="button">
            Custom
          </button>
        </Popover.Trigger>
      </Popover.Root>,
    )

    const trigger = screen.getByRole('button', { name: 'Custom' })
    expect(trigger.className).toContain('custom-trigger')
    expect(trigger.className).not.toContain('focus-visible:ring-ring')
  })
})
