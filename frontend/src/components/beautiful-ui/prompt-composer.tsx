import { type FormEvent, type ReactNode, useId } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/control'

export type PromptComposerProps = {
  attachments?: ReactNode
  busy?: boolean
  canSubmit?: boolean
  children?: ReactNode
  onCancel?(): void
  onSubmit(event: FormEvent<HTMLFormElement>): void
  prompt: string
  promptLabel: string
  submitLabel: string
  onPromptChange(value: string): void
  tools?: ReactNode
}

export function PromptComposer({
  attachments,
  busy = false,
  canSubmit = false,
  children,
  onCancel,
  onPromptChange,
  onSubmit,
  prompt,
  promptLabel,
  submitLabel,
  tools,
}: PromptComposerProps) {
  const promptId = useId()

  return (
    <form
      aria-busy={busy || undefined}
      aria-label={promptLabel}
      className="grid gap-2 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:gap-1 max-[680px]:p-2"
      data-slot="prompt-composer"
      onSubmit={onSubmit}
    >
      {attachments ? <div data-slot="prompt-composer-attachments">{attachments}</div> : null}
      <label className="sr-only" htmlFor={promptId}>
        {promptLabel}
      </label>
      <Textarea
        id={promptId}
        onChange={(event) => onPromptChange(event.target.value)}
        placeholder={promptLabel}
        value={prompt}
      />
      {children ? <div data-slot="prompt-composer-content">{children}</div> : null}
      <div
        className="flex flex-wrap items-center justify-between gap-2 max-[680px]:gap-1"
        data-slot="prompt-composer-controls"
      >
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-1" data-slot="prompt-composer-tools">
          {tools}
        </div>
        <div className="flex items-center gap-2 max-[680px]:gap-1">
          {busy && onCancel ? (
            <Button onClick={onCancel} type="button" variant="secondary">
              Cancel request
            </Button>
          ) : null}
          <Button disabled={!canSubmit || busy} type="submit">
            {submitLabel}
          </Button>
        </div>
      </div>
    </form>
  )
}
