import { type FormEvent, useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import { Select } from '@/components/ui/select'
import type {
  AdminUser,
  ApiClient,
  SystemRole,
  Workspace,
  WorkspaceMember,
  WorkspaceRole,
} from '@/lib/apiClient'
import { OneTimePasswordDialog } from './OneTimePasswordDialog'

const WORKSPACE_ROLE_OPTIONS = [
  { label: 'Viewer', value: 'viewer' },
  { label: 'Contributor', value: 'contributor' },
  { label: 'Admin', value: 'admin' },
] as const

const SYSTEM_ROLE_OPTIONS = [
  { label: 'Workspace user', value: 'user' },
  { label: 'Global superadmin', value: 'superadmin' },
] as const

type OneTimePassword = { email: string; password: string }

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message
  return 'The request could not be completed.'
}

function StatusMessage({ error, loading }: { error: string | null; loading: boolean }) {
  if (error !== null) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {error}
      </p>
    )
  }
  if (loading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    )
  }
  return null
}

export function GlobalUsersPanel({
  client,
  workspaces,
}: {
  client: ApiClient
  workspaces: Workspace[]
}) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [busyUserId, setBusyUserId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'all' | 'active' | 'suspended'>('all')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [systemRole, setSystemRole] = useState<SystemRole>('user')
  const [workspaceId, setWorkspaceId] = useState(workspaces[0]?.id ?? '')
  const [workspaceRole, setWorkspaceRole] =
    useState<WorkspaceRole>('viewer')
  const [oneTimePassword, setOneTimePassword] =
    useState<OneTimePassword | null>(null)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)
  const [editEmail, setEditEmail] = useState('')
  const [editDisplayName, setEditDisplayName] = useState('')
  const [editSystemRole, setEditSystemRole] = useState<SystemRole>('user')
  const selectedWorkspaceId = workspaceId || workspaces[0]?.id || ''

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const response = await client.listUsers()
      setUsers(response.items)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let canceled = false
    void client
      .listUsers()
      .then((response) => {
        if (!canceled) setUsers(response.items)
      })
      .catch((requestError: unknown) => {
        if (!canceled) setError(errorMessage(requestError))
      })
      .finally(() => {
        if (!canceled) setLoading(false)
      })
    return () => {
      canceled = true
    }
  }, [client])

  const visibleUsers = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return users.filter((user) => {
      if (status === 'active' && !user.is_active) return false
      if (status === 'suspended' && user.is_active) return false
      return (
        needle === '' ||
        user.email.toLocaleLowerCase().includes(needle) ||
        user.display_name.toLocaleLowerCase().includes(needle)
      )
    })
  }, [query, status, users])

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setBusyUserId('create')
    try {
      const result = await client.createUser({
        display_name: displayName.trim(),
        email: email.trim(),
        ...(systemRole === 'user'
          ? {
              initial_workspace_id: selectedWorkspaceId,
              initial_workspace_role: workspaceRole,
            }
          : {}),
        system_role: systemRole,
      })
      setUsers((current) => [result.user, ...current])
      setOneTimePassword({
        email: result.user.email,
        password: result.temporary_password,
      })
      setEmail('')
      setDisplayName('')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  function beginEdit(user: AdminUser) {
    setEditingUserId(user.id)
    setEditEmail(user.email)
    setEditDisplayName(user.display_name)
    setEditSystemRole(user.system_role as SystemRole)
  }

  async function saveEdit(event: FormEvent<HTMLFormElement>, userId: string) {
    event.preventDefault()
    setError(null)
    setBusyUserId(userId)
    try {
      const updated = await client.updateUser(userId, {
        display_name: editDisplayName.trim(),
        email: editEmail.trim(),
        system_role: editSystemRole,
      })
      setUsers((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
      setEditingUserId(null)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  async function toggleSuspension(user: AdminUser) {
    if (
      user.is_active &&
      !window.confirm(`Suspend ${user.email}? All human sessions will be revoked.`)
    ) {
      return
    }
    setError(null)
    setBusyUserId(user.id)
    try {
      const updated = user.is_active
        ? await client.suspendUser(user.id)
        : await client.reactivateUser(user.id)
      setUsers((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  async function resetPassword(user: AdminUser) {
    if (!window.confirm(`Reset the password for ${user.email}?`)) return
    setError(null)
    setBusyUserId(user.id)
    try {
      const result = await client.resetUserPassword(user.id)
      setUsers((current) =>
        current.map((item) =>
          item.id === result.user.id ? result.user : item,
        ),
      )
      setOneTimePassword({
        email: result.user.email,
        password: result.temporary_password,
      })
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  return (
    <div className="grid gap-4">
      <Panel>
        <PanelHeader>
          <PanelTitle>Global users</PanelTitle>
          <PanelDescription>
            Create human identities and manage global access. Workspace users
            start with one membership; superadmins have global access.
          </PanelDescription>
        </PanelHeader>
        <PanelBody className="grid gap-4">
          <form className="grid gap-3 md:grid-cols-2" onSubmit={createUser}>
            <label className="grid gap-1 text-sm font-medium">
              Email
              <Input
                autoComplete="off"
                onChange={(event) => setEmail(event.currentTarget.value)}
                required
                type="email"
                value={email}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Display name
              <Input
                autoComplete="off"
                onChange={(event) => setDisplayName(event.currentTarget.value)}
                required
                value={displayName}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Global role
              <Select
                aria-label="Global role"
                onValueChange={(value) => setSystemRole(value as SystemRole)}
                options={SYSTEM_ROLE_OPTIONS}
                value={systemRole}
              />
            </label>
            {systemRole === 'user' ? (
              <>
                <label className="grid gap-1 text-sm font-medium">
                  Initial workspace
                  <Select
                    aria-label="Initial workspace"
                    onValueChange={setWorkspaceId}
                    options={workspaces.map((workspace) => ({
                      label: workspace.name,
                      value: workspace.id,
                    }))}
                    placeholder="Select a workspace"
                    value={selectedWorkspaceId}
                  />
                </label>
                <label className="grid gap-1 text-sm font-medium">
                  Initial workspace role
                  <Select
                    aria-label="Initial workspace role"
                    onValueChange={(value) =>
                      setWorkspaceRole(value as WorkspaceRole)
                    }
                    options={WORKSPACE_ROLE_OPTIONS}
                    value={workspaceRole}
                  />
                </label>
              </>
            ) : null}
            <div className="flex items-end gap-2">
              <Button
                disabled={
                  busyUserId !== null ||
                  email.trim() === '' ||
                  displayName.trim() === '' ||
                  (systemRole === 'user' && selectedWorkspaceId === '')
                }
                type="submit"
              >
                {busyUserId === 'create' ? 'Creating…' : 'Create user'}
              </Button>
              <Button
                disabled={loading || busyUserId !== null}
                onClick={() => void refresh()}
                type="button"
                variant="secondary"
              >
                Refresh
              </Button>
            </div>
          </form>
          <StatusMessage error={error} loading={loading} />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader>
          <PanelTitle>User directory</PanelTitle>
          <PanelDescription>
            Suspension is reversible and retains workspace memberships.
          </PanelDescription>
        </PanelHeader>
        <PanelBody className="grid gap-3">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-sm font-medium">
              Search
              <Input
                onChange={(event) => setQuery(event.currentTarget.value)}
                placeholder="Email or display name"
                type="search"
                value={query}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Status
              <Select
                aria-label="Status"
                onValueChange={(value) =>
                  setStatus(value as 'all' | 'active' | 'suspended')
                }
                options={[
                  { label: 'All', value: 'all' },
                  { label: 'Active', value: 'active' },
                  { label: 'Suspended', value: 'suspended' },
                ]}
                value={status}
              />
            </label>
          </div>
          {!loading && visibleUsers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No users found.</p>
          ) : null}
          <div className="grid gap-3">
            {visibleUsers.map((user) => (
              <article
                className="grid gap-3 rounded-md border border-border p-3"
                key={user.id}
              >
                {editingUserId === user.id ? (
                  <form
                    className="grid gap-3 md:grid-cols-3"
                    onSubmit={(event) => void saveEdit(event, user.id)}
                  >
                    <label className="grid gap-1 text-sm font-medium">
                      Email
                      <Input
                        onChange={(event) => setEditEmail(event.currentTarget.value)}
                        required
                        type="email"
                        value={editEmail}
                      />
                    </label>
                    <label className="grid gap-1 text-sm font-medium">
                      Display name
                      <Input
                        onChange={(event) =>
                          setEditDisplayName(event.currentTarget.value)
                        }
                        required
                        value={editDisplayName}
                      />
                    </label>
                    <label className="grid gap-1 text-sm font-medium">
                      Global role
                      <Select
                        aria-label={`Global role for ${user.email}`}
                        onValueChange={(value) =>
                          setEditSystemRole(value as SystemRole)
                        }
                        options={SYSTEM_ROLE_OPTIONS}
                        value={editSystemRole}
                      />
                    </label>
                    <div className="flex gap-2 md:col-span-3">
                      <Button disabled={busyUserId === user.id} type="submit">
                        Save
                      </Button>
                      <Button
                        onClick={() => setEditingUserId(null)}
                        type="button"
                        variant="secondary"
                      >
                        Cancel
                      </Button>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold">{user.display_name}</h4>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      <div className="text-right text-xs text-muted-foreground">
                        <div>{user.system_role}</div>
                        <div>{user.is_active ? 'Active' : 'Suspended'}</div>
                        {user.must_change_password ? (
                          <div>Password change required</div>
                        ) : null}
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {user.memberships.length === 0
                        ? 'No workspace memberships.'
                        : user.memberships
                            .map(
                              (membership) =>
                                `${membership.workspace_name}: ${membership.role}`,
                            )
                            .join(' · ')}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        disabled={busyUserId !== null}
                        onClick={() => beginEdit(user)}
                        type="button"
                        variant="secondary"
                      >
                        Edit
                      </Button>
                      <Button
                        disabled={busyUserId !== null}
                        onClick={() => void resetPassword(user)}
                        type="button"
                        variant="secondary"
                      >
                        Reset password
                      </Button>
                      <Button
                        disabled={busyUserId !== null}
                        onClick={() => void toggleSuspension(user)}
                        type="button"
                        variant={user.is_active ? 'danger' : 'secondary'}
                      >
                        {user.is_active ? 'Suspend' : 'Reactivate'}
                      </Button>
                    </div>
                  </>
                )}
              </article>
            ))}
          </div>
        </PanelBody>
      </Panel>

      {oneTimePassword !== null ? (
        <OneTimePasswordDialog
          email={oneTimePassword.email}
          onClose={() => setOneTimePassword(null)}
          password={oneTimePassword.password}
        />
      ) : null}
    </div>
  )
}

export function WorkspaceMembersPanel({
  client,
  workspace,
}: {
  client: ApiClient
  workspace: Workspace
}) {
  const [members, setMembers] = useState<WorkspaceMember[]>([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<WorkspaceRole>('viewer')
  const [roleDrafts, setRoleDrafts] = useState<Record<string, WorkspaceRole>>({})
  const [loading, setLoading] = useState(true)
  const [busyUserId, setBusyUserId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let canceled = false
    void client
      .listWorkspaceMembers(workspace.id)
      .then((response) => {
        if (canceled) return
        setMembers(response.items)
        setRoleDrafts(
          Object.fromEntries(
            response.items.map((member) => [member.user_id, member.role]),
          ),
        )
      })
      .catch((requestError: unknown) => {
        if (!canceled) setError(errorMessage(requestError))
      })
      .finally(() => {
        if (!canceled) setLoading(false)
      })
    return () => {
      canceled = true
    }
  }, [client, workspace.id])

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setBusyUserId('add')
    try {
      const member = await client.addWorkspaceMember(workspace.id, {
        email: email.trim(),
        role,
      })
      setMembers((current) => [...current, member])
      setRoleDrafts((current) => ({ ...current, [member.user_id]: member.role }))
      setEmail('')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  async function saveRole(member: WorkspaceMember) {
    const nextRole = roleDrafts[member.user_id] ?? member.role
    setError(null)
    setBusyUserId(member.user_id)
    try {
      const updated = await client.updateWorkspaceMember(
        workspace.id,
        member.user_id,
        { role: nextRole },
      )
      setMembers((current) =>
        current.map((item) =>
          item.user_id === updated.user_id ? updated : item,
        ),
      )
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  async function removeMember(member: WorkspaceMember) {
    if (!window.confirm(`Remove ${member.email} from ${workspace.name}?`)) return
    setError(null)
    setBusyUserId(member.user_id)
    try {
      await client.removeWorkspaceMember(workspace.id, member.user_id)
      setMembers((current) =>
        current.filter((item) => item.user_id !== member.user_id),
      )
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusyUserId(null)
    }
  }

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>Workspace members</PanelTitle>
        <PanelDescription>
          Manage access to {workspace.name}. Users must already exist in the
          global directory; roles apply only to this workspace.
        </PanelDescription>
      </PanelHeader>
      <PanelBody className="grid gap-4">
        <form className="grid gap-3 md:grid-cols-[1fr_14rem_auto]" onSubmit={addMember}>
          <label className="grid gap-1 text-sm font-medium">
            User email
            <Input
              autoComplete="off"
              onChange={(event) => setEmail(event.currentTarget.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Workspace role
            <Select
              aria-label="Workspace role"
              onValueChange={(value) => setRole(value as WorkspaceRole)}
              options={WORKSPACE_ROLE_OPTIONS}
              value={role}
            />
          </label>
          <div className="flex items-end">
            <Button
              disabled={busyUserId !== null || email.trim() === ''}
              type="submit"
            >
              {busyUserId === 'add' ? 'Adding…' : 'Add member'}
            </Button>
          </div>
        </form>
        <StatusMessage error={error} loading={loading} />
        {!loading && members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No members yet.</p>
        ) : null}
        <div className="grid gap-3">
          {members.map((member) => (
            <article
              className="grid gap-3 rounded-md border border-border p-3 md:grid-cols-[1fr_14rem_auto] md:items-end"
              key={member.user_id}
            >
              <div>
                <h4 className="font-semibold">{member.display_name}</h4>
                <p className="text-sm text-muted-foreground">{member.email}</p>
                {!member.is_active ? (
                  <p className="text-xs text-destructive">Suspended globally</p>
                ) : null}
              </div>
              <label className="grid gap-1 text-sm font-medium">
                Role for {member.email}
                <Select
                  aria-label={`Role for ${member.email}`}
                  disabled={!member.is_active}
                  onValueChange={(value) =>
                    setRoleDrafts((current) => ({
                      ...current,
                      [member.user_id]: value as WorkspaceRole,
                    }))
                  }
                  options={WORKSPACE_ROLE_OPTIONS}
                  value={roleDrafts[member.user_id] ?? member.role}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={
                    busyUserId !== null ||
                    !member.is_active ||
                    (roleDrafts[member.user_id] ?? member.role) === member.role
                  }
                  onClick={() => void saveRole(member)}
                  type="button"
                >
                  Save role
                </Button>
                <Button
                  disabled={busyUserId !== null}
                  onClick={() => void removeMember(member)}
                  type="button"
                  variant="danger"
                >
                  Remove
                </Button>
              </div>
            </article>
          ))}
        </div>
      </PanelBody>
    </Panel>
  )
}
