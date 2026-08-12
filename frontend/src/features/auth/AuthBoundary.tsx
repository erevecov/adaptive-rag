import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useState,
} from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import type { ApiClient, CurrentUser } from '@/lib/apiClient'

export type AuthSessionActions = {
  logoutBusy: boolean
  logoutError: string | null
  onLogout(): void
}

type AuthBoundaryProps = {
  children(currentUser: CurrentUser, actions: AuthSessionActions): ReactNode
  client: ApiClient
  initialCurrentUser?: CurrentUser
}

export function AuthBoundary({
  children,
  client,
  initialCurrentUser,
}: AuthBoundaryProps) {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(
    initialCurrentUser ?? null,
  )
  const [state, setState] = useState<'loading' | 'anonymous' | 'authenticated'>(
    initialCurrentUser === undefined ? 'loading' : 'authenticated',
  )
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialCurrentUser !== undefined) return
    let ignore = false
    void client
      .getCurrentUser()
      .then((user) => {
        if (ignore) return
        setCurrentUser(user)
        setState('authenticated')
      })
      .catch(() => {
        if (!ignore) setState('anonymous')
      })
    return () => {
      ignore = true
    }
  }, [client, initialCurrentUser])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const user = await client.login({ email: email.trim(), password })
      setPassword('')
      setCurrentUser(user)
      setState('authenticated')
    } catch {
      setError('The email or password is incorrect.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (newPassword.length < 15) {
      setError('Use at least 15 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('The passwords do not match.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const user = await client.changePassword({ new_password: newPassword })
      setNewPassword('')
      setConfirmPassword('')
      setCurrentUser(user)
    } catch {
      setError('The password could not be changed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleLogout() {
    setSubmitting(true)
    setError(null)
    try {
      await client.logout()
      setCurrentUser(null)
      setState('anonymous')
    } catch {
      // Fail closed: keep the authenticated UI until the server revokes the session.
      setError('Sign out failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (state === 'loading') {
    return (
      <main className="grid min-h-screen place-items-center bg-background p-6">
        <p aria-live="polite" className="text-sm text-muted-foreground">
          Loading session…
        </p>
      </main>
    )
  }

  if (state === 'anonymous' || currentUser === null) {
    return (
      <AuthCard description="Use your Adaptive RAG account." title="Sign in">
        <form className="grid gap-4" onSubmit={handleLogin}>
          <label className="grid gap-1 text-sm font-medium" htmlFor="auth-email">
            Email
            <Input
              autoComplete="email"
              id="auth-email"
              onChange={(event) => setEmail(event.currentTarget.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label
            className="grid gap-1 text-sm font-medium"
            htmlFor="auth-password"
          >
            Password
            <Input
              autoComplete="current-password"
              id="auth-password"
              onChange={(event) => setPassword(event.currentTarget.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <AuthError error={error} />
          <Button disabled={submitting} type="submit">
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </AuthCard>
    )
  }

  if (currentUser.must_change_password) {
    return (
      <AuthCard
        description="Your temporary password can only be used to choose a permanent one."
        title="Choose a new password"
      >
        <form className="grid gap-4" onSubmit={handlePasswordChange}>
          <label
            className="grid gap-1 text-sm font-medium"
            htmlFor="auth-new-password"
          >
            New password
            <Input
              autoComplete="new-password"
              id="auth-new-password"
              onChange={(event) => setNewPassword(event.currentTarget.value)}
              required
              type="password"
              value={newPassword}
            />
          </label>
          <label
            className="grid gap-1 text-sm font-medium"
            htmlFor="auth-confirm-password"
          >
            Confirm new password
            <Input
              autoComplete="new-password"
              id="auth-confirm-password"
              onChange={(event) => setConfirmPassword(event.currentTarget.value)}
              required
              type="password"
              value={confirmPassword}
            />
          </label>
          <AuthError error={error} />
          <div className="flex gap-2">
            <Button disabled={submitting} type="submit">
              {submitting ? 'Saving…' : 'Save password'}
            </Button>
            <Button
              disabled={submitting}
              onClick={() => void handleLogout()}
              type="button"
              variant="secondary"
            >
              Sign out
            </Button>
          </div>
        </form>
      </AuthCard>
    )
  }

  // h-full keeps the app-shell viewport lock (#root → shell) intact. Do not use
  // min-h-screen here: it breaks h-full descendants and clips the chat layout.
  return (
    <div className="h-full min-h-0">
      {children(currentUser, {
        logoutBusy: submitting,
        logoutError: error,
        onLogout: () => {
          void handleLogout()
        },
      })}
    </div>
  )
}

function AuthCard({
  children,
  description,
  title,
}: {
  children: ReactNode
  description: string
  title: string
}) {
  return (
    <main className="grid min-h-screen place-items-center bg-muted/30 p-6">
      <Panel className="w-full max-w-md">
        <PanelHeader>
          <PanelTitle>{title}</PanelTitle>
          <PanelDescription>{description}</PanelDescription>
        </PanelHeader>
        <PanelBody>{children}</PanelBody>
      </Panel>
    </main>
  )
}

function AuthError({ error }: { error: string | null }) {
  return error ? (
    <p className="text-sm text-destructive" role="alert">
      {error}
    </p>
  ) : null
}
