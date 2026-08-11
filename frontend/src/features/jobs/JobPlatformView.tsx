import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Input } from '@/components/ui/control'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
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
  encodeJobFilters,
  jobActions,
  jobStatusLabel,
  jobStatusTone,
  type JobAction,
  type JobFilters,
  type JobsSubmodule,
} from '@/features/jobs/jobPlatformUi'
import {
  ApiClientError,
  type ApiClient,
  type BackgroundJob,
  type BackgroundJobDetail,
  type ConfigureJobQueueBody,
  type CreateJobScheduleBody,
  type EnqueueBackgroundJobBody,
  type JobMetrics,
  type JobHandler,
  type JobQueue,
  type JobSchedule,
  type JobWorker,
  type UpdateJobScheduleBody,
} from '@/lib/apiClient'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'

import { JobDetailDrawer } from './JobDetailDrawer'

type LoadState = 'idle' | 'loading' | 'succeeded' | 'failed'
type Confirmation =
  | { kind: JobAction; job: BackgroundJob }
  | { kind: 'archive-schedule' | 'pause-schedule'; schedule: JobSchedule }
  | { kind: 'pause-queue'; queue: JobQueue }

const POLL_INTERVAL_MS = 5_000
const DEFAULT_FILTERS: JobFilters = {
  cursor: null,
  job_type: null,
  limit: 50,
  queue: null,
  status: null,
}

