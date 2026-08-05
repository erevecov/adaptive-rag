/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useRef } from 'react'
import { afterEach, describe, expect, test } from 'vitest'

import { listFocusable, useFocusTrap } from './focusTrap'

afterEach(() => {
  cleanup()
})

function TrapDemo({ active }: { active: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useFocusTrap(ref, active)
  return (
    <div>
      <button type="button">Outside</button>
      <div aria-label="trap" ref={ref} role="dialog" tabIndex={-1}>
        <button type="button">First</button>
        <button type="button">Second</button>
      </div>
    </div>
  )
}

describe('focusTrap', () => {
  test('listFocusable skips inert and aria-hidden subtrees', () => {
    const root = document.createElement('div')
    root.innerHTML = `
      <button>A</button>
      <div inert><button>B</button></div>
      <div aria-hidden="true"><button>C</button></div>
      <button>D</button>
    `
    document.body.appendChild(root)
    const names = listFocusable(root).map((el) => el.textContent)
    expect(names).toEqual(['A', 'D'])
    root.remove()
  })

  test('Tab cycles inside the active trap', async () => {
    const user = userEvent.setup()
    render(<TrapDemo active />)

    const first = screen.getByRole('button', { name: 'First' })
    const second = screen.getByRole('button', { name: 'Second' })
    expect(document.activeElement).toBe(first)

    await user.tab()
    expect(document.activeElement).toBe(second)
    await user.tab()
    expect(document.activeElement).toBe(first)
    await user.tab({ shift: true })
    expect(document.activeElement).toBe(second)
  })
})
