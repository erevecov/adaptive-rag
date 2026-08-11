/** @vitest-environment jsdom */

import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { OneTimePasswordDialog } from './OneTimePasswordDialog'

afterEach(cleanup)

describe('OneTimePasswordDialog', () => {
  test('copies the temporary password and closes irreversibly', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    const onClose = vi.fn()

    render(
      <OneTimePasswordDialog
        email="viewer@example.com"
        onClose={onClose}
        password="temporary-secret-value"
      />,
    )

    expect(screen.getByRole('dialog').textContent).toContain(
      'This password will not be shown again.',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Copy password' }))
    expect(writeText).toHaveBeenCalledWith('temporary-secret-value')
    expect(screen.getByRole('status').textContent).toContain('Password copied')
    await userEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
