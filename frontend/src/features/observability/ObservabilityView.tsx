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
    'No cost rollup available yet. Enter filters and refresh to inspect provider spend.',
  errors:
    'No error clusters available yet. Enter filters and refresh to inspect failures.',
  latency:
    'No latency groups available yet. Enter filters and refresh to inspect response timing.',
  summary:
    'No observability summary yet. Enter filters and refresh to inspect chat health.',
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
      <PanelHeader className="min-w-0 flex-col items-start justify-between gap-3 p-4 lg:flex-row">
        <div className="grid min-w-0 gap-1">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            Observability
          </p>
          <PanelTitle id="observability-title">{activeLabel}</PanelTitle>
          <PanelDescription>
            Inspect chat health, cost, error, and latency rollups.
          </PanelDescription>
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 lg:justify-end">
          <StatusBadge
            aria-live="polite"
            className="max-w-full break-all text-left"
            role="status"
            tone={requestStateTone(state)}
          >
            {observabilityStatusLabel(state)}
          </StatusBadge>
        </div>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0">
        <SegmentedControl
          aria-label="Observability views"
          className="max-w-full flex-wrap justify-start"
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

        <form className="grid gap-4 xl:grid-cols-[minmax(220px,1.4fr)_repeat(3,minmax(160px,1fr))_auto] xl:items-end" onSubmit={handleSubmit}>
          <ObservabilityField id="observability-project-id" label="Project ID">
            {(fieldId) => (
              <Input
                autoComplete="off"
                id={fieldId}
                name="observability-project-id"
                onChange={(event) => onProjectIdChange(event.currentTarget.value)}
                placeholder="Project UUID"
                value={projectId}
              />
            )}
          </ObservabilityField>
          <ObservabilityField id="observability-created-from" label="Created from">
            {(fieldId) => (
              <Input
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
          <ObservabilityField id="observability-created-to" label="Created to">
            {(fieldId) => (
              <Input
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
                id={fieldId}
                name="observability-status"
                onValueChange={onStatusChange}
                options={[
                  { label: 'Any', value: '' },
                  { label: 'running', value: 'running' },
                  { label: 'succeeded', value: 'succeeded' },
                  { label: 'failed', value: 'failed' },
                ]}
                value={status}
              />
            )}
          </ObservabilityField>
          <Button className="whitespace-nowrap" disabled={isRefreshing} type="submit">
            {isRefreshing ? 'Refreshing...' : 'Refresh summary'}
          </Button>
        </form>

        {error ? (
          <Callout className="p-3" role="alert" tone="danger">
            {error}
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
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
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
          className="border-destructive/40 bg-destructive/5 p-4 text-left"
          data-slot-state="failed"
          role="alert"
        >
          <p className="font-semibold text-destructive">Summary unavailable.</p>
          <p className="text-xs leading-relaxed text-muted-foreground">
            The last refresh failed. Adjust filters and try again.
          </p>
        </EmptyState>
      )
    }
    return (
      <EmptyState data-slot-state="empty" role="status">
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
      <div className="grid gap-3" data-slot="observability-stale-failed">
        <Callout className="p-3" role="alert" tone="danger">
          Showing last successful summary — refresh failed.
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
      <p className="mb-2 text-xs font-medium text-muted-foreground" role="status">
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
      ? 'Cost observability metrics loading'
      : activeSubmodule === 'errors'
        ? 'Error observability metrics loading'
        : activeSubmodule === 'latency'
          ? 'Latency observability metrics loading'
          : 'Chat observability metrics loading'

  return (
    <div
      aria-busy="true"
      aria-label={label}
      className={
        cardCount === 5
          ? 'grid gap-3 md:grid-cols-2 xl:grid-cols-5'
          : 'grid gap-3 md:grid-cols-2 xl:grid-cols-3'
      }
      data-slot="observability-metric-skeleton"
      role="status"
    >
      <span className="sr-only">Loading observability metrics…</span>
      {Array.from({ length: cardCount }, (_, index) => (
        <article
          aria-hidden="true"
          className="grid min-h-28 gap-2 rounded-md border border-border bg-card p-4"
          key={index}
        >
          <div className="h-3 w-1/3 motion-safe:animate-pulse rounded bg-muted" />
          <div className="h-7 w-2/3 motion-safe:animate-pulse rounded bg-muted" />
          <div className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted" />
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
    <MetricGrid label="Chat observability metrics">
      <MetricCard
        detail="Filtered chat sessions"
        label="Sessions"
        value={String(summary.sessions.total)}
      />
      <MetricCard
        detail={`${summary.provider_usage.missing_cost_count} missing cost`}
        label="Provider calls"
        value={String(summary.provider_usage.total_records)}
      />
      <MetricCard
        detail="Known usage only"
        label="Estimated cost"
        value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
      />
      <MetricCard
        detail={`${summary.errors.session_error_count} sessions / ${summary.errors.provider_error_count} providers`}
        label="Errors"
        value={String(errorCount)}
      />
      <MetricCard
        detail={
          slowestP95 === null
            ? 'No known provider latency'
            : `Slowest p95 ${slowestP95.provider} / ${slowestP95.model}`
        }
        label="Latency"
        value={slowestP95 === null ? 'No p95' : `${slowestP95.latency_ms.p95} ms`}
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
      <MetricGrid columns={3} label="Cost observability metrics">
        <MetricCard
          detail={`${summary.provider_usage.groups.length} provider groups`}
          label="Provider calls"
          value={String(summary.provider_usage.total_records)}
        />
        <MetricCard
          detail="Known usage only"
          label="Estimated cost"
          value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
        />
        <MetricCard
          detail="Usage records without cost"
          label="Missing costs"
          value={String(summary.provider_usage.missing_cost_count)}
        />
      </MetricGrid>
      <div className="grid gap-3">
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
      <MetricGrid columns={3} label="Error observability metrics">
        <MetricCard
          detail={`${summary.errors.session_error_count} sessions / ${summary.errors.provider_error_count} providers`}
          label="Errors"
          value={String(errorCount)}
        />
        <MetricCard
          detail={`${summary.sessions.total} sessions in filter`}
          label="Failed sessions"
          value={String(summary.sessions.by_status.failed ?? 0)}
        />
        <MetricCard
          detail="Grouped error messages"
          label="Top messages"
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
      <MetricGrid columns={3} label="Latency observability metrics">
        <MetricCard
          detail={
            slowestP95 === null
              ? 'No known provider latency'
              : `Slowest p95 ${slowestP95.provider} / ${slowestP95.model}`
          }
          label="Latency"
          value={
            slowestP95 === null ? 'No p95' : `${slowestP95.latency_ms.p95} ms`
          }
        />
        <MetricCard
          detail="Latency rollups"
          label="Provider groups"
          value={String(summary.provider_usage.groups.length)}
        />
        <MetricCard
          detail="Usage records with timing"
          label="Provider calls"
          value={String(summary.provider_usage.total_records)}
        />
      </MetricGrid>
      <div className="grid gap-3">
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
          ? 'grid gap-3 md:grid-cols-2 xl:grid-cols-5'
          : 'grid gap-3 md:grid-cols-2 xl:grid-cols-3'
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
      className="grid min-h-28 gap-2 rounded-md border border-border bg-card p-4 text-card-foreground"
    >
      <span
        className="text-xs font-semibold uppercase tracking-normal text-muted-foreground"
        id={labelId}
      >
        {label}
      </span>
      <strong
        className="break-words text-2xl font-semibold leading-none tabular-nums"
        id={valueId}
      >
        {value}
      </strong>
      <small className="text-sm leading-relaxed text-muted-foreground">
        {detail}
      </small>
    </article>
  )
}

function BreakdownGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 lg:grid-cols-2">{children}</div>
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
      className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4 text-card-foreground"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-base font-semibold leading-none">{title}</h3>
        <Badge>{label}</Badge>
      </div>
      {children}
    </section>
  )
}

function StatusBreakdown({ summary }: { summary: ChatObservabilitySummary }) {
  const rows = getStatusBreakdown(summary.sessions.by_status)

  return (
    <BreakdownCard label={`${summary.sessions.total} total`} title="Status breakdown">
      {rows.length === 0 ? (
        <EmptyState className="p-3 text-left" data-slot-state="empty" role="status">
          No status data yet.
        </EmptyState>
      ) : (
        <DataList>
          {rows.map((row) => (
            <DataListItem
              className="flex flex-wrap items-center justify-between gap-3 border-0 bg-transparent p-2 shadow-none"
              key={row.status}
            >
              <div className="grid min-w-0 gap-1">
                <strong className="break-words text-sm font-semibold">
                  {row.status}
                </strong>
                <small className="text-xs text-muted-foreground">
                  {formatPercent(row.count, summary.sessions.total)}
                </small>
              </div>
              <Badge>{formatCount(row.count, 'session')}</Badge>
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
      label={`${summary.errors.top_messages.length} messages`}
      title="Error messages"
    >
      {summary.errors.top_messages.length === 0 ? (
        <EmptyState className="p-3 text-left" data-slot-state="empty" role="status">
          No error messages yet.
        </EmptyState>
      ) : (
        <DataList>
          {summary.errors.top_messages.map((error) => (
            <DataListItem
              className="flex flex-wrap items-center justify-between gap-3 border-0 bg-transparent p-2 shadow-none"
              key={error.message}
            >
              <strong className="break-words text-sm font-semibold">
                {error.message}
              </strong>
              <Badge>{formatCount(error.count, 'occurrence')}</Badge>
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
        title="Provider usage"
      >
        {summary.provider_usage.groups.length === 0 ? (
          <EmptyState className="p-3 text-left" data-slot-state="empty" role="status">
            No provider usage groups yet.
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
        title="Provider latency"
      >
        {summary.provider_usage.groups.length === 0 ? (
          <EmptyState className="p-3 text-left" data-slot-state="empty" role="status">
            No provider latency groups yet.
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
    <BreakdownCard label="Current filter" title="Session health">
      {total === 0 ? (
        <EmptyState className="p-3 text-left" data-slot-state="empty" role="status">
          No sessions in this filter window.
        </EmptyState>
      ) : (
        <div className="grid gap-2">
          <strong className="text-2xl font-semibold leading-none">
            {formatPercent(succeeded, total)} success
          </strong>
          <span className="text-sm text-muted-foreground">
            {formatCount(failed, 'failed session')}
          </span>
          <span className="text-sm text-muted-foreground">
            {formatCount(running, 'running session')}
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
  return value === null ? 'n/a' : formatUsd(value)
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}

function formatNullableNumber(value: number | null): string {
  return value === null ? 'n/a' : formatNumber(value)
}

function formatNullableMs(value: number | null): string {
  return value === null ? 'n/a' : `${value} ms`
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
