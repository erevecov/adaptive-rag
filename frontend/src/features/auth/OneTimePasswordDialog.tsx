import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'

export function OneTimePasswordDialog({
  email,
  onClose,
  password,
}: {
  email: string
  onClose(): void
  password: string
}) {
  const doneRef = useRef<HTMLButtonElement | null>(null)
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle')

  useEffect(() => {
    doneRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  async function copyPassword() {
    try {
      await navigator.clipboard.writeText(password)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
  }

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/50 p-4">
      <Panel
        aria-labelledby="temporary-password-title"
        aria-modal="true"
        className="w-full max-w-lg"
        role="dialog"
      >
        <PanelHeader>
          <PanelTitle id="temporary-password-title">
            Temporary password
          </PanelTitle>
          <p className="text-sm text-muted-foreground">
            This password will not be shown again. Send it through a secure
            channel; the user must replace it at first sign-in.
          </p>
        </PanelHeader>
        <PanelBody className="grid gap-4">
          <label className="grid gap-1 text-sm font-medium">
            Email
            <Input readOnly value={email} />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Temporary password
            <Input readOnly value={password} />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void copyPassword()} type="button">
              Copy password
            </Button>
            <Button
              onClick={onClose}
              ref={doneRef}
              type="button"
              variant="secondary"
            >
              Done
            </Button>
          </div>
          {copyState !== 'idle' ? (
            <p
              className={
                copyState === 'failed'
                  ? 'text-sm text-destructive'
                  : 'text-sm text-muted-foreground'
              }
              role="status"
            >
              {copyState === 'copied'
                ? 'Password copied.'
                : 'Copy failed. Select the password manually.'}
            </p>
          ) : null}
        </PanelBody>
      </Panel>
    </div>
  )
}
