import { type ReactNode } from 'react'
import { Check, CircleAlert, LoaderCircle } from 'lucide-react'

import { StatusBadge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/feedback'
import { cn } from '@/lib/utils'

export type AgentTaskItem = {
  detail?: ReactNode
  id: string
  label: string
  meta?: string
  status: 'running' | 'completed' | 'failed'
}

export type AgentTaskListProps = {
  emptyLabel: string
  label: string
  tasks: readonly AgentTaskItem[]
}

const statusTone = {
  completed: 'success',
  failed: 'danger',
  running: 'primary',
} as const

function TaskStatusIcon({ status }: Pick<AgentTaskItem, 'status'>) {
  if (status === 'completed') {
    return <Check aria-hidden="true" className="size-3.5 shrink-0" />
  }
  if (status === 'failed') {
    return <CircleAlert aria-hidden="true" className="size-3.5 shrink-0" />
  }
  return <LoaderCircle aria-hidden="true" className={cn('size-3.5 shrink-0 motion-safe:animate-spin')} />
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
                <StatusBadge tone={statusTone[task.status]}>{task.status}</StatusBadge>
              </div>
              {task.detail ? <div className="pl-5 text-sm text-muted-foreground">{task.detail}</div> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
