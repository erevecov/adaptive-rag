import { type FormEvent, type ReactNode } from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { DataList, DataListItem } from '@/components/ui/data-list'
import { Callout, EmptyState } from '@/components/ui/feedback'
import { Field, FieldControl, FieldLabel } from '@/components/ui/field'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import { Select } from '@/components/ui/select'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
  tableNumericClass,
} from '@/components/ui/table'
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@/components/ui/tabs'
import type {
  ChatObservabilityProviderUsageGroup,
  ChatObservabilitySummary,
} from '@/lib/apiClient'

const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')
const STATUS_ORDER = ['failed', 'running', 'succeeded']

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type ObservabilitySubmodule = 'summary' | 'costs' | 'errors' | 'latency'

const OBSERVABILITY_TABS: { label: string; value: ObservabilitySubmodule }[] = [
  { label: 'Summary', value: 'summary' },
  { label: 'Costs', value: 'costs' },
  { label: 'Errors', value: 'errors' },
  { label: 'Latency', value: 'latency' },
]

const EMPTY_OBSERVABILITY_MESSAGES: Record<ObservabilitySubmodule, string> = {
  costs:
    'No Cost Rollup Available Yet. Enter Filters and Refresh to Inspect Provider Spend.',
  errors:
    'No Error Clusters Available Yet. Enter Filters and Refresh to Inspect Failures.',
  latency:
    'No Latency Groups Available Yet. Enter Filters and Refresh to Inspect Response Timing.',
  summary:
    'No Observability Summary Yet. Enter Filters and Refresh to Inspect Chat Health.',
}

export type ObservabilityPanelProps = {
  activeSubmodule: ObservabilitySubmodule
  createdAtFrom: string
  createdAtTo: string
  error: string | null
  onCreatedAtFromChange(value: string): void
  onCreatedAtToChange(value: string): void
  onProjectIdChange(value: string): void
  onRefresh(): void
  onStatusChange(value: string): void
  onSubmoduleChange(submodule: ObservabilitySubmodule): void
  projectId: string
  state: RequestState
  status: string
  summary: ChatObservabilitySummary | null
}