export function JobPlatformPanel({
  activeSubmodule,
  apiClient,
  canAdminWorkspace,
  isSuperadmin,
  pollIntervalMs = POLL_INTERVAL_MS,
  workspaceId,
}: {
  activeSubmodule: JobsSubmodule
  apiClient: ApiClient
  canAdminWorkspace: boolean
  isSuperadmin: boolean
  pollIntervalMs?: number
  workspaceId: string
}) {
  const [filters, setFilters] = useState<JobFilters>(DEFAULT_FILTERS)
  const [jobs, setJobs] = useState<BackgroundJob[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [cursorHistory, setCursorHistory] = useState<Array<string | null>>([])
  const [schedules, setSchedules] = useState<JobSchedule[]>([])
  const [queues, setQueues] = useState<JobQueue[]>([])
  const [workers, setWorkers] = useState<JobWorker[]>([])
  const [metrics, setMetrics] = useState<JobMetrics | null>(null)
  const [handlers, setHandlers] = useState<JobHandler[]>([])
  const [state, setState] = useState<LoadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [detail, setDetail] = useState<BackgroundJobDetail | null>(null)
  const [detailState, setDetailState] = useState<LoadState>('idle')
  const [detailError, setDetailError] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [mutationPending, setMutationPending] = useState(false)
  const refreshGeneration = useRef(0)
  const feedbackTimer = useRef<number | null>(null)

  const jobParams = useMemo(
    () => ({
      cursor: filters.cursor,
      job_type: filters.job_type,
      limit: filters.limit,
      queue: filters.queue,
      status: filters.status,
    }),
    [filters],
  )

  const refresh = useCallback(async () => {
    const generation = ++refreshGeneration.current
    setState((current) => (current === 'succeeded' ? current : 'loading'))
    setError(null)
    try {
      if (
        workspaceId.trim().length === 0 &&
        (activeSubmodule === 'jobs' || activeSubmodule === 'schedules')
      ) {
        setJobs([])
        setSchedules([])
        setState('succeeded')
        return
      }
      if (activeSubmodule === 'jobs') {
        const [response, handlerRows] = await Promise.all([
          apiClient.listBackgroundJobs(workspaceId, jobParams),
          canAdminWorkspace
            ? apiClient.listJobHandlers(workspaceId)
            : Promise.resolve([]),
        ])
        if (generation !== refreshGeneration.current) return
        setJobs(response.items)
        setNextCursor(response.next_cursor)
        setHandlers(handlerRows)
      } else if (activeSubmodule === 'schedules') {
        const [response, handlerRows] = await Promise.all([
          apiClient.listJobSchedules(workspaceId),
          canAdminWorkspace
            ? apiClient.listJobHandlers(workspaceId)
            : Promise.resolve([]),
        ])
        if (generation !== refreshGeneration.current) return
        setSchedules(response.items)
        setHandlers(handlerRows)
      } else if (activeSubmodule === 'queues' && isSuperadmin) {
        const [queueRows, metricSnapshot] = await Promise.all([
          apiClient.listJobQueues(),
          apiClient.getJobMetrics(),
        ])
        if (generation !== refreshGeneration.current) return
        setQueues(queueRows)
        setMetrics(metricSnapshot)
      } else if (activeSubmodule === 'workers' && isSuperadmin) {
        const [workerRows, metricSnapshot] = await Promise.all([
          apiClient.listJobWorkers(),
          apiClient.getJobMetrics(),
        ])
        if (generation !== refreshGeneration.current) return
        setWorkers(workerRows)
        setMetrics(metricSnapshot)
      }
      if (generation === refreshGeneration.current) setState('succeeded')
    } catch (reason) {
      if (generation !== refreshGeneration.current) return
      setState('failed')
      setError(safeErrorMessage(reason))
    }
  }, [
    activeSubmodule,
    apiClient,
    canAdminWorkspace,
    isSuperadmin,
    jobParams,
    workspaceId,
  ])

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refresh(), 0)
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh()
    }, pollIntervalMs)
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') void refresh()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      refreshGeneration.current += 1
      window.clearTimeout(initialRefresh)
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [pollIntervalMs, refresh])

  useEffect(() => {
    if (selectedJobId === null) return
    let obsolete = false
    void apiClient
      .getBackgroundJob(workspaceId, selectedJobId)
      .then((response) => {
        if (obsolete) return
        setDetail(response)
        setDetailState('succeeded')
      })
      .catch((reason) => {
        if (obsolete) return
        setDetailState('failed')
        setDetailError(safeErrorMessage(reason))
      })
    return () => {
      obsolete = true
    }
  }, [apiClient, selectedJobId, workspaceId])

  useEffect(
    () => () => {
      if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current)
    },
    [],
  )

  function changeFilters(changes: Partial<JobFilters>) {
    const next = { ...filters, ...changes, cursor: null }
    setCursorHistory([])
    setFilters(next)
    replaceJobQuery(next)
  }

  function openJob(jobId: string) {
    setDetail(null)
    setDetailError(null)
    setDetailState('loading')
    setSelectedJobId(jobId)
  }

  function closeJob() {
    setSelectedJobId(null)
    setDetail(null)
    setDetailError(null)
    setDetailState('idle')
  }

  function showFeedback(message: string) {
    setFeedback(message)
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current)
    feedbackTimer.current = window.setTimeout(() => setFeedback(null), 4_000)
  }

  async function runMutation(operation: () => Promise<unknown>, success: string) {
    setMutationPending(true)
    try {
      await operation()
      showFeedback(success)
    } catch (reason) {
      showFeedback(
        reason instanceof ApiClientError && reason.status === 409
          ? 'State changed on the server. The latest record has been loaded.'
          : safeErrorMessage(reason),
      )
    } finally {
      setMutationPending(false)
      setConfirmation(null)
      await refresh()
      if (selectedJobId !== null) {
        try {
          setDetail(await apiClient.getBackgroundJob(workspaceId, selectedJobId))
        } catch {
          setSelectedJobId(null)
        }
      }
    }
  }

  function confirmMutation() {
    if (confirmation === null) return
    if ('job' in confirmation) {
      const { job, kind } = confirmation
      if (kind === 'cancel') {
        void runMutation(
          () => apiClient.cancelBackgroundJob(workspaceId, job.id, { version: job.version }),
          'Cancellation requested.',
        )
      } else if (kind === 'retry') {
        void runMutation(
          () =>
            apiClient.retryBackgroundJob(workspaceId, job.id, {
              reset_retry_count: true,
              version: job.version,
            }),
          'Job queued for retry.',
        )
      } else {
        void runMutation(
          () => apiClient.unblockBackgroundJob(workspaceId, job.id, { version: job.version }),
          'Job unblocked.',
        )
      }
    } else if ('schedule' in confirmation) {
      const { schedule } = confirmation
      if (confirmation.kind === 'archive-schedule') {
        void runMutation(
          () =>
            apiClient.archiveJobSchedule(workspaceId, schedule.id, {
              version: schedule.version,
            }),
          'Schedule archived.',
        )
      } else {
        void runMutation(
          () =>
            apiClient.pauseJobSchedule(workspaceId, schedule.id, {
              version: schedule.version,
            }),
          'Schedule paused.',
        )
      }
    } else {
      void runMutation(
        () =>
          apiClient.configureJobQueue(confirmation.queue.name, {
            paused: true,
            version: confirmation.queue.version,
          }),
        'Queue paused.',
      )
    }
  }

  const unauthorizedGlobal =
    (activeSubmodule === 'queues' || activeSubmodule === 'workers') && !isSuperadmin

  return (
    <section aria-label="Background Jobs Console" className="grid gap-4">
      <header>
        <h2 className="text-2xl font-semibold">{submoduleTitle(activeSubmodule)}</h2>
        <p className="text-sm text-muted-foreground">
          Durable PostgreSQL jobs, schedules, queues, and worker presence.
        </p>
      </header>
      {feedback ? (
        <div className="fixed right-4 top-4 z-[90] rounded-md border border-border bg-card p-3 shadow-lg" role="status">
          {feedback}
        </div>
      ) : null}
      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}
      {unauthorizedGlobal ? (
        <InlineFeedback tone="danger">Superadmin access is required.</InlineFeedback>
      ) : activeSubmodule === 'jobs' ? (
        <JobsView
          canAdmin={canAdminWorkspace}
          cursorHistory={cursorHistory}
          filters={filters}
          handlers={handlers}
          jobs={jobs}
          nextCursor={nextCursor}
          onAction={(action, selectedJob) => setConfirmation({ kind: action, job: selectedJob })}
          onFiltersChange={changeFilters}
          onEnqueue={(body) =>
            runMutation(
              () => apiClient.enqueueBackgroundJob(workspaceId, body),
              'Job queued.',
            )
          }
          onNext={() => {
            if (nextCursor === null) return
            setCursorHistory((current) => [...current, filters.cursor])
            setFilters((current) => ({ ...current, cursor: nextCursor }))
          }}
          onOpen={openJob}
          onPrevious={() => {
            const previous = cursorHistory.at(-1) ?? null
            setCursorHistory((current) => current.slice(0, -1))
            setFilters((current) => ({ ...current, cursor: previous }))
          }}
          state={state}
        />
      ) : activeSubmodule === 'schedules' ? (
        <SchedulesView
          canAdmin={canAdminWorkspace}
          handlers={handlers}
          onArchive={(schedule) => setConfirmation({ kind: 'archive-schedule', schedule })}
          onPause={(schedule) => setConfirmation({ kind: 'pause-schedule', schedule })}
          onCreate={(body) =>
            runMutation(
              () => apiClient.createJobSchedule(workspaceId, body),
              'Schedule created.',
            )
          }
          onResume={(schedule) =>
            void runMutation(
              () => apiClient.resumeJobSchedule(workspaceId, schedule.id, { version: schedule.version }),
              'Schedule resumed.',
            )
          }
          onRunNow={(schedule) =>
            void runMutation(
              () => apiClient.runJobScheduleNow(workspaceId, schedule.id, { version: schedule.version }),
              'Schedule run queued.',
            )
          }
          onUpdate={(schedule, body) =>
            runMutation(
              () => apiClient.updateJobSchedule(workspaceId, schedule.id, body),
              'Schedule updated.',
            )
          }
          schedules={schedules}
          state={state}
        />
      ) : activeSubmodule === 'queues' ? (
        <QueuesView
          metrics={metrics}
          onPause={(queue) => setConfirmation({ kind: 'pause-queue', queue })}
          onConfigure={(queue, body) =>
            runMutation(
              () => apiClient.configureJobQueue(queue.name, body),
              'Queue configuration saved.',
            )
          }
          onResume={(queue) =>
            void runMutation(
              () => apiClient.configureJobQueue(queue.name, { paused: false, version: queue.version }),
              'Queue resumed.',
            )
          }
          queues={queues}
          state={state}
        />
      ) : (
        <WorkersView metrics={metrics} state={state} workers={workers} />
      )}

      {selectedJobId !== null ? (
        <JobDetailDrawer
          detail={detail}
          error={detailError}
          onClose={closeJob}
          state={detailState}
        />
      ) : null}
      {confirmation ? (
        <ConfirmationDialog
          confirmation={confirmation}
          disabled={mutationPending}
          onCancel={() => setConfirmation(null)}
          onConfirm={confirmMutation}
        />
      ) : null}
    </section>
  )
}

