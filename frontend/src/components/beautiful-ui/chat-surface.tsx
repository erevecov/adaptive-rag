import { type ReactNode } from 'react'

export type ChatSurfaceProps = {
  composer: ReactNode
  empty?: ReactNode
  isEmpty?: boolean
  transcript: ReactNode
}

export function ChatSurface({
  composer,
  empty,
  isEmpty = false,
  transcript,
}: ChatSurfaceProps) {
  return (
    <section
      className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] overflow-hidden rounded-[2px] border border-border bg-card"
      data-slot="chat-surface"
    >
      <div className="min-h-0 overflow-y-auto p-4 max-[680px]:p-3" data-slot="chat-transcript">
        {isEmpty ? empty : transcript}
      </div>
      <div
        className="max-h-[45svh] overflow-y-auto border-t border-border bg-background p-3 max-[680px]:max-h-[50svh]"
        data-slot="chat-composer"
      >
        {composer}
      </div>
    </section>
  )
}