export function ObservabilityPanel({
  activeSubmodule,
  createdAtFrom,
  createdAtTo,
  error,
  onCreatedAtFromChange,
  onCreatedAtToChange,
  onProjectIdChange,
  onRefresh,
  onStatusChange,
  onSubmoduleChange,
  projectId,
  state,
  status,
  summary,
}: ObservabilityPanelProps) {
  const isRefreshing = state === 'loading'
  const activeLabel = observabilitySubmoduleLabel(activeSubmodule)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onRefresh()
  }

  return (
    <Panel
      aria-label={`Observability ${activeSubmodule}`}
      role="region"
    >
      <PanelHeader className="max-[680px]:border-b max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary min-w-0 flex-col items-start justify-between gap-3 p-4 lg:flex-row max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:px-0.5">
            Observability
          </p>
          <PanelTitle className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" id="observability-title">{activeLabel}</PanelTitle>
          <PanelDescription className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            Inspect Chat Health, Cost, Error, and Latency Rollups.
          </PanelDescription>
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 lg:justify-end max-[680px]:gap-0.5">
          <StatusBadge
            aria-live="polite"
            className="max-[680px]:rounded-sm max-w-full break-all text-left max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
            role="status"
            tone={requestStateTone(state)}
          >
            {observabilityStatusLabel(state)}
          </StatusBadge>
        </div>
      </PanelHeader>
      <PanelBody className="max-[680px]:border-t max-[680px]:border-primary/95 grid gap-4 p-4 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">
        <SegmentedControl
          aria-label="Observability Views"
          className="max-w-full flex-wrap justify-start max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:border max-[680px]:border-primary/95 max-[680px]:rounded-sm max-[680px]:p-0.5 max-[680px]:px-0.5"
          role="tablist"
        >
          {OBSERVABILITY_TABS.map((tab) => (
            <SegmentedControlItem
              active={activeSubmodule === tab.value}
              aria-controls={`observability-panel-${tab.value}`}
              id={`observability-tab-${tab.value}`}
              key={tab.value}
              onClick={() => onSubmoduleChange(tab.value)}
              value={tab.value}
            >
              {tab.label}
            </SegmentedControlItem>
          ))}
        </SegmentedControl>

        <form className="grid gap-4 max-[680px]:gap-0.5 xl:grid-cols-[minmax(220px,1.4fr)_repeat(3,minmax(160px,1fr))_auto] xl:items-end" onSubmit={handleSubmit}>
          <ObservabilityField id="observability-project-id" label="Project ID">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                autoComplete="off"
                id={fieldId}
                name="observability-project-id"
                onChange={(event) => onProjectIdChange(event.currentTarget.value)}
                placeholder="Project UUID"
                value={projectId}
              />
            )}
          </ObservabilityField>
          <ObservabilityField id="observability-created-from" label="Created From">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                id={fieldId}
                name="created-at-from"
                onChange={(event) =>
                  onCreatedAtFromChange(event.currentTarget.value)
                }
                placeholder="2026-06-21T00:00:00Z"
                value={createdAtFrom}
              />
            )}
          </ObservabilityField>
          <ObservabilityField id="observability-created-to" label="Created To">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                id={fieldId}
                name="created-at-to"
                onChange={(event) => onCreatedAtToChange(event.currentTarget.value)}
                placeholder="2026-06-22T00:00:00Z"
                value={createdAtTo}
              />
            )}
          </ObservabilityField>
          <ObservabilityField id="observability-status" label="Status">
            {(fieldId) => (
              <Select
                className="max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                id={fieldId}
                name="observability-status"
                onValueChange={onStatusChange}
                options={[
                  { label: 'Any', value: '' },
                  { label: 'Running', value: 'running' },
                  { label: 'Succeeded', value: 'succeeded' },
                  { label: 'Failed', value: 'failed' },
                ]}
                value={status}
              />
            )}
          </ObservabilityField>
          <Button className="whitespace-nowrap max-[680px]:h-6 max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isRefreshing} type="submit">
            {isRefreshing ? 'Refreshing…' : 'Refresh Summary'}
          </Button>
        </form>

        {error ? (
          <Callout className="p-3 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm" role="alert" tone="danger">
            {operatorSafeMessage(error)}
          </Callout>
        ) : null}

        <div
          aria-labelledby={`observability-tab-${activeSubmodule}`}
          id={`observability-panel-${activeSubmodule}`}
          role="tabpanel"
        >
          <ObservabilityContent
            activeSubmodule={activeSubmodule}
            state={state}
            summary={summary}
          />
        </div>
      </PanelBody>
    </Panel>
  )
}

function ObservabilityField({
  children,
  id,
  label,
}: {
  children(id: string): ReactNode
  id: string
  label: string
}) {
  return (
    <Field className="max-[680px]:gap-0.5">
      <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
    </Field>
  )
}