function JobsView({
  canAdmin,
  cursorHistory,
  filters,
  handlers,
  jobs,
  nextCursor,
  onAction,
  onFiltersChange,
  onEnqueue,
  onNext,
  onOpen,
  onPrevious,
  state,
}: {
  canAdmin: boolean
  cursorHistory: Array<string | null>
  filters: JobFilters
  handlers: JobHandler[]
  jobs: BackgroundJob[]
  nextCursor: string | null
  onAction(action: JobAction, job: BackgroundJob): void
  onFiltersChange(filters: Partial<JobFilters>): void
  onEnqueue(body: EnqueueBackgroundJobBody): void
  onNext(): void
  onOpen(jobId: string): void
  onPrevious(): void
  state: LoadState
}) {
  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>Jobs</PanelTitle>
        <PanelDescription>Filter, inspect, cancel, retry, or unblock durable work.</PanelDescription>
      </PanelHeader>
      <PanelBody className="grid gap-3">
        {canAdmin ? <EnqueueJobForm handlers={handlers} onSubmit={onEnqueue} /> : null}
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="grid gap-1 text-xs">
            Status
            <select
              aria-label="Status"
              className="h-9 rounded-md border border-input bg-background px-3"
              onChange={(event) => onFiltersChange({ status: event.target.value || null })}
              value={filters.status ?? ''}
            >
              <option value="">All statuses</option>
              {['queued', 'running', 'blocked', 'dead_letter', 'succeeded', 'cancelled'].map(
                (status) => <option key={status} value={status}>{jobStatusLabel(status)}</option>,
              )}
            </select>
          </label>
          <label className="grid gap-1 text-xs">
            Queue
            <Input
              aria-label="Queue"
              onChange={(event) => onFiltersChange({ queue: event.target.value || null })}
              value={filters.queue ?? ''}
            />
          </label>
          <label className="grid gap-1 text-xs">
            Handler
            <Input
              aria-label="Handler"
              onChange={(event) => onFiltersChange({ job_type: event.target.value || null })}
              value={filters.job_type ?? ''}
            />
          </label>
        </div>
        {state === 'loading' && jobs.length === 0 ? <EmptyState>Loading jobs…</EmptyState> : null}
        {state !== 'loading' && jobs.length === 0 ? <EmptyState>No jobs match these filters.</EmptyState> : null}
        {jobs.length > 0 ? (
          <TableScroll>
            <Table>
              <TableHeader><TableRow>
                <TableHead>Job</TableHead><TableHead>Status</TableHead><TableHead>Queue</TableHead>
                <TableHead>Run after</TableHead><TableHead>Attempts</TableHead><TableHead>Actions</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell><Button onClick={() => onOpen(job.id)} size="sm" variant="ghost">{job.job_type} · {job.id.slice(0, 8)}</Button></TableCell>
                    <TableCell><StatusBadge tone={jobStatusTone(job.status)}>{jobStatusLabel(job.status)}</StatusBadge></TableCell>
                    <TableCell>{job.queue_name}</TableCell>
                    <TableCell>{formatTimestamp(job.run_after)}</TableCell>
                    <TableCell className={tableNumericClass}>{job.attempt_count}</TableCell>
                    <TableCell><div className="flex gap-1">
                      {jobActions(job.status, canAdmin).map((action) => (
                        <Button key={action} onClick={() => onAction(action, job)} size="sm" variant={action === 'cancel' ? 'danger' : 'secondary'}>
                          {actionLabel(action)} Job
                        </Button>
                      ))}
                    </div></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button disabled={cursorHistory.length === 0} onClick={onPrevious} variant="secondary">Previous</Button>
          <Button disabled={nextCursor === null} onClick={onNext} variant="secondary">Next</Button>
        </div>
      </PanelBody>
    </Panel>
  )
}

function EnqueueJobForm({
  handlers,
  onSubmit,
}: {
  handlers: JobHandler[]
  onSubmit(body: EnqueueBackgroundJobBody): void
}) {
  const [open, setOpen] = useState(false)
  const [jobType, setJobType] = useState('')
  const [payload, setPayload] = useState('{}')
  const [idempotencyKey, setIdempotencyKey] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  function submit() {
    try {
      const parsed = JSON.parse(payload) as unknown
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('Payload must be a JSON object.')
      }
      if (jobType.length === 0) throw new Error('Select a handler.')
      setValidationError(null)
      onSubmit({
        idempotency_key: idempotencyKey.trim() || null,
        job_type: jobType,
        payload: parsed as Record<string, unknown>,
      })
      setOpen(false)
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : 'Invalid job payload.',
      )
    }
  }

  if (!open) {
    return <Button className="w-fit" onClick={() => setOpen(true)}>Enqueue Job</Button>
  }
  return (
    <div className="grid gap-2 rounded-md border border-border p-3" role="group" aria-label="Enqueue Job">
      <label className="grid gap-1 text-xs">Handler
        <select aria-label="Job Handler" className="h-9 rounded-md border border-input bg-background px-3" onChange={(event) => setJobType(event.target.value)} value={jobType}>
          <option value="">Select handler</option>
          {handlers.map((handler) => <option key={`${handler.name}@${handler.version}`} value={handler.name}>{handler.name}@{handler.version}</option>)}
        </select>
      </label>
      <label className="grid gap-1 text-xs">Payload JSON
        <textarea aria-label="Job Payload JSON" className="min-h-24 rounded-md border border-input bg-background p-2 font-mono text-sm" onChange={(event) => setPayload(event.target.value)} value={payload} />
      </label>
      <label className="grid gap-1 text-xs">Idempotency key
        <Input aria-label="Idempotency Key" onChange={(event) => setIdempotencyKey(event.target.value)} value={idempotencyKey} />
      </label>
      {validationError ? <InlineFeedback tone="danger">{validationError}</InlineFeedback> : null}
      <div className="flex justify-end gap-2"><Button onClick={() => setOpen(false)} variant="secondary">Cancel Enqueue</Button><Button onClick={submit}>Queue Job</Button></div>
    </div>
  )
}

