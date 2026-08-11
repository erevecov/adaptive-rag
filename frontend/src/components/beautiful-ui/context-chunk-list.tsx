import { type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/feedback'

export type ContextChunkItem = {
  content: ReactNode
  id: string
  meta?: ReactNode
  openLabel?: string
  sourceLabel: string
}

export type ContextChunkListProps = {
  chunks: readonly ContextChunkItem[]
  emptyLabel: string
  label: string
  onOpenChunk?(id: string): void
}

export function ContextChunkList({
  chunks,
  emptyLabel,
  label,
  onOpenChunk,
}: ContextChunkListProps) {
  return (
    <section
      className="grid gap-2 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:p-2"
    >
      <h2 className="text-sm font-medium">{label}</h2>
      {chunks.length === 0 ? (
        <EmptyState>{emptyLabel}</EmptyState>
      ) : (
        <ul
          aria-label={label}
          className="overflow-hidden rounded-[2px] border border-border"
          data-slot="context-chunk-list"
        >
          {chunks.map((chunk) => (
            <li
              className="grid gap-2 border-b border-border p-3 last:border-b-0 max-[680px]:gap-1 max-[680px]:p-2"
              data-slot="context-chunk"
              key={chunk.id}
            >
              <div className="flex min-w-0 items-center justify-between gap-2">
                {onOpenChunk ? (
                  <Button
                    aria-label={chunk.openLabel}
                    className="h-auto min-h-9 max-w-full justify-start px-0 py-0 text-left underline-offset-2 hover:underline max-[680px]:min-h-11"
                    onClick={() => onOpenChunk(chunk.id)}
                    variant="ghost"
                  >
                    {chunk.sourceLabel}
                  </Button>
                ) : (
                  <span className="min-w-0 truncate text-sm font-medium">{chunk.sourceLabel}</span>
                )}
                {chunk.meta ? (
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{chunk.meta}</span>
                ) : null}
              </div>
              <div className="text-sm leading-relaxed text-muted-foreground">{chunk.content}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