function ObservabilityContent({
  activeSubmodule,
  state,
  summary,
}: {
  activeSubmodule: ObservabilitySubmodule
  state: RequestState
  summary: ChatObservabilitySummary | null
}) {
  const isLoading = state === 'loading'

  if (summary === null) {
    if (isLoading) {
      return <ObservabilityMetricSkeleton activeSubmodule={activeSubmodule} />
    }
    // Keep failed load distinct from the never-loaded empty prompt.
    if (state === 'failed') {
      return (
        <EmptyState
          className="border-destructive/40 bg-destructive/5 p-4 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="failed"
          role="alert"
        >
          <p className="font-semibold text-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">Summary Unavailable.</p>
          <p className="text-xs leading-relaxed text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            The Last Refresh Failed. Adjust Filters and Try Again.
          </p>
        </EmptyState>
      )
    }
    if (state === 'canceled') {
      return (
        <EmptyState
          className="border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="canceled"
          role="status"
        >
          <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">Refresh Canceled.</p>
          <p className="text-xs leading-relaxed text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            No Summary Loaded. Run Refresh Again When Ready.
          </p>
        </EmptyState>
      )
    }
    return (
      <EmptyState className="border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
        {EMPTY_OBSERVABILITY_MESSAGES[activeSubmodule]}
      </EmptyState>
    )
  }

  const content =
    activeSubmodule === 'costs' ? (
      <ObservabilityCostsContent summary={summary} />
    ) : activeSubmodule === 'errors' ? (
      <ObservabilityErrorsContent summary={summary} />
    ) : activeSubmodule === 'latency' ? (
      <ObservabilityLatencyContent summary={summary} />
    ) : (
      <ObservabilitySummaryContent summary={summary} />
    )

  if (!isLoading && state !== 'failed') {
    return content
  }

  if (state === 'failed') {
    return (
      <div className="grid gap-3 max-[680px]:gap-0.5" data-slot="observability-stale-failed">
        <Callout className="p-3 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm" role="alert" tone="danger">
          Showing last successful summary — Refresh Failed.
        </Callout>
        <div className="pointer-events-none" data-stale="">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div
      aria-busy="true"
      className="relative"
      data-slot="observability-refreshing"
    >
      <p className="mb-2 text-xs font-medium text-muted-foreground max-[680px]:mb-1 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" role="status">
        Refreshing…
      </p>
      {content}
    </div>
  )
}

function ObservabilityMetricSkeleton({
  activeSubmodule,
}: {
  activeSubmodule: ObservabilitySubmodule
}) {
  const cardCount = activeSubmodule === 'summary' ? 5 : 3
  const label =
    activeSubmodule === 'costs'
      ? 'Cost Observability Metrics Loading'
      : activeSubmodule === 'errors'
        ? 'Error Observability Metrics Loading'
        : activeSubmodule === 'latency'
          ? 'Latency Observability Metrics Loading'
          : 'Chat Observability Metrics Loading'

  return (
    <div
      aria-busy="true"
      aria-label={label}
      className={
        cardCount === 5
          ? 'grid gap-3 max-[680px]:gap-0.5 md:grid-cols-2 xl:grid-cols-5'
          : 'grid gap-3 max-[680px]:gap-0.5 md:grid-cols-2 xl:grid-cols-3'
      }
      data-slot="observability-metric-skeleton"
      role="status"
    >
      <span className="sr-only">Loading Observability Metrics…</span>
      {Array.from({ length: cardCount }, (_, index) => (
        <article
          aria-hidden="true"
          className="grid min-h-28 gap-2 rounded-md border border-border bg-card p-4 max-[680px]:min-h-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
          key={index}
        >
          <div className="h-3 w-1/3 motion-safe:animate-pulse max-[680px]:h-1 rounded bg-muted/40" />
          <div className="h-7 w-2/3 motion-safe:animate-pulse max-[680px]:h-2 rounded bg-muted/40" />
          <div className="h-3 w-4/5 motion-safe:animate-pulse max-[680px]:h-1 rounded bg-muted/40" />
        </article>
      ))}
    </div>
  )
}

function ObservabilitySummaryContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <>
      <ObservabilitySummaryMetrics summary={summary} />
      <ObservabilityBreakdowns summary={summary} />
    </>
  )
}

function ObservabilitySummaryMetrics({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  const slowestP95 = getSlowestP95Group(summary.provider_usage.groups)
  const errorCount =
    summary.errors.session_error_count + summary.errors.provider_error_count

  return (
    <MetricGrid label="Chat Observability Metrics">
      <MetricCard
        detail="Filtered Chat Sessions"
        label="Sessions"
        value={String(summary.sessions.total)}
      />
      <MetricCard
        detail={`${summary.provider_usage.missing_cost_count} Missing Cost`}
        label="Provider Calls"
        value={String(summary.provider_usage.total_records)}
      />
      <MetricCard
        detail="Known Usage Only"
        label="Estimated Cost"
        value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
      />
      <MetricCard
        detail={`${summary.errors.session_error_count} Sessions / ${summary.errors.provider_error_count} Providers`}
        label="Errors"
        value={String(errorCount)}
      />
      <MetricCard
        detail={
          slowestP95 === null
            ? 'No Known Provider Latency'
            : `Slowest P95 ${slowestP95.provider} / ${slowestP95.model}`
        }
        label="Latency"
        value={slowestP95 === null ? 'No P95' : `${slowestP95.latency_ms.p95} ms`}
      />
    </MetricGrid>
  )
}

function ObservabilityCostsContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <>
      <MetricGrid columns={3} label="Cost Observability Metrics">
        <MetricCard
          detail={`${summary.provider_usage.groups.length} Provider Groups`}
          label="Provider Calls"
          value={String(summary.provider_usage.total_records)}
        />
        <MetricCard
          detail="Known Usage Only"
          label="Estimated Cost"
          value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
        />
        <MetricCard
          detail="Usage Records Without Cost"
          label="Missing Costs"
          value={String(summary.provider_usage.missing_cost_count)}
        />
      </MetricGrid>
      <div className="grid gap-3 max-[680px]:gap-0.5">
        <ProviderUsageTable summary={summary} />
      </div>
    </>
  )
}

function ObservabilityErrorsContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  const errorCount =
    summary.errors.session_error_count + summary.errors.provider_error_count

  return (
    <>
      <MetricGrid columns={3} label="Error Observability Metrics">
        <MetricCard
          detail={`${summary.errors.session_error_count} Sessions / ${summary.errors.provider_error_count} Providers`}
          label="Errors"
          value={String(errorCount)}
        />
        <MetricCard
          detail={`${summary.sessions.total} Sessions in Filter`}
          label="Failed Sessions"
          value={String(summary.sessions.by_status.failed ?? 0)}
        />
        <MetricCard
          detail="Grouped Error Messages"
          label="Top Messages"
          value={String(summary.errors.top_messages.length)}
        />
      </MetricGrid>
      <BreakdownGrid>
        <StatusBreakdown summary={summary} />
        <ErrorMessages summary={summary} />
        <SessionHealth summary={summary} />
      </BreakdownGrid>
    </>
  )
}

function ObservabilityLatencyContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  const slowestP95 = getSlowestP95Group(summary.provider_usage.groups)

  return (
    <>
      <MetricGrid columns={3} label="Latency Observability Metrics">
        <MetricCard
          detail={
            slowestP95 === null
              ? 'No Known Provider Latency'
              : `Slowest P95 ${slowestP95.provider} / ${slowestP95.model}`
          }
          label="Latency"
          value={
            slowestP95 === null ? 'No P95' : `${slowestP95.latency_ms.p95} ms`
          }
        />
        <MetricCard
          detail="Latency Rollups"
          label="Provider Groups"
          value={String(summary.provider_usage.groups.length)}
        />
        <MetricCard
          detail="Usage Records With Timing"
          label="Provider Calls"
          value={String(summary.provider_usage.total_records)}
        />
      </MetricGrid>
      <div className="grid gap-3 max-[680px]:gap-0.5">
        <ProviderLatencyTable summary={summary} />
      </div>
    </>
  )
}

function ObservabilityBreakdowns({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <BreakdownGrid>
      <StatusBreakdown summary={summary} />
      <ErrorMessages summary={summary} />
      <ProviderUsageTable summary={summary} />
      <SessionHealth summary={summary} />
    </BreakdownGrid>
  )
}

function MetricGrid({
  children,
  columns = 5,
  label,
}: {
  children: ReactNode
  columns?: 3 | 5
  label: string
}) {
  return (
    <div
      aria-label={label}
      className={
        columns === 5
          ? 'grid gap-3 max-[680px]:gap-0.5 md:grid-cols-2 xl:grid-cols-5'
          : 'grid gap-3 max-[680px]:gap-0.5 md:grid-cols-2 xl:grid-cols-3'
      }
    >
      {children}
    </div>
  )
}

function MetricCard({
  detail,
  label,
  value,
}: {
  detail: string
  label: string
  value: string
}) {
  const slug = label.toLowerCase().replace(/\s+/g, '-')
  const labelId = `metric-label-${slug}`
  const valueId = `metric-value-${slug}`
  return (
    <article
      aria-labelledby={`${labelId} ${valueId}`}
      className="grid min-h-28 gap-2 rounded-md border border-border bg-card p-4 text-card-foreground tracking-tight max-[680px]:min-h-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
    >
      <span
        className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter max-[680px]:px-0.5"
        id={labelId}
      >
        {label}
      </span>
      <strong
        className="break-words text-2xl font-semibold leading-none tabular-nums max-[680px]:text-base max-[680px]:leading-tight max-[680px]:tracking-tighter"
        id={valueId}
      >
        {value}
      </strong>
      <small className="text-sm leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
        {detail}
      </small>
    </article>
  )
}

function BreakdownGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 max-[680px]:gap-0.5 lg:grid-cols-2">{children}</div>
}