function SchedulesView({
  canAdmin,
  handlers,
  onArchive,
  onCreate,
  onPause,
  onResume,
  onRunNow,
  onUpdate,
  schedules,
  state,
}: {
  canAdmin: boolean
  handlers: JobHandler[]
  onArchive(schedule: JobSchedule): void
  onCreate(body: CreateJobScheduleBody): void
  onPause(schedule: JobSchedule): void
  onResume(schedule: JobSchedule): void
  onRunNow(schedule: JobSchedule): void
  onUpdate(schedule: JobSchedule, body: UpdateJobScheduleBody): void
  schedules: JobSchedule[]
  state: LoadState
}) {
  const [editing, setEditing] = useState<JobSchedule | 'new' | null>(null)
  return (
    <Panel><PanelHeader><PanelTitle>Schedules</PanelTitle><PanelDescription>Timezone-aware cron schedules with durable misfire policy.</PanelDescription></PanelHeader>
      <PanelBody className="grid gap-3">
        {canAdmin && editing === null ? <Button className="w-fit" onClick={() => setEditing('new')}>Create Schedule</Button> : null}
        {editing !== null ? <ScheduleForm
          handlers={handlers}
          schedule={editing === 'new' ? null : editing}
          onCancel={() => setEditing(null)}
          onSubmit={(body) => {
            if (editing === 'new') onCreate(body as CreateJobScheduleBody)
            else onUpdate(editing, body as UpdateJobScheduleBody)
            setEditing(null)
          }}
        /> : null}
        {schedules.length === 0 ? <EmptyState>{state === 'loading' ? 'Loading schedules…' : 'No schedules configured.'}</EmptyState> : (
        <TableScroll><Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Cron</TableHead><TableHead>Policy</TableHead><TableHead>Next</TableHead><TableHead>Last</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>{schedules.map((schedule) => <TableRow key={schedule.id}>
            <TableCell><strong>{schedule.name}</strong><div className="text-xs text-muted-foreground">{schedule.job_type}</div></TableCell>
            <TableCell><code>{schedule.cron_expression}</code> · {schedule.timezone}</TableCell>
            <TableCell>{schedule.misfire_policy}</TableCell><TableCell>{formatTimestamp(schedule.next_run_at)}</TableCell><TableCell>{formatTimestamp(schedule.last_scheduled_for)}</TableCell>
            <TableCell>{canAdmin ? <div className="flex flex-wrap gap-1">
              <Button onClick={() => setEditing(schedule)} size="sm" variant="secondary">Edit Schedule</Button>
              {schedule.paused_at ? <Button onClick={() => onResume(schedule)} size="sm" variant="secondary">Resume Schedule</Button> : <Button onClick={() => onPause(schedule)} size="sm" variant="secondary">Pause Schedule</Button>}
              <Button onClick={() => onRunNow(schedule)} size="sm" variant="secondary">Run Now</Button>
              <Button onClick={() => onArchive(schedule)} size="sm" variant="danger">Archive Schedule</Button>
            </div> : null}</TableCell>
          </TableRow>)}</TableBody>
        </Table></TableScroll>
      )}</PanelBody>
    </Panel>
  )
}

