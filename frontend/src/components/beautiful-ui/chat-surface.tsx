import {
  type HTMLAttributes,
  type ReactNode,
  type Ref,
} from 'react'

export type ChatSurfaceProps = {
  className?: string
  composer: ReactNode
  composerClassName?: string
  empty?: ReactNode
  isEmpty?: boolean
  label?: string
  transcript: ReactNode
  transcriptClassName?: string
  transcriptProps?: Omit<HTMLAttributes<HTMLDivElement>, 'children' | 'className'>
  transcriptRef?: Ref<HTMLDivElement>
}

export function ChatSurface({
  className,
  composer,
  composerClassName,
  empty,
  isEmpty = false,
  label,
  transcript,
  transcriptClassName,
  transcriptProps,
  transcriptRef,
}: ChatSurfaceProps) {
  return (
    <section
      aria-label={label}
      className={
        className ??
        'grid min-h-0 grid-rows-[minmax(0,1fr)_auto] overflow-hidden rounded-[2px] border border-border bg-card'
      }
      data-slot="chat-surface"
    >
      <div
        {...transcriptProps}
        className={
          transcriptClassName ??
          'min-h-0 overflow-y-auto p-4 max-[680px]:p-3'
        }
        data-slot="chat-transcript"
        ref={transcriptRef}
      >
        {isEmpty ? empty : transcript}
      </div>
      <div
        className={
          composerClassName ??
          'max-h-[45svh] overflow-y-auto border-t border-border bg-background p-3 max-[680px]:max-h-[50svh]'
        }
        data-slot="chat-composer"
      >
        {composer}
      </div>
    </section>
  )
}