function BreakdownCard({
  children,
  label,
  title,
}: {
  children: ReactNode
  label: string
  title: string
}) {
  return (
    <section
      aria-label={title}
      className="grid min-w-0 gap-3 max-[680px]:gap-0.5 rounded-md border border-border bg-card p-4 text-card-foreground max-[680px]:p-0.5 max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2 max-[680px]:gap-0.5">
        <h3 className="text-base font-semibold leading-none max-[680px]:text-[0.5625rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">{title}</h3>
        <Badge className="max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{label}</Badge>
      </div>
      {children}
    </section>
  )
}

function StatusBreakdown({ summary }: { summary: ChatObservabilitySummary }) {
  const rows = getStatusBreakdown(summary.sessions.by_status)

  return (
    <BreakdownCard label={`${summary.sessions.total} Total`} title="Status Breakdown">
      {rows.length === 0 ? (
        <EmptyState className="p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
          No Status Data Yet.
        </EmptyState>
      ) : (
        <DataList className="max-[680px]:gap-0.5">
          {rows.map((row) => (
            <DataListItem
              className="flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0.5 border-0 bg-transparent p-2 max-[680px]:p-0.5 max-[680px]:tracking-tighter shadow-none max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border max-[680px]:border-primary/95 max-[680px]:rounded-sm max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary"
              key={row.status}
            >
              <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                <strong className="break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {sessionStatusDisplayLabel(row.status)}
                </strong>
                <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {formatPercent(row.count, summary.sessions.total)}
                </small>
              </div>
              <Badge className="max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{formatCount(row.count, 'Session')}</Badge>
            </DataListItem>
          ))}
        </DataList>
      )}
    </BreakdownCard>
  )
}

function ErrorMessages({ summary }: { summary: ChatObservabilitySummary }) {
  return (
    <BreakdownCard
      label={`${summary.errors.top_messages.length} Messages`}
      title="Error Messages"
    >
      {summary.errors.top_messages.length === 0 ? (
        <EmptyState className="p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
          No Error Messages Yet.
        </EmptyState>
      ) : (
        <DataList className="max-[680px]:gap-0.5">
          {summary.errors.top_messages.map((error) => (
            <DataListItem
              className="flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0.5 border-0 bg-transparent p-2 max-[680px]:p-0.5 max-[680px]:tracking-tighter shadow-none max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border max-[680px]:border-primary/95 max-[680px]:rounded-sm max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary"
              key={error.message}
            >
              <strong className="break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                {operatorSafeMessage(error.message, error.message)}
              </strong>
              <Badge className="max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{formatCount(error.count, 'Occurrence')}</Badge>
            </DataListItem>
          ))}
        </DataList>
      )}
    </BreakdownCard>
  )
}

