import { type FormEvent, useId, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'

export type ApprovalChoice = { id: string; label: string }

export type ApprovalPromptProps = {
  busy?: boolean
  choices: readonly ApprovalChoice[]
  customLabel?: string
  onChoose(id: string): void
  onCustomSubmit?(value: string): void
  question: string
}

export function ApprovalPrompt({
  busy = false,
  choices,
  customLabel = 'Custom answer',
  onChoose,
  onCustomSubmit,
  question,
}: ApprovalPromptProps) {
  const customAnswerId = useId()
  const [customAnswer, setCustomAnswer] = useState('')
  const trimmedCustomAnswer = customAnswer.trim()

  function submitCustomAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!trimmedCustomAnswer) {
      return
    }

    onCustomSubmit?.(trimmedCustomAnswer)
    setCustomAnswer('')
  }

  return (
    <section
      aria-busy={busy || undefined}
      aria-label={question}
      className="grid gap-3 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:gap-2 max-[680px]:p-2"
      data-slot="approval-prompt"
    >
      <h2 className="text-sm font-medium">{question}</h2>
      <div className="flex flex-wrap gap-2 max-[680px]:gap-1" data-slot="approval-prompt-choices">
        {choices.map((choice) => (
          <Button disabled={busy} key={choice.id} onClick={() => onChoose(choice.id)}>
            {choice.label}
          </Button>
        ))}
      </div>
      {onCustomSubmit ? (
        <form
          aria-label={customLabel}
          className="flex flex-wrap items-end gap-2 max-[680px]:gap-1"
          onSubmit={submitCustomAnswer}
        >
          <label className="grid min-w-0 flex-1 gap-1 text-sm" htmlFor={customAnswerId}>
            <span>{customLabel}</span>
            <Input
              disabled={busy}
              id={customAnswerId}
              onChange={(event) => setCustomAnswer(event.target.value)}
              value={customAnswer}
            />
          </label>
          <Button disabled={busy || !trimmedCustomAnswer} type="submit" variant="secondary">
            Submit {customLabel.toLowerCase()}
          </Button>
        </form>
      ) : null}
    </section>
  )
}
