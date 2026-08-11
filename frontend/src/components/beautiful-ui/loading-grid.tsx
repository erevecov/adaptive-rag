import { cn } from '@/lib/utils'

export type LoadingGridProps = {
  elapsedMs?: number | null
  label: string
  variant?: 'grid' | 'dots' | 'orbit'
}

function formatElapsed(elapsedMs: number): string {
  return `${(Math.max(0, elapsedMs) / 1_000).toFixed(1)}s`
}

export function LoadingGrid({
  elapsedMs,
  label,
  variant = 'grid',
}: LoadingGridProps) {
  const elapsed = typeof elapsedMs === 'number' ? formatElapsed(elapsedMs) : null

  return (
    <div
      aria-atomic="true"
      aria-label={label}
      aria-live="polite"
      className="inline-flex items-center gap-2 text-sm text-muted-foreground max-[680px]:min-h-11"
      data-slot="loading-grid"
      data-variant={variant}
      role="status"
    >
      <LoadingMark variant={variant} />
      <span>{label}</span>
      {elapsed ? <span className="tabular-nums">Elapsed {elapsed}</span> : null}
    </div>
  )
}

function LoadingMark({ variant }: Pick<LoadingGridProps, 'variant'>) {
  if (variant === 'dots') {
    return (
      <span aria-hidden="true" className="flex items-center gap-1" data-slot="loading-mark">
        {[0, 1, 2].map((dot) => (
          <span
            className="size-1.5 rounded-full bg-primary motion-safe:animate-pulse"
            key={dot}
          />
        ))}
      </span>
    )
  }

  if (variant === 'orbit') {
    return (
      <span
        aria-hidden="true"
        className="relative size-4 rounded-full border border-border motion-safe:animate-spin"
        data-slot="loading-mark"
      >
        <span className="absolute -top-0.5 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-primary" />
      </span>
    )
  }

  return (
    <span
      aria-hidden="true"
      className="grid size-4 grid-cols-2 gap-0.5"
      data-slot="loading-mark"
    >
      {[0, 1, 2, 3].map((cell) => (
        <span
          className={cn(
            'rounded-[2px] bg-primary/75 motion-safe:animate-pulse',
            cell % 2 === 0 && 'motion-safe:[animation-delay:150ms]',
          )}
          key={cell}
        />
      ))}
    </span>
  )
}
