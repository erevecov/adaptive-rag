/** @vitest-environment jsdom */
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'

import type {
  ApiClient,
  BackgroundJob,
  BackgroundJobDetail,
  JobSchedule,
} from '@/lib/apiClient'

import { JobPlatformPanel } from './JobPlatformView'

const job: BackgroundJob = {
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
}

const detail: BackgroundJobDetail = {
  attempts: [],
  events: [
    {
      actor_id: 'worker-1',
      actor_type: 'worker',
      attempt_id: 'attempt-1',
      created_at: '2026-08-10T12:00:00Z',
      event_type: 'leased',
      extra_metadata: { secret: '[REDACTED]' },
      id: 'event-1',
      job_id: job.id,
      message: 'leased',
    },
  ],
  job,
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

test('filters jobs and opens an event detail drawer', async () => {
  const client = clientStub()
  render(
    <JobPlatformPanel
      activeSubmodule="jobs"
      apiClient={client}
      canAdminWorkspace
      isSuperadmin={false}
      workspaceId="workspace-1"
    />,
  )

  await screen.findByRole('button', { name: /index_document_version/i })
  fireEvent.change(screen.getByLabelText('Status'), {
    target: { value: 'running' },
  })
  await userEvent.click(
    screen.getByRole('button', { name: /index_document_version/i }),
  )

  await waitFor(() =>
    expect(client.listBackgroundJobs).toHaveBeenLastCalledWith(
      'workspace-1',
      expect.objectContaining({ status: 'running' }),
    ),
  )
  const drawer = await screen.findByRole('dialog', { name: 'Job Details' })
  expect(drawer.textContent).toContain('leased')
  expect(drawer.textContent).toContain('[REDACTED]')
})

test('admin confirms cancellation while a viewer sees no mutations', async () => {
  const user = userEvent.setup()
  const adminClient = clientStub()
  const { unmount } = render(
    <JobPlatformPanel
      activeSubmodule="jobs"
      apiClient={adminClient}
      canAdminWorkspace
      isSuperadmin={false}
      workspaceId="workspace-1"
    />,
  )
  await screen.findByRole('button', { name: 'Cancel Job' })
  await user.click(screen.getByRole('button', { name: 'Cancel Job' }))
  await user.click(screen.getByRole('button', { name: 'Confirm Cancellation' }))
  expect(adminClient.cancelBackgroundJob).toHaveBeenCalledWith(
    'workspace-1',
    job.id,
    { version: job.version },
  )

  unmount()
  render(
    <JobPlatformPanel
      activeSubmodule="jobs"
      apiClient={clientStub()}
      canAdminWorkspace={false}
      isSuperadmin={false}
      workspaceId="workspace-1"
    />,
  )
  await screen.findByRole('button', { name: /index_document_version/i })
  expect(screen.queryByRole('button', { name: /cancel|retry|unblock/i })).toBeNull()
})

test('polls only while visible and removes its timers on unmount', async () => {
  vi.useFakeTimers()
  setDocumentVisibility('visible')
  const client = clientStub()
  const { unmount } = render(
    <JobPlatformPanel
      activeSubmodule="jobs"
      apiClient={client}
      canAdminWorkspace={false}
      isSuperadmin={false}
      pollIntervalMs={5_000}
      workspaceId="workspace-1"
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(10_000)
  })
  expect(client.listBackgroundJobs).toHaveBeenCalledTimes(3)

  setDocumentVisibility('hidden')
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10_000)
  })
  expect(client.listBackgroundJobs).toHaveBeenCalledTimes(3)

  unmount()
  expect(vi.getTimerCount()).toBe(0)
})

test('keeps archived schedules visible without mutable actions', async () => {
  const archivedSchedule: JobSchedule = {
    archived_at: '2026-08-10T13:00:00Z',
    concurrency_key: null,
    created_at: '2026-08-10T12:00:00Z',
    cron_expression: '0 * * * *',
    description: null,
    handler_version: 1,
    id: 'schedule-1',
    job_type: 'ingest_source',
    last_scheduled_for: null,
    max_catch_up: 1,
    misfire_policy: 'run_once',
    name: 'Archived ingestion',
    next_run_at: '2026-08-10T14:00:00Z',
    paused_at: null,
    payload_json: { source_id: 'source-1' },
    priority: 0,
    queue_name: 'ingestion',
    scope: 'workspace',
    timezone: 'UTC',
    updated_at: '2026-08-10T13:00:00Z',
    version: 2,
    workspace_id: 'workspace-1',
  }
  const client = clientStub()
  client.listJobSchedules = vi.fn(async () => ({ items: [archivedSchedule] }))

  render(
    <JobPlatformPanel
      activeSubmodule="schedules"
      apiClient={client}
      canAdminWorkspace
      isSuperadmin={false}
      workspaceId="workspace-1"
    />,
  )

  const row = await screen.findByRole('row', { name: /Archived ingestion/ })
  expect(within(row).getByText('Archived')).toBeTruthy()
  expect(within(row).queryByRole('button')).toBeNull()
})

function clientStub(): ApiClient {
  return {
    cancelBackgroundJob: vi.fn(async () => ({ ...job, status: 'cancelled' })),
    getBackgroundJob: vi.fn(async () => detail),
    listBackgroundJobs: vi.fn(async () => ({ items: [job], next_cursor: null })),
    listJobSchedules: vi.fn(async () => ({ items: [] })),
    listJobQueues: vi.fn(async () => []),
    listJobWorkers: vi.fn(async () => []),
    getJobMetrics: vi.fn(async () => ({
      generated_at: '2026-08-10T12:00:00Z',
      queues: [],
      scheduler_lag_seconds: 0,
      unroutable_queued: 0,
      workers: { draining: 0, live: 0, stale: 0 },
    })),
    listJobHandlers: vi.fn(async () => []),
  } as unknown as ApiClient
}

function setDocumentVisibility(value: 'hidden' | 'visible') {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    value,
  })
  document.dispatchEvent(new Event('visibilitychange'))
}