function ScheduleForm({
  handlers,
  onCancel,
  onSubmit,
  schedule,
}: {
  handlers: JobHandler[]
  onCancel(): void
  onSubmit(body: CreateJobScheduleBody | UpdateJobScheduleBody): void
  schedule: JobSchedule | null
}) {
  const [name, setName] = useState(schedule?.name ?? '')
  const [jobType, setJobType] = useState(schedule?.job_type ?? '')
  const [payload, setPayload] = useState(
    JSON.stringify(schedule?.payload_json ?? {}, null, 2),
  )
  const [cron, setCron] = useState(schedule?.cron_expression ?? '0 * * * *')
  const [timezone, setTimezone] = useState(schedule?.timezone ?? 'UTC')
  const [misfirePolicy, setMisfirePolicy] = useState<
    'catch_up' | 'run_once' | 'skip'
  >(schedule?.misfire_policy ?? 'run_once')
  const [validationError, setValidationError] = useState<string | null>(null)

  function submit() {
    try {
      const parsed = JSON.parse(payload) as unknown
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('Payload must be a JSON object.')
      }
      if (name.trim().length === 0) throw new Error('Name is required.')
      if (schedule === null && jobType.length === 0) {
        throw new Error('Select a handler.')
      }
      const common = {
        cron_expression: cron,
        misfire_policy: misfirePolicy,
        name: name.trim(),
        payload: parsed as Record<string, unknown>,
        timezone,
      }
      onSubmit(
        schedule === null
          ? { ...common, job_type: jobType }
          : { ...common, version: schedule.version },
      )
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : 'Invalid schedule.',
      )
    }
  }

  return (
    <div aria-label={schedule ? 'Edit Schedule' : 'Create Schedule'} className="grid gap-2 rounded-md border border-border p-3" role="group">
      <label className="grid gap-1 text-xs">Name<Input aria-label="Schedule Name" onChange={(event) => setName(event.target.value)} value={name} /></label>
      {schedule === null ? <label className="grid gap-1 text-xs">Handler<select aria-label="Schedule Handler" className="h-9 rounded-md border border-input bg-background px-3" onChange={(event) => setJobType(event.target.value)} value={jobType}><option value="">Select handler</option>{handlers.map((handler) => <option key={`${handler.name}@${handler.version}`} value={handler.name}>{handler.name}@{handler.version}</option>)}</select></label> : null}
      <label className="grid gap-1 text-xs">Cron<Input aria-label="Cron Expression" onChange={(event) => setCron(event.target.value)} value={cron} /></label>
      <label className="grid gap-1 text-xs">Timezone<Input aria-label="Schedule Timezone" onChange={(event) => setTimezone(event.target.value)} value={timezone} /></label>
      <label className="grid gap-1 text-xs">Misfire policy<select aria-label="Misfire Policy" className="h-9 rounded-md border border-input bg-background px-3" onChange={(event) => setMisfirePolicy(event.target.value as typeof misfirePolicy)} value={misfirePolicy}><option value="skip">Skip</option><option value="run_once">Run once</option><option value="catch_up">Catch up</option></select></label>
      <label className="grid gap-1 text-xs">Payload JSON<textarea aria-label="Schedule Payload JSON" className="min-h-24 rounded-md border border-input bg-background p-2 font-mono text-sm" onChange={(event) => setPayload(event.target.value)} value={payload} /></label>
      {validationError ? <InlineFeedback tone="danger">{validationError}</InlineFeedback> : null}
      <div className="flex justify-end gap-2"><Button onClick={onCancel} variant="secondary">Cancel Schedule</Button><Button onClick={submit}>Save Schedule</Button></div>
    </div>
  )
}

