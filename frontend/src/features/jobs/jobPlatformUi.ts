export type JobsSubmodule = 'jobs' | 'schedules' | 'queues' | 'workers'
export type JobAction = 'cancel' | 'retry' | 'unblock'
export type JobStatusTone =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'

export type JobFilters = {
  status: string | null
  queue: string | null
  job_type: string | null
  limit: number | null
  cursor: string | null
}

const STATUS_LABELS: Record<string, string> = {
  blocked: 'Blocked',
  cancelled: 'Cancelled',
  dead_letter: 'Dead letter',
  queued: 'Queued',
  running: 'Running',
  succeeded: 'Succeeded',
}

const STATUS_TONES: Record<string, JobStatusTone> = {
  blocked: 'warning',
  cancelled: 'neutral',
  dead_letter: 'danger',
  queued: 'neutral',
  running: 'primary',
  succeeded: 'success',
}

export function encodeJobFilters(filters: Partial<JobFilters>): string {
  const query = new URLSearchParams()
  appendFilter(query, 'status', filters.status)
  appendFilter(query, 'queue', filters.queue)
  appendFilter(query, 'job_type', filters.job_type)
  appendFilter(query, 'limit', filters.limit)
  appendFilter(query, 'cursor', filters.cursor)
  return query.toString()
}

export function decodeJobFilters(query: string): JobFilters {
  const params = new URLSearchParams(query.replace(/^\?/, ''))
  const rawLimit = params.get('limit')
  const parsedLimit = rawLimit === null ? Number.NaN : Number(rawLimit)
  return {
    cursor: cleanFilter(params.get('cursor')),
    job_type: cleanFilter(params.get('job_type')),
    limit:
      Number.isInteger(parsedLimit) && parsedLimit > 0 ? parsedLimit : null,
    queue: cleanFilter(params.get('queue')),
    status: cleanFilter(params.get('status')),
  }
}

export function jobActions(status: string, canAdmin: boolean): JobAction[] {
  if (!canAdmin) {
    return []
  }
  if (status === 'blocked') {
    return ['unblock', 'cancel']
  }
  if (status === 'dead_letter') {
    return ['retry']
  }
  if (status === 'queued' || status === 'running') {
    return ['cancel']
  }
  return []
}

export function jobStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? titleCaseToken(status)
}

export function jobStatusTone(status: string): JobStatusTone {
  return STATUS_TONES[status] ?? 'neutral'
}

function appendFilter(
  query: URLSearchParams,
  key: keyof JobFilters,
  value: number | string | null | undefined,
): void {
  if (value === null || value === undefined || String(value).trim().length === 0) {
    return
  }
  query.append(key, String(value))
}

function cleanFilter(value: string | null): string | null {
  const cleaned = value?.trim() ?? ''
  return cleaned.length > 0 ? cleaned : null
}

function titleCaseToken(value: string): string {
  const normalized = value.trim().replaceAll(/[_-]+/g, ' ')
  if (normalized.length === 0) {
    return 'Unknown'
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}