function ProviderUsageTable({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <div className="lg:col-span-2">
      <BreakdownCard
        label={`${summary.provider_usage.groups.length} groups`}
        title="Provider Usage"
      >
        {summary.provider_usage.groups.length === 0 ? (
          <EmptyState className="p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
            No Provider Usage Groups Yet.
          </EmptyState>
        ) : (
          <TableScroll>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Operation</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead className={tableNumericClass}>Calls</TableHead>
                  <TableHead className={tableNumericClass}>Tokens</TableHead>
                  <TableHead className={tableNumericClass}>Cost</TableHead>
                  <TableHead className={tableNumericClass}>P95</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.provider_usage.groups.map((group) => (
                  <TableRow key={`${group.operation}-${group.provider}-${group.model}`}>
                    <TableCell>{group.operation}</TableCell>
                    <TableCell>{group.provider}</TableCell>
                    <TableCell>{group.model}</TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNumber(group.record_count)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableNumber(group.total_tokens)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableUsd(group.estimated_cost_usd)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableMs(group.latency_ms.p95)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        )}
      </BreakdownCard>
    </div>
  )
}

function ProviderLatencyTable({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <div className="lg:col-span-2">
      <BreakdownCard
        label={`${summary.provider_usage.groups.length} groups`}
        title="Provider Latency"
      >
        {summary.provider_usage.groups.length === 0 ? (
          <EmptyState className="p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
            No Provider Latency Groups Yet.
          </EmptyState>
        ) : (
          <TableScroll>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Operation</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead className={tableNumericClass}>Calls</TableHead>
                  <TableHead className={tableNumericClass}>Avg</TableHead>
                  <TableHead className={tableNumericClass}>P50</TableHead>
                  <TableHead className={tableNumericClass}>P95</TableHead>
                  <TableHead className={tableNumericClass}>Max</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.provider_usage.groups.map((group) => (
                  <TableRow key={`${group.operation}-${group.provider}-${group.model}`}>
                    <TableCell>{group.operation}</TableCell>
                    <TableCell>{group.provider}</TableCell>
                    <TableCell>{group.model}</TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNumber(group.record_count)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableMs(group.latency_ms.avg)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableMs(group.latency_ms.p50)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableMs(group.latency_ms.p95)}
                    </TableCell>
                    <TableCell className={tableNumericClass}>
                      {formatNullableMs(group.latency_ms.max)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        )}
      </BreakdownCard>
    </div>
  )
}

function SessionHealth({ summary }: { summary: ChatObservabilitySummary }) {
  const total = summary.sessions.total
  const succeeded = summary.sessions.by_status.succeeded ?? 0
  const failed = summary.sessions.by_status.failed ?? 0
  const running = summary.sessions.by_status.running ?? 0

  return (
    <BreakdownCard label="Current Filter" title="Session Health">
      {total === 0 ? (
        <EmptyState className="p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
          No Sessions in This Filter Window.
        </EmptyState>
      ) : (
        <div className="grid gap-2 max-[680px]:gap-0.5">
          <strong className="text-2xl font-semibold leading-none tabular-nums max-[680px]:text-lg max-[680px]:leading-tight max-[680px]:tracking-tighter">
            {formatPercent(succeeded, total)} Success
          </strong>
          <span className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            {formatCount(failed, 'Failed Session')}
          </span>
          <span className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            {formatCount(running, 'Running Session')}
          </span>
        </div>
      )}
    </BreakdownCard>
  )
}

function requestStateTone(
  state: RequestState,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (state === 'failed') return 'danger'
  if (state === 'succeeded') return 'success'
  if (state === 'loading') return 'warning'
  if (state === 'canceled') return 'neutral'
  return 'neutral'
}

function observabilityStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Refreshing'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Loaded'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Ready'
}

function sessionStatusDisplayLabel(status: string): string {
  if (status === 'failed') {
    return 'Failed'
  }
  if (status === 'succeeded') {
    return 'Succeeded'
  }
  if (status === 'running') {
    return 'Running'
  }
  if (status === 'canceled' || status === 'cancelled') {
    return 'Canceled'
  }
  return status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function observabilitySubmoduleLabel(submodule: ObservabilitySubmodule): string {
  if (submodule === 'costs') return 'Costs'
  if (submodule === 'errors') return 'Errors'
  if (submodule === 'latency') return 'Latency'
  return 'Summary'
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`
}

function formatNullableUsd(value: number | null): string {
  return value === null ? 'N/A' : formatUsd(value)
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}

function formatNullableNumber(value: number | null): string {
  return value === null ? 'N/A' : formatNumber(value)
}

function formatNullableMs(value: number | null): string {
  return value === null ? 'N/A' : `${value} ms`
}

function formatPercent(value: number, total: number): string {
  if (total === 0) {
    return '0.0%'
  }
  return `${((value / total) * 100).toFixed(1)}%`
}

function formatCount(value: number, singularLabel: string): string {
  if (value === 1) {
    return `1 ${singularLabel}`
  }
  return `${formatNumber(value)} ${singularLabel}s`
}

function getStatusBreakdown(
  byStatus: Record<string, number>,
): { count: number; status: string }[] {
  return Object.entries(byStatus)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ count, status }))
    .sort((left, right) => {
      const leftIndex = STATUS_ORDER.indexOf(left.status)
      const rightIndex = STATUS_ORDER.indexOf(right.status)
      if (leftIndex !== -1 || rightIndex !== -1) {
        return normalizeStatusIndex(leftIndex) - normalizeStatusIndex(rightIndex)
      }
      return right.count - left.count
    })
}

function normalizeStatusIndex(index: number): number {
  return index === -1 ? Number.MAX_SAFE_INTEGER : index
}

function getSlowestP95Group(
  groups: ChatObservabilityProviderUsageGroup[],
): ChatObservabilityProviderUsageGroup | null {
  let slowest: ChatObservabilityProviderUsageGroup | null = null
  for (const group of groups) {
    if (group.latency_ms.p95 === null) {
      continue
    }
    if (slowest === null || group.latency_ms.p95 > slowest.latency_ms.p95!) {
      slowest = group
    }
  }
  return slowest
}