function QueuesView({ metrics, onConfigure, onPause, onResume, queues, state }: { metrics: JobMetrics | null; onConfigure(queue: JobQueue, body: ConfigureJobQueueBody): void; onPause(queue: JobQueue): void; onResume(queue: JobQueue): void; queues: JobQueue[]; state: LoadState }) {
  const [editing, setEditing] = useState<JobQueue | null>(null)
  return <Panel><PanelHeader><PanelTitle>Queues</PanelTitle><PanelDescription>Global depth, capacity, and admission controls.</PanelDescription></PanelHeader><PanelBody className="grid gap-3">
    {editing ? <QueueConfigurationForm onCancel={() => setEditing(null)} onSubmit={(body) => { onConfigure(editing, body); setEditing(null) }} queue={editing} /> : null}
    {queues.length === 0 ? <EmptyState>{state === 'loading' ? 'Loading queues…' : 'No queues configured.'}</EmptyState> : <TableScroll><Table><TableHeader><TableRow><TableHead>Queue</TableHead><TableHead>Depth</TableHead><TableHead>Running</TableHead><TableHead>Oldest eligible</TableHead><TableHead>Capacity</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader><TableBody>
      {queues.map((queue) => { const summary = metrics?.queues.find((item) => item.name === queue.name); return <TableRow key={queue.name}><TableCell><strong>{queue.name}</strong>{queue.paused_at ? <Badge tone="warning">Paused</Badge> : null}</TableCell><TableCell>{summary?.queued ?? 0}</TableCell><TableCell>{summary?.running ?? 0}</TableCell><TableCell>{formatAge(summary?.oldest_eligible_age_seconds ?? null)}</TableCell><TableCell>{queue.global_concurrency_limit ?? 'Unlimited'} / workspace {queue.workspace_concurrency_limit ?? 'Unlimited'}</TableCell><TableCell><div className="flex gap-1"><Button onClick={() => setEditing(queue)} size="sm" variant="secondary">Configure Queue</Button>{queue.paused_at ? <Button onClick={() => onResume(queue)} size="sm" variant="secondary">Resume Queue</Button> : <Button onClick={() => onPause(queue)} size="sm" variant="danger">Pause Queue</Button>}</div></TableCell></TableRow> })}
    </TableBody></Table></TableScroll>}
  </PanelBody></Panel>
}

