/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { SegmentedControl, SegmentedControlItem } from './tabs'

afterEach(() => {
  cleanup()
})

describe('SegmentedControl', () => {
  test('defaults wrapper to group role', () => {
    render(<SegmentedControl aria-label="Runtime sections" />)

    const control = screen.getByRole('group', { name: 'Runtime sections' })
    expect(control.getAttribute('data-slot')).toBe('segmented-control')
  })

  test('marks active item with aria-pressed', () => {
    render(
      <SegmentedControl aria-label="Runtime sections">
        <SegmentedControlItem active>Connections</SegmentedControlItem>
        <SegmentedControlItem>Model Catalog</SegmentedControlItem>
      </SegmentedControl>,
    )

    expect(
      screen.getByRole('button', { name: 'Connections' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('focus-visible:ring-inset')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('data-[active]:ring-primary/30')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('data-[active]:bg-card')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('hover:bg-primary/15')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('active:bg-primary/20')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('max-[680px]:active:bg-primary/60')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('max-[680px]:min-h-11')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('max-[680px]:text-[0.5625rem]')
    expect(
      screen.getByRole('button', { name: 'Connections' }).className,
    ).toContain('max-[680px]:tracking-tighter')
    expect(
      screen.getByRole('group', { name: 'Runtime sections' }).className,
    ).toContain('bg-muted/40')
    expect(
      screen.getByRole('group', { name: 'Runtime sections' }).className,
    ).toContain('max-[680px]:rounded-sm')
    expect(
      screen.getByRole('group', { name: 'Runtime sections' }).className,
    ).toContain('max-[680px]:p-0.5')
    expect(
      screen.getByRole('group', { name: 'Runtime sections' }).className,
    ).toContain('max-[680px]:gap-0.5')
    expect(
      screen.getByRole('button', { name: 'Model Catalog' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })

  test('keeps disabled item inert', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(
      <SegmentedControl aria-label="Runtime sections">
        <SegmentedControlItem disabled onClick={handleClick}>
          Model Catalog
        </SegmentedControlItem>
      </SegmentedControl>,
    )

    const item = screen.getByRole('button', { name: 'Model Catalog' })
    expect(item.getAttribute('disabled')).toBe('')

    await user.click(item)

    expect(handleClick).not.toHaveBeenCalled()
  })

  test('uses Radix tab state for tablist controls', () => {
    render(
      <SegmentedControl aria-label="Inspector Panels" role="tablist">
        <SegmentedControlItem active role="tab" value="context">
          Context
        </SegmentedControlItem>
        <SegmentedControlItem role="tab" value="minimap">
          Minimap
        </SegmentedControlItem>
      </SegmentedControl>,
    )

    const tablist = screen.getByRole('tablist', { name: 'Inspector Panels' })
    const contextTab = screen.getByRole('tab', { name: 'Context' })
    const minimapTab = screen.getByRole('tab', { name: 'Minimap' })

    expect(tablist.getAttribute('data-orientation')).toBe('horizontal')
    expect(contextTab.getAttribute('data-state')).toBe('active')
    expect(minimapTab.getAttribute('data-state')).toBe('inactive')
  })

  test('arrow keys change tablist value via onClick compat', async () => {
    const user = userEvent.setup()
    const onContext = vi.fn()
    const onMinimap = vi.fn()

    render(
      <SegmentedControl aria-label="Inspector Panels" role="tablist">
        <SegmentedControlItem active onClick={onContext} role="tab" value="context">
          Context
        </SegmentedControlItem>
        <SegmentedControlItem onClick={onMinimap} role="tab" value="minimap">
          Minimap
        </SegmentedControlItem>
      </SegmentedControl>,
    )

    const contextTab = screen.getByRole('tab', { name: 'Context' })
    contextTab.focus()
    await user.keyboard('{ArrowRight}')
    expect(onMinimap).toHaveBeenCalled()
  })
})
