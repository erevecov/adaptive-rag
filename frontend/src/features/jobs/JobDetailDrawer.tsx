import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import { StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '@/components/ui/table'
import { jobStatusLabel, jobStatusTone } from '@/features/jobs/jobPlatformUi'
import type { BackgroundJobDetail } from '@/lib/apiClient'
import { useFocusTrap } from '@/lib/focusTrap'

type DetailState = 'idle' | 'loading' | 'succeeded' | 'failed'

export function JobDetailDrawer({
  detail,
  error = null,
  onClose,
  state,
}: {
  detail: BackgroundJobDetail | null
  error?: string | null
  onClose(): void
  state: DetailState
}) {
  const drawerRef = useRef<HTMLElement>(null)
  useFocusTrap(drawerRef, true)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  const content = (
    <div
      className="fixed inset-0 z-[70] flex justify-end bg-[var(--overlay-backdrop)]"
      data-slot="job-detail-overlay"
    >
      <aside
        aria-label="Job Details"
        aria-modal="true"
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-border bg-card p-5 text-card-foreground shadow-2xl max-[680px]:p-2"
        ref={drawerRef}
        role="dialog"
      >
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Job Details</h2>
            {detail ? (
              <p className="break-all text-xs text-muted-foreground">
                {detail.job.id}
              </p>
            ) : null}
          </div>
          <Button onClick={onClose} type="button" variant="secondary">
            Close Job Details
          </Button>
        </header>

        {state === 'loading' ? <EmptyState>Loading job details…</EmptyState> : null}
        {state === 'failed' ? (
          <InlineFeedback role="alert" tone="danger">
            {error ?? 'Could not load job details.'}
          </InlineFeedback>
        ) : null}
        {detail ? <JobDetailContent detail={detail} /> : null}
      </aside>
    </div>
  )

  return typeof document === 'undefined' ? content : createPortal(content, document.body)
}

function JobDetailContent({ detail }: { detail: BackgroundJobDetail }) {
  const { job } = detail
  return (
    <div className="grid gap-5">
      <section aria-label="Job Summary" className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge tone={jobStatusTone(job.status)}>
            {jobStatusLabel(job.status)}
          </StatusBadge>
          <strong>{job.job_type}</strong>
          <span className="text-xs text-muted-foreground">{job.queue_name}</span>
        </div>
        <DefinitionList
          entries={[
            ['Handler', `${job.job_type}@${job.handler_version}`],
            ['Run after', formatTimestamp(job.run_after)],
            ['Attempts', `${job.attempt_count}`],
            ['Retries', `${job.retry_count}/${job.max_retries}`],
            ['Version', `${job.version}`],
            ['Concurrency key', job.concurrency_key ?? 'None'],
          ]}
        />
        {job.last_error ? (
          <InlineFeedback tone="danger">
            {job.last_error.code ?? 'Job error'}: {job.last_error.message ?? 'Unknown'}
            {job.last_error.trace_id ? ` · ${job.last_error.trace_id}` : ''}
          </InlineFeedback>
        ) : null}
      </section>

      <JsonSection label="Payload" value={job.payload_json} />
      <JsonSection label="Result" value={job.result_json} />

      <section aria-labelledby="job-attempts-title" className="grid gap-2">
        <h3 className="font-semibold" id="job-attempts-title">Attempts</h3>
        {detail.attempts.length === 0 ? (
          <EmptyState>No attempts recorded.</EmptyState>
        ) : (
          <TableScroll>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Worker</TableHead>
                  <TableHead>Trace</TableHead>
                  <TableHead>Progress</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.attempts.map((attempt) => (
                  <TableRow key={attempt.id}>
                    <TableCell>{attempt.attempt_number}</TableCell>
                    <TableCell>{attempt.status}</TableCell>
                    <TableCell className="max-w-36 truncate">{attempt.worker_id}</TableCell>
                    <TableCell>{attempt.trace_id ?? '—'}</TableCell>
                    <TableCell>
                      <code>{compactJson(attempt.progress_json)}</code>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        )}
      </section>

      <section aria-labelledby="job-events-title" className="grid gap-2">
        <h3 className="font-semibold" id="job-events-title">Events</h3>
        {detail.events.length === 0 ? (
          <EmptyState>No events recorded.</EmptyState>
        ) : (
          <ol className="grid gap-2">
            {detail.events.map((event) => (
              <li className="rounded-md border border-border p-3" key={event.id}>
                <div className="flex flex-wrap justify-between gap-2">
                  <strong>{event.event_type}</strong>
                  <time>{formatTimestamp(event.created_at)}</time>
                </div>
                {event.message ? <p>{event.message}</p> : null}
                {event.extra_metadata ? (
                  <pre className="mt-2 overflow-auto text-xs">
                    {prettyJson(event.extra_metadata)}
                  </pre>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}

function DefinitionList({ entries }: { entries: Array<[string, string]> }) {
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
      {entries.map(([label, value]) => (
        <div className="contents" key={label}>
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-all">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function JsonSection({ label, value }: { label: string; value: unknown }) {
  return (
    <section aria-label={label} className="grid gap-2">
      <h3 className="font-semibold">{label}</h3>
      <pre className="max-h-64 overflow-auto rounded-md border border-border bg-muted/20 p-3 text-xs">
        {prettyJson(value)}
      </pre>
    </section>
  )
}

function compactJson(value: unknown): string {
  if (value === null || value === undefined) return '—'
  return JSON.stringify(value)
}

function prettyJson(value: unknown): string {
  if (value === null || value === undefined) return 'null'
  return JSON.stringify(value, null, 2)
}

function formatTimestamp(value: string | null): string {
  if (value === null) return '—'
  const timestamp = new Date(value)
  return Number.isNaN(timestamp.getTime()) ? value : timestamp.toLocaleString()
}