function QueueConfigurationForm({ onCancel, onSubmit, queue }: { onCancel(): void; onSubmit(body: ConfigureJobQueueBody): void; queue: JobQueue }) {
  const [globalLimit, setGlobalLimit] = useState(queue.global_concurrency_limit?.toString() ?? '')
  const [workspaceLimit, setWorkspaceLimit] = useState(queue.workspace_concurrency_limit?.toString() ?? '')
  const [leaseSeconds, setLeaseSeconds] = useState(queue.default_lease_seconds.toString())
  return <div aria-label="Configure Queue" className="grid gap-2 rounded-md border border-border p-3" role="group"><strong>Configure {queue.name}</strong>
    <label className="grid gap-1 text-xs">Global concurrency<Input aria-label="Global Concurrency Limit" min={1} onChange={(event) => setGlobalLimit(event.target.value)} type="number" value={globalLimit} /></label>
    <label className="grid gap-1 text-xs">Workspace concurrency<Input aria-label="Workspace Concurrency Limit" min={1} onChange={(event) => setWorkspaceLimit(event.target.value)} type="number" value={workspaceLimit} /></label>
    <label className="grid gap-1 text-xs">Default lease seconds<Input aria-label="Default Lease Seconds" max={3600} min={15} onChange={(event) => setLeaseSeconds(event.target.value)} type="number" value={leaseSeconds} /></label>
    <div className="flex justify-end gap-2"><Button onClick={onCancel} variant="secondary">Cancel Queue Configuration</Button><Button onClick={() => onSubmit({ default_lease_seconds: Number(leaseSeconds), global_concurrency_limit: globalLimit ? Number(globalLimit) : null, version: queue.version, workspace_concurrency_limit: workspaceLimit ? Number(workspaceLimit) : null })}>Save Queue Configuration</Button></div>
  </div>
}

