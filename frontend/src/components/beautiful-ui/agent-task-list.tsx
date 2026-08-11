import { type ReactNode } from 'react'
import { Check, Circle, CircleAlert, LoaderCircle } from 'lucide-react'

import { StatusBadge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/feedback'
import { cn } from '@/lib/utils'

export type AgentTaskStatus =
  | 'blocked'
  | 'canceled'
  | 'completed'
  | 'dead_letter'
  | 'failed'
  | 'queued'
  | 'running'
  | 'succeeded'

export type AgentTaskItem = {
  detail?: ReactNode
  id: string
  label: string
  meta?: string
  status: AgentTaskStatus
  statusLabel?: string
}

export type AgentTaskListProps = {
  emptyLabel: string
  label: string
  tasks: readonly AgentTaskItem[]
}

const statusTone = {
  blocked: 'danger',
  canceled: 'neutral',
  completed: 'success',
  dead_letter: 'danger',
  failed: 'danger',
  queued: 'neutral',
  running: 'primary',
  succeeded: 'success',
} as const

function TaskStatusIcon({ status }: Pick<AgentTaskItem, 'status'>) {
  if (status === 'completed' || status === 'succeeded') {
    return (
      <Check
        aria-hidden="true"
        className="size-3.5 shrink-0"
        data-slot="agent-task-status-icon"
      />
    )
  }
  if (status === 'failed' || status === 'blocked' || status === 'dead_letter') {
    return (
      <CircleAlert
        aria-hidden="true"
        className="size-3.5 shrink-0"
        data-slot="agent-task-status-icon"
      />
    )
  }
  if (status === 'running') {
    return (
      <LoaderCircle
        aria-hidden="true"
        className={cn('size-3.5 shrink-0 motion-safe:animate-spin')}
        data-slot="agent-task-status-icon"
      />
    )
  }
  return (
    <Circle
      aria-hidden="true"
      className="size-3.5 shrink-0"
      data-slot="agent-task-status-icon"
    />
  )
}

export function AgentTaskList({ emptyLabel, label, tasks }: AgentTaskListProps) {
  return (
    <section aria-label={label} className="grid gap-2" data-slot="agent-task-list">
      <h2 className="text-sm font-medium">{label}</h2>
      {tasks.length === 0 ? (
        <EmptyState>{emptyLabel}</EmptyState>
      ) : (
        <ul className="overflow-hidden rounded-[2px] border border-border">
          {tasks.map((task) => (
            <li
              className="grid gap-1 border-b border-border p-3 last:border-b-0 max-[680px]:min-h-11"
              data-slot="agent-task-row"
              data-status={task.status}
              key={task.id}
            >
              <div className="flex min-w-0 items-center gap-2 text-sm">
                <TaskStatusIcon status={task.status} />
                <span className="min-w-0 flex-1 truncate">{task.label}</span>
                {task.meta ? <span className="text-xs tabular-nums text-muted-foreground">{task.meta}</span> : null}
                <StatusBadge tone={statusTone[task.status]}>
                  {task.statusLabel ?? task.status}
                </StatusBadge>
              </div>
              {task.detail ? <div className="pl-5 text-sm text-muted-foreground">{task.detail}</div> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
