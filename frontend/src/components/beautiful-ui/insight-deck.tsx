import { type ReactNode, useState } from 'react'

import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/feedback'

export type InsightPoint = { x: number; y: number }

export type InsightItem = {
  body: ReactNode
  id: string
  title: string
  trend?: readonly InsightPoint[]
}

export type InsightDeckProps = { insights: readonly InsightItem[]; label: string }

function TrendGraphic({ points, title }: { points: readonly InsightPoint[]; title: string }) {
  const xValues = points.map((point) => point.x)
  const yValues = points.map((point) => point.y)
  const minX = Math.min(...xValues)
  const maxX = Math.max(...xValues)
  const minY = Math.min(...yValues)
  const maxY = Math.max(...yValues)
  const xRange = maxX - minX || 1
  const yRange = maxY - minY || 1
  const path = points
    .map((point, index) => {
      const x = ((point.x - minX) / xRange) * 100
      const y = 32 - ((point.y - minY) / yRange) * 32
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  return (
    <svg
      aria-label={`${title} trend`}
      className="h-10 w-full text-primary"
      role="img"
      viewBox="0 0 100 32"
    >
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export function InsightDeck({ insights, label }: InsightDeckProps) {
  const [page, setPage] = useState(0)
  const currentPage = Math.min(page, Math.max(0, insights.length - 1))
  const insight = insights[currentPage]

  return (
    <section aria-label={label} className="grid gap-2" data-slot="insight-deck">
      <h2 className="text-sm font-medium">{label}</h2>
      {insight ? (
        <article className="grid gap-3 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:p-2">
          <div className="grid gap-1">
            <h3 className="font-medium">{insight.title}</h3>
            <div className="text-sm text-muted-foreground">{insight.body}</div>
          </div>
          {insight.trend && insight.trend.length >= 2 ? (
            <TrendGraphic points={insight.trend} title={insight.title} />
          ) : null}
          <div className="flex items-center justify-between gap-2">
            <Button disabled={currentPage === 0} onClick={() => setPage((value) => value - 1)} variant="secondary">
              Previous insight
            </Button>
            <span aria-live="polite" className="text-xs tabular-nums text-muted-foreground">
              {currentPage + 1} / {insights.length}
            </span>
            <Button
              disabled={currentPage >= insights.length - 1}
              onClick={() => setPage((value) => value + 1)}
              variant="secondary"
            >
              Next insight
            </Button>
          </div>
        </article>
      ) : (
        <EmptyState>No insights available.</EmptyState>
      )}
    </section>
  )
}
