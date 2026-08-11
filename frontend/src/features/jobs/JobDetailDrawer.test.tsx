/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import type { BackgroundJobDetail } from '@/lib/apiClient'

import { JobDetailDrawer } from './JobDetailDrawer'

const detail: BackgroundJobDetail = {
  attempts: [
    {
      attempt_number: 1,
      error_code: null,
      error_message: null,
      finished_at: null,
      heartbeat_at: '2026-08-10T12:00:01Z',
      id: 'attempt-1',
      job_id: 'job-1',
      lease_expires_at: '2026-08-10T12:05:00Z',
      progress_json: { phase: 'leased' },
      started_at: '2026-08-10T12:00:00Z',
      status: 'running',
      trace_id: 'trace-1',
      worker_id: 'worker-1',
    },
  ],
  events: [
    {
      actor_id: 'worker-1',
      actor_type: 'worker',
      attempt_id: 'attempt-1',
      created_at: '2026-08-10T12:00:00Z',
      event_type: 'leased',
      extra_metadata: { api_key: '[REDACTED]' },
      id: 'event-1',
      job_id: 'job-1',
      message: 'leased',
    },
  ],
  job: {
    attempt_count: 1,
    cancellation_requested_at: null,
    concurrency_key: null,
    created_at: '2026-08-10T12:00:00Z',
    current_attempt_id: 'attempt-1',
    finished_at: null,
    handler_version: 1,
    id: 'job-1',
    idempotency_key: null,
    job_type: 'index_document_version',
    last_error: null,
    max_retries: 2,
    payload_json: { secret: '[REDACTED]' },
    priority: 0,
    queue_name: 'ingestion',
    result_json: null,
    retry_count: 0,
    run_after: '2026-08-10T12:00:00Z',
    schedule_id: null,
    scheduled_for: null,
    scope: 'workspace',
    status: 'running',
    updated_at: '2026-08-10T12:00:01Z',
    version: 2,
    workspace_id: 'workspace-1',
  },
}

test('shows redacted payload, progress, attempts, events and trace IDs', () => {
  render(<JobDetailDrawer detail={detail} onClose={vi.fn()} state="succeeded" />)

  const drawer = screen.getByRole('dialog', { name: 'Job Details' })
  expect(drawer.textContent).toContain('[REDACTED]')
  expect(drawer.textContent).toContain('leased')
  expect(drawer.textContent).toContain('trace-1')
  expect(screen.getByRole('button', { name: 'Close Job Details' })).toBeTruthy()
})
