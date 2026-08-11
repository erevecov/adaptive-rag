/** @vitest-environment jsdom */

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { ApiClient, Workspace } from '@/lib/apiClient'
import {
  GlobalUsersPanel,
  WorkspaceMembersPanel,
} from './UserManagementPanel'

afterEach(cleanup)

const workspace: Workspace = {
  access_role: 'admin',
  budget_config_json: null,
  can_access: true,
  created_at: '2026-08-11T00:00:00Z',
  embedding_mode: 'dense',
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Research',
  retrieval_contextualization_enabled: false,
  updated_at: '2026-08-11T00:00:00Z',
}

describe('GlobalUsersPanel', () => {
  test('creates a human user and reveals the generated password once', async () => {
    const createUser = vi.fn().mockResolvedValue({
      temporary_password: 'temporary-human-password',
      user: {
        created_at: '2026-08-11T00:00:00Z',
        display_name: 'New Viewer',
        email: 'new.viewer@example.com',
        id: '22222222-2222-4222-8222-222222222222',
        is_active: true,
        last_workspace_id: null,
        memberships: [
          {
            role: 'viewer',
            workspace_id: workspace.id,
            workspace_name: workspace.name,
          },
        ],
        must_change_password: true,
        system_role: 'user',
        updated_at: '2026-08-11T00:00:00Z',
      },
    })
    const client = {
      createUser,
      listUsers: vi.fn().mockResolvedValue({ items: [] }),
    } as unknown as ApiClient

    render(<GlobalUsersPanel client={client} workspaces={[workspace]} />)

    await screen.findByRole('heading', { name: 'Global users' })
    await userEvent.type(screen.getByLabelText('Email'), 'new.viewer@example.com')
    await userEvent.type(screen.getByLabelText('Display name'), 'New Viewer')
    await userEvent.click(screen.getByRole('button', { name: 'Create user' }))

    await waitFor(() =>
      expect(createUser).toHaveBeenCalledWith({
        display_name: 'New Viewer',
        email: 'new.viewer@example.com',
        initial_workspace_id: workspace.id,
        initial_workspace_role: 'viewer',
        system_role: 'user',
      }),
    )
    expect(screen.getByDisplayValue('temporary-human-password')).toBeTruthy()
    expect(screen.queryByLabelText(/access token/i)).toBeNull()
  })
})

describe('WorkspaceMembersPanel', () => {
  test('adds an existing user by exact email without creating an identity', async () => {
    const addWorkspaceMember = vi.fn().mockResolvedValue({
      created_at: '2026-08-11T00:00:00Z',
      display_name: 'Existing User',
      email: 'existing@example.com',
      id: '33333333-3333-4333-8333-333333333333',
      is_active: true,
      role: 'viewer',
      updated_at: '2026-08-11T00:00:00Z',
      user_id: '22222222-2222-4222-8222-222222222222',
      workspace_id: workspace.id,
    })
    const client = {
      addWorkspaceMember,
      listWorkspaceMembers: vi.fn().mockResolvedValue({ items: [] }),
    } as unknown as ApiClient

    render(<WorkspaceMembersPanel client={client} workspace={workspace} />)

    await screen.findByRole('heading', { name: 'Workspace members' })
    await userEvent.type(screen.getByLabelText('User email'), 'existing@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Add member' }))

    await waitFor(() =>
      expect(addWorkspaceMember).toHaveBeenCalledWith(workspace.id, {
        email: 'existing@example.com',
        role: 'viewer',
      }),
    )
    expect(screen.getByText('Existing User')).toBeTruthy()
    expect('createUser' in client).toBe(false)
  })
})
