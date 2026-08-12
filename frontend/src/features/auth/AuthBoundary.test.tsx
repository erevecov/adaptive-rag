/** @vitest-environment jsdom */

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { ApiClient, CurrentUser } from '@/lib/apiClient'
import { AuthBoundary } from './AuthBoundary'

afterEach(cleanup)

function user(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    display_name: 'Viewer',
    email: 'viewer@example.com',
    id: '11111111-1111-4111-8111-111111111111',
    last_workspace_id: null,
    must_change_password: false,
    system_role: 'user',
    ...overrides,
  }
}

describe('AuthBoundary', () => {
  test('shows login after unauthenticated startup and enters the app', async () => {
    const login = vi.fn().mockResolvedValue(user())
    const client = {
      getCurrentUser: vi.fn().mockRejectedValue(new Error('401')),
      login,
    } as unknown as ApiClient

    render(
      <AuthBoundary client={client}>
        {(current) => <div>Welcome {current.email}</div>}
      </AuthBoundary>,
    )

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeTruthy()
    await userEvent.type(screen.getByLabelText('Email'), 'viewer@example.com')
    await userEvent.type(
      screen.getByLabelText('Password'),
      'correct horse battery staple',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Welcome viewer@example.com')).toBeTruthy()
    expect(login).toHaveBeenCalledWith({
      email: 'viewer@example.com',
      password: 'correct horse battery staple',
    })
  })

  test('blocks the application until a temporary password is changed', async () => {
    const changePassword = vi.fn().mockResolvedValue(
      user({ must_change_password: false }),
    )
    const client = {
      changePassword,
      getCurrentUser: vi.fn().mockResolvedValue(
        user({ must_change_password: true }),
      ),
    } as unknown as ApiClient

    render(
      <AuthBoundary client={client}>
        {() => <div>Protected application</div>}
      </AuthBoundary>,
    )

    expect(
      await screen.findByRole('heading', { name: 'Choose a new password' }),
    ).toBeTruthy()
    expect(screen.queryByText('Protected application')).toBeNull()
    await userEvent.type(
      screen.getByLabelText('New password'),
      'permanent correct horse password',
    )
    await userEvent.type(
      screen.getByLabelText('Confirm new password'),
      'permanent correct horse password',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Save password' }))

    await waitFor(() => expect(changePassword).toHaveBeenCalled())
    expect(await screen.findByText('Protected application')).toBeTruthy()
  })

  test('keeps the session UI when logout fails', async () => {
    const logout = vi.fn().mockRejectedValue(new Error('network'))
    const client = {
      getCurrentUser: vi.fn().mockResolvedValue(user()),
      logout,
    } as unknown as ApiClient

    render(
      <AuthBoundary client={client}>
        {(current, actions) => (
          <div>
            <div>Welcome {current.email}</div>
            <button onClick={actions.onLogout} type="button">
              Sign out
            </button>
            {actions.logoutError ? <p>{actions.logoutError}</p> : null}
          </div>
        )}
      </AuthBoundary>,
    )

    expect(await screen.findByText('Welcome viewer@example.com')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(
      await screen.findByText('Sign out failed. Please try again.'),
    ).toBeTruthy()
    expect(screen.getByText('Welcome viewer@example.com')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Sign in' })).toBeNull()
    expect(logout).toHaveBeenCalled()
  })
})
