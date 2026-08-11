import { type ReactNode } from 'react'

export type StreamingAnswerProps = {
  actions?: ReactNode
  children: ReactNode
  isStreaming?: boolean
  sources?: ReactNode
}

export function StreamingAnswer({
  actions,
  children,
  isStreaming = false,
  sources,
}: StreamingAnswerProps) {
  return (
    <article
      aria-busy={isStreaming || undefined}
      className="grid gap-3 rounded-[2px] border border-border bg-card p-4 text-sm leading-relaxed text-card-foreground motion-safe:transition-colors max-[680px]:p-3"
      data-slot="streaming-answer"
    >
      <div data-slot="streaming-answer-content">{children}</div>
      {sources ? (
        <div className="border-t border-border pt-3" data-slot="streaming-answer-sources">
          {sources}
        </div>
      ) : null}
      {actions ? (
        <div
          className="flex flex-wrap items-center gap-2 border-t border-border pt-3 max-[680px]:gap-1"
          data-slot="streaming-answer-actions"
        >
          {actions}
        </div>
      ) : null}
    </article>
  )
}
