import { type ReactNode } from 'react'

import { Button } from '@/components/ui/button'

export type RecommendationAlternative = {
  description?: ReactNode
  id: string
  label: string
}

export type RecommendationPanelProps = {
  alternatives?: readonly RecommendationAlternative[]
  confidence?: number | null
  description: ReactNode
  onAccept(): void
  onAlternative?(id: string): void
  title: string
}

function displayConfidence(confidence: number | null | undefined): number | null {
  if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
    return null
  }

  return Math.min(100, Math.max(0, confidence))
}

export function RecommendationPanel({
  alternatives = [],
  confidence,
  description,
  onAccept,
  onAlternative,
  title,
}: RecommendationPanelProps) {
  const displayedConfidence = displayConfidence(confidence)

  return (
    <article
      aria-label={title}
      className="grid gap-3 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:gap-2 max-[680px]:p-2"
      data-slot="recommendation-panel"
    >
      <div className="grid gap-1">
        <h2 className="text-sm font-medium">{title}</h2>
        <div className="text-sm text-muted-foreground">{description}</div>
      </div>
      {displayedConfidence !== null ? (
        <div className="grid gap-1" data-slot="recommendation-confidence">
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Confidence</span>
            <span className="tabular-nums">{displayedConfidence}%</span>
          </div>
          <progress
            aria-label="Confidence"
            className="h-2 w-full rounded-[2px] accent-primary"
            max={100}
            value={displayedConfidence}
          />
        </div>
      ) : null}
      {alternatives.length > 0 ? (
        <ul className="grid gap-2" data-slot="recommendation-alternatives">
          {alternatives.map((alternative) => (
            <li className="grid gap-1 border-l-2 border-border pl-2" key={alternative.id}>
              {onAlternative ? (
                <Button
                  className="h-auto min-h-9 justify-start px-0 py-0 text-left max-[680px]:min-h-11"
                  onClick={() => onAlternative(alternative.id)}
                  variant="ghost"
                >
                  {alternative.label}
                </Button>
              ) : (
                <span className="text-sm font-medium">{alternative.label}</span>
              )}
              {alternative.description ? (
                <div className="text-sm text-muted-foreground">{alternative.description}</div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      <div>
        <Button onClick={onAccept}>Accept recommendation</Button>
      </div>
    </article>
  )
}
