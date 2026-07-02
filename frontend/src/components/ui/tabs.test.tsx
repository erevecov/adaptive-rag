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
        <SegmentedControlItem>Model catalog</SegmentedControlItem>
      </SegmentedControl>,
    )

    expect(
      screen.getByRole('button', { name: 'Connections' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: 'Model catalog' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })

  test('keeps disabled item inert', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(
      <SegmentedControl aria-label="Runtime sections">
        <SegmentedControlItem disabled onClick={handleClick}>
          Model catalog
        </SegmentedControlItem>
      </SegmentedControl>,
    )

    const item = screen.getByRole('button', { name: 'Model catalog' })
    expect(item.getAttribute('disabled')).toBe('')

    await user.click(item)

    expect(handleClick).not.toHaveBeenCalled()
  })
})