function WorkersView({ metrics, state, workers }: { metrics: JobMetrics | null; state: LoadState; workers: JobWorker[] }) {
  return <Panel><PanelHeader><PanelTitle>Workers</PanelTitle><PanelDescription>{metrics ? `${metrics.workers.live} live · ${metrics.workers.draining} draining · ${metrics.workers.stale} stale` : 'Operational worker presence.'}</PanelDescription></PanelHeader><PanelBody>
    {workers.length === 0 ? <EmptyState>{state === 'loading' ? 'Loading workers…' : 'No workers have advertised presence.'}</EmptyState> : <TableScroll><Table><TableHeader><TableRow><TableHead>Worker</TableHead><TableHead>Status</TableHead><TableHead>Heartbeat</TableHead><TableHead>Version</TableHead><TableHead>Queues</TableHead><TableHead>Handlers</TableHead></TableRow></TableHeader><TableBody>
      {workers.map((worker) => <TableRow key={worker.id}><TableCell>{worker.process_identity}</TableCell><TableCell><StatusBadge tone={workerTone(worker)}>{workerStatus(worker)}</StatusBadge></TableCell><TableCell>{formatTimestamp(worker.heartbeat_at)}</TableCell><TableCell>{worker.application_version}</TableCell><TableCell>{worker.supported_queues.join(', ')}</TableCell><TableCell className="max-w-80 whitespace-normal">{worker.supported_handlers.join(', ')}</TableCell></TableRow>)}
    </TableBody></Table></TableScroll>}
  </PanelBody></Panel>
}

function ConfirmationDialog({ confirmation, disabled, onCancel, onConfirm }: { confirmation: Confirmation; disabled: boolean; onCancel(): void; onConfirm(): void }) {
  const label = confirmationLabel(confirmation)
  return <div className="fixed inset-0 z-[80] grid place-items-center bg-[var(--overlay-backdrop)] p-4"><div aria-label={label} aria-modal="true" className="w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-2xl" role="alertdialog"><h2 className="text-lg font-semibold">{label}</h2><p className="my-3 text-sm text-muted-foreground">This durable control operation is version-checked and will be recorded.</p><div className="flex justify-end gap-2"><Button disabled={disabled} onClick={onCancel} variant="secondary">Keep Current State</Button><Button disabled={disabled} onClick={onConfirm} variant="danger">{confirmationButtonLabel(confirmation)}</Button></div></div></div>
}

function replaceJobQuery(filters: JobFilters) {
  if (typeof window === 'undefined') return
  const query = encodeJobFilters(filters)
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
}

function submoduleTitle(value: JobsSubmodule): string { return value === 'jobs' ? 'Background Jobs' : value.charAt(0).toUpperCase() + value.slice(1) }
function actionLabel(action: JobAction): string { return action === 'cancel' ? 'Cancel' : action === 'retry' ? 'Retry' : 'Unblock' }
function confirmationLabel(value: Confirmation): string { if ('job' in value) return `${actionLabel(value.kind)} Job`; if ('schedule' in value) return value.kind === 'archive-schedule' ? 'Archive Schedule' : 'Pause Schedule'; return 'Pause Queue' }
function confirmationButtonLabel(value: Confirmation): string { if ('job' in value) return value.kind === 'cancel' ? 'Confirm Cancellation' : value.kind === 'retry' ? 'Confirm Retry' : 'Confirm Unblock'; if ('schedule' in value) return value.kind === 'archive-schedule' ? 'Confirm Archive' : 'Confirm Pause'; return 'Confirm Queue Pause' }
function formatTimestamp(value: string | null): string { if (value === null) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString() }
function formatAge(value: number | null): string { if (value === null) return '—'; return value < 60 ? `${Math.round(value)}s` : `${Math.round(value / 60)}m` }
function workerStatus(worker: JobWorker): string { if (worker.shutdown_at) return 'Shutdown'; if (worker.draining_at) return 'Draining'; return Date.now() - new Date(worker.heartbeat_at).getTime() > 30_000 ? 'Stale' : 'Live' }
function workerTone(worker: JobWorker): 'danger' | 'neutral' | 'success' | 'warning' { const status = workerStatus(worker); return status === 'Live' ? 'success' : status === 'Draining' ? 'warning' : status === 'Stale' ? 'danger' : 'neutral' }
function safeErrorMessage(reason: unknown): string { return operatorSafeMessage(reason instanceof Error ? reason.message : null) }

export const ConnectedJobPlatform = JobPlatformPanel
