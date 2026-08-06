import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useId,
  useState,
} from 'react'

import { StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldHelp, FieldLabel } from '@/components/ui/field'
import { Panel, PanelDescription } from '@/components/ui/panel'
import {
  ApiClientError,
  USER_MEMORY_MAX_CHARS,
  USER_MEMORY_SOFT_HINT_CHARS,
  type ApiClient,
  type UserMemory,
  type UserMemoryStatus,
} from '@/lib/apiClient'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import { cn } from '@/lib/utils'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed'

export type MemoryStatusFilter = 'all' | UserMemoryStatus

const STATUS_FILTERS: Array<{ id: MemoryStatusFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'proposed', label: 'Proposed' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
]

export type UserMemoryPanelProps = {
  apiClient: ApiClient
  projectId: string
}

export function UserMemoryPanel({ apiClient, projectId }: UserMemoryPanelProps) {
  const titleId = useId()
  const draftFieldId = useId()
  const [statusFilter, setStatusFilter] = useState<MemoryStatusFilter>('all')
  const [items, setItems] = useState<UserMemory[]>([])
  const [listState, setListState] = useState<RequestState>('idle')
  const [listError, setListError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [scopeToProject, setScopeToProject] = useState(false)
  const [proposeState, setProposeState] = useState<RequestState>('idle')
  const [proposeError, setProposeError] = useState<string | null>(null)
  const [proposeSuccess, setProposeSuccess] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [busyMemoryId, setBusyMemoryId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState('')
  const [injectableCount, setInjectableCount] = useState(0)
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({})
  const [statusCounts, setStatusCounts] = useState({
    all: 0,
    approved: 0,
    proposed: 0,
    rejected: 0,
  })
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null)
  const [undoRemoveId, setUndoRemoveId] = useState<string | null>(null)

  const trimmedProjectId = projectId.trim()
  const draftLength = draft.length
  const draftOverLimit = draftLength > USER_MEMORY_MAX_CHARS

  useEffect(() => {
    if (undoRemoveId === null) {
      return
    }
    const timer = window.setTimeout(() => {
      setUndoRemoveId(null)
    }, 10_000)
    return () => window.clearTimeout(timer)
  }, [undoRemoveId])

  useEffect(() => {
    if (confirmRemoveId === null) {
      return
    }
    const button = document.getElementById(`confirm-remove-${confirmRemoveId}`)
    if (button instanceof HTMLElement) {
      button.focus()
    }
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') {
        return
      }
      event.preventDefault()
      const memoryId = confirmRemoveId
      setConfirmRemoveId(null)
      requestAnimationFrame(() => {
        document.getElementById(`remove-injection-${memoryId}`)?.focus()
      })
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [confirmRemoveId])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setListState('loading')
      setListError(null)
      setConfirmRemoveId(null)
      try {
        const projectScope =
          trimmedProjectId.length > 0 ? trimmedProjectId : null
        const tallyResponse = await apiClient.listUserMemories({
          project_id: projectScope,
          status: null,
        })
        const listResponse =
          statusFilter === 'all'
            ? tallyResponse
            : await apiClient.listUserMemories({
                project_id: projectScope,
                status: statusFilter,
              })
        if (cancelled) {
          return
        }
        const tally = tallyResponse.items
        setItems(sortMemoriesForFilter(listResponse.items, statusFilter))
        setInjectableCount(
          tally.filter((item) => item.status === 'approved').length,
        )
        setStatusCounts({
          all: tally.length,
          approved: tally.filter((item) => item.status === 'approved').length,
          proposed: tally.filter((item) => item.status === 'proposed').length,
          rejected: tally.filter((item) => item.status === 'rejected').length,
        })
        setListState('succeeded')
      } catch (error) {
        if (cancelled) {
          return
        }
        setItems([])
        setListError(getErrorMessage(error, 'Could not load memories.'))
        setListState('failed')
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [apiClient, statusFilter, trimmedProjectId])


  async function refreshList() {
    setListState('loading')
    setListError(null)
    try {
      const projectScope =
        trimmedProjectId.length > 0 ? trimmedProjectId : null
      const tallyResponse = await apiClient.listUserMemories({
        project_id: projectScope,
        status: null,
      })
      const response =
        statusFilter === 'all'
          ? tallyResponse
          : await apiClient.listUserMemories({
              project_id: projectScope,
              status: statusFilter,
            })
      const tally = tallyResponse.items
      setItems(sortMemoriesForFilter(response.items, statusFilter))
      setInjectableCount(
        tally.filter((item) => item.status === 'approved').length,
      )
      setStatusCounts({
        all: tally.length,
        approved: tally.filter((item) => item.status === 'approved').length,
        proposed: tally.filter((item) => item.status === 'proposed').length,
        rejected: tally.filter((item) => item.status === 'rejected').length,
      })
      setListState('succeeded')
    } catch (error) {
      setItems([])
      setListError(getErrorMessage(error, 'Could not load memories.'))
      setListState('failed')
    }
  }

  async function handlePropose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const content = draft.trim()
    if (content.length === 0 || draftOverLimit || proposeState === 'loading') {
      return
    }

    setProposeState('loading')
    setProposeError(null)
    setProposeSuccess(null)
    setActionError(null)
    try {
      await apiClient.proposeUserMemory({
        content,
        project_id:
          scopeToProject && trimmedProjectId.length > 0 ? trimmedProjectId : null,
      })
      setDraft('')
      setProposeState('succeeded')
      setProposeSuccess('Proposed. Approve it below before chat can use it.')
      if (statusFilter !== 'proposed') {
        setStatusFilter('proposed')
      } else {
        await refreshList()
      }
    } catch (error) {
      setProposeState('failed')
      setProposeError(getErrorMessage(error, 'Could not propose memory.'))
    }
  }

  async function handleApprove(memory: UserMemory) {
    setBusyMemoryId(memory.id)
    setActionError(null)
    const rowIndex = items.findIndex((item) => item.id === memory.id)
    try {
      await apiClient.approveUserMemory(memory.id)
      await refreshList()
      requestAnimationFrame(() => {
        focusAfterReview(memory.id, rowIndex)
      })
    } catch (error) {
      setActionError(getErrorMessage(error, 'Could not approve memory.'))
    } finally {
      setBusyMemoryId(null)
    }
  }

  async function handleReject(memory: UserMemory) {
    setBusyMemoryId(memory.id)
    setActionError(null)
    const wasApproved = memory.status === 'approved'
    const rowIndex = items.findIndex((item) => item.id === memory.id)
    const remainingApproved = wasApproved
      ? items.filter(
          (item) => item.id !== memory.id && item.status === 'approved',
        ).length
      : 0
    const switchApprovedToRejected =
      wasApproved && statusFilter === 'approved' && remainingApproved === 0
    try {
      await apiClient.rejectUserMemory(memory.id)
      if (editingId === memory.id) {
        setEditingId(null)
        setEditDraft('')
      }
      setConfirmRemoveId(null)
      if (wasApproved) {
        setUndoRemoveId(memory.id)
      } else {
        setUndoRemoveId(null)
      }
      if (switchApprovedToRejected) {
        setStatusFilter('rejected')
      } else {
        await refreshList()
      }
      requestAnimationFrame(() => {
        if (wasApproved) {
          document.getElementById('memory-undo-remove')?.focus()
          return
        }
        focusAfterReview(memory.id, rowIndex)
      })
    } catch (error) {
      setActionError(getErrorMessage(error, 'Could not reject memory.'))
    } finally {
      setBusyMemoryId(null)
    }
  }

  async function handleUndoRemove(memoryId: string) {
    setBusyMemoryId(memoryId)
    setActionError(null)
    try {
      await apiClient.approveUserMemory(memoryId)
      setUndoRemoveId(null)
      await refreshList()
      requestAnimationFrame(() => {
        document.getElementById(`remove-injection-${memoryId}`)?.focus()
      })
    } catch (error) {
      setActionError(getErrorMessage(error, 'Could not restore memory.'))
    } finally {
      setBusyMemoryId(null)
    }
  }

  async function handleSaveEdit(memory: UserMemory) {
    const content = editDraft.trim()
    if (content.length === 0 || content.length > USER_MEMORY_MAX_CHARS) {
      return
    }
    setBusyMemoryId(memory.id)
    setActionError(null)
    try {
      await apiClient.updateUserMemory(memory.id, { content })
      setEditingId(null)
      setEditDraft('')
      await refreshList()
    } catch (error) {
      setActionError(getErrorMessage(error, 'Could not update memory.'))
    } finally {
      setBusyMemoryId(null)
    }
  }

  function handleRowKeyDown(
    event: KeyboardEvent<HTMLLIElement>,
    memory: UserMemory,
  ) {
    if (busyMemoryId === memory.id) {
      return
    }
    if (event.key === 'Escape' && confirmRemoveId === memory.id) {
      event.preventDefault()
      setConfirmRemoveId(null)
      requestAnimationFrame(() => {
        document.getElementById(`remove-injection-${memory.id}`)?.focus()
      })
      return
    }
    const target = event.target as HTMLElement
    if (target.closest('button, textarea, input, a')) {
      return
    }
    if (editingId === memory.id) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setEditingId(null)
        setEditDraft('')
      }
      return
    }
    if (memory.status !== 'proposed') {
      return
    }
    if (event.key === 'Enter' || event.key === 'a' || event.key === 'A') {
      event.preventDefault()
      void handleApprove(memory)
      return
    }
    if (event.key === 'r' || event.key === 'R') {
      event.preventDefault()
      void handleReject(memory)
      return
    }
    if (event.key === 'e' || event.key === 'E') {
      event.preventDefault()
      setEditingId(memory.id)
      setEditDraft(memory.content)
    }
  }

  return (
    <Panel
      aria-labelledby={titleId}
      className="grid gap-4 p-4 max-[680px]:gap-0.5 max-[680px]:p-0.5"
      role="region"
    >
      <header className="flex flex-col gap-2 max-[680px]:gap-0.5 sm:flex-row sm:items-start sm:justify-between">
        <div className="grid gap-1 max-[680px]:gap-0.5">
          <p className="text-xs font-bold uppercase leading-none text-muted-foreground max-[680px]:text-[0.5625rem]">
            My account
          </p>
          <h2
            className="text-lg font-semibold leading-tight text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug"
            id={titleId}
          >
            Memory
          </h2>
        </div>
        <div className="grid justify-items-end gap-1 max-[680px]:gap-0.5">
          <div className="flex flex-wrap justify-end gap-1 max-[680px]:gap-0.5">
            {listState !== 'loading' && statusCounts.proposed > 0 ? (
              <StatusBadge
                aria-label={`${statusCounts.proposed} proposed`}
                className="w-fit"
                tone="warning"
              >
                {statusCounts.proposed} Proposed
              </StatusBadge>
            ) : null}
            <StatusBadge
              aria-label={
                listState === 'loading'
                  ? 'Loading injectable count'
                  : `${injectableCount} injectable`
              }
              className="w-fit"
              tone="primary"
            >
              {listState === 'loading'
                ? 'Loading'
                : `${injectableCount} Injectable`}
            </StatusBadge>
          </div>
          <p aria-live="polite" className="sr-only">
            {listState === 'loading'
              ? 'Loading memories'
              : `${injectableCount} injectable ${injectableCount === 1 ? 'memory' : 'memories'}${
                  statusCounts.proposed > 0
                    ? `, ${statusCounts.proposed} proposed awaiting review`
                    : ''
                }`}
          </p>
        </div>
      </header>

      <PanelDescription>
        Only approved items inject as system context (never as a user turn).
        Propose → approve required. No automatic capture in this build.
      </PanelDescription>

      <form className="grid gap-2" onSubmit={(event) => void handlePropose(event)}>
        <Field>
          <FieldLabel htmlFor={draftFieldId}>Propose Memory</FieldLabel>
          <FieldControl>
            <Textarea
              aria-describedby={`${draftFieldId}-help`}
              aria-invalid={draftOverLimit || undefined}
              aria-label="Propose Memory"
              className="min-h-20"
              id={draftFieldId}
              maxLength={USER_MEMORY_MAX_CHARS}
              onChange={(event) => {
                setDraft(event.target.value)
                setProposeSuccess(null)
              }}
              placeholder="e.g. Prefer concise answers in Spanish"
              value={draft}
            />
          </FieldControl>
          <FieldHelp id={`${draftFieldId}-help`}>
            <span
              className={cn(
                draftOverLimit && 'text-destructive',
                draftLength >= USER_MEMORY_SOFT_HINT_CHARS &&
                  !draftOverLimit &&
                  'text-amber-900 dark:text-amber-100',
              )}
            >
              {draftLength}/{USER_MEMORY_MAX_CHARS}
            </span>
            {draftLength >= USER_MEMORY_SOFT_HINT_CHARS
              ? ' — keep preferences short when possible.'
              : null}
          </FieldHelp>
        </Field>

        {trimmedProjectId.length > 0 ? (
          <label className="flex items-start gap-2 text-xs text-foreground">
            <input
              checked={scopeToProject}
              className="mt-0.5"
              onChange={(event) => setScopeToProject(event.target.checked)}
              type="checkbox"
            />
            <span>
              Scope to current project
              <span className="block text-muted-foreground">
                Unchecked = global (all projects for this user).
              </span>
            </span>
          </label>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <Button
            disabled={
              draft.trim().length === 0 ||
              draftOverLimit ||
              proposeState === 'loading'
            }
            size="sm"
            type="submit"
          >
            {proposeState === 'loading' ? 'Proposing…' : 'Propose'}
          </Button>
          {proposeSuccess ? (
            <InlineFeedback role="status" tone="success">
              {proposeSuccess}
            </InlineFeedback>
          ) : null}
          {proposeError ? (
            <InlineFeedback role="alert" tone="danger">
              {proposeError}
            </InlineFeedback>
          ) : null}
        </div>
      </form>

      <div
        aria-label="Memory Status Filters"
        className="flex flex-wrap gap-1.5 max-[680px]:gap-0.5"
        role="group"
      >
        {STATUS_FILTERS.map((filter) => {
          const active = statusFilter === filter.id
          return (
            <Button
              aria-label={`${filter.label}, ${statusCounts[filter.id]} items`}
              aria-pressed={active}
              disabled={listState === 'loading'}
              key={filter.id}
              onClick={() => {
                setConfirmRemoveId(null)
                setStatusFilter(filter.id)
              }}
              size="sm"
              type="button"
              variant={active ? 'primary' : 'secondary'}
            >
              {filter.label}
              <span aria-hidden className="tabular-nums text-[10px] opacity-80">
                {statusCounts[filter.id]}
              </span>
            </Button>
          )
        })}
      </div>
      {items.some((item) => item.status === 'proposed') ? (
        <p className="text-[11px] leading-snug text-muted-foreground">
          Focus a proposed row: Enter/A approve · R reject · E edit.
        </p>
      ) : null}
      {confirmRemoveId !== null ? (
        <p
          aria-live="assertive"
          className="text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]"
          id="memory-confirm-remove-hint"
          role="status"
        >
          Confirm remove drops injection. Esc or Keep In Injection leaves it
          approved.
        </p>
      ) : null}

      <div aria-live="polite" className="grid gap-1.5 max-[680px]:gap-0.5">
        {listError ? (
          <div className="flex flex-wrap items-center gap-2">
            <InlineFeedback role="alert" tone="danger">
              {listError}
            </InlineFeedback>
            <Button
              onClick={() => void refreshList()}
              size="sm"
              type="button"
              variant="secondary"
            >
              Retry
            </Button>
          </div>
        ) : null}
        {actionError ? (
          <InlineFeedback role="alert" tone="danger">
            {actionError}
          </InlineFeedback>
        ) : null}
        {undoRemoveId !== null ? (
          <div className="flex flex-wrap items-center gap-2">
            <InlineFeedback role="status" tone="neutral">
              Removed from injection.
            </InlineFeedback>
            <Button
              aria-label="Undo remove from injection"
              disabled={busyMemoryId === undoRemoveId}
              id="memory-undo-remove"
              onClick={() => void handleUndoRemove(undoRemoveId)}
              size="sm"
              type="button"
              variant="secondary"
            >
              Undo
            </Button>
          </div>
        ) : null}
      </div>

      {listState === 'loading' && items.length === 0 ? (
        <MemoryListLoadingSkeleton />
      ) : null}

      {listState !== 'loading' && items.length === 0 ? (
        <FilterEmptyState
          filter={statusFilter}
          onPropose={() => {
            setConfirmRemoveId(null)
            document.getElementById(draftFieldId)?.focus()
          }}
          onViewProposed={() => {
            setConfirmRemoveId(null)
            setStatusFilter('proposed')
          }}
        />
      ) : null}

      {items.length > 0 ? (
        <DataList
          aria-busy={listState === 'loading' || undefined}
          aria-label="User Memories"
          className="gap-1.5"
        >
          {listState === 'loading' ? (
            <li className="list-none">
              <p
                className="text-[11px] leading-snug text-muted-foreground"
                role="status"
              >
                Refreshing memories…
              </p>
            </li>
          ) : null}
          {items.map((memory) => {
            const busy = busyMemoryId === memory.id
            const isEditing = editingId === memory.id
            const keyboardReviewable =
              memory.status === 'proposed' && !isEditing
            return (
              <DataListItem
                aria-busy={busy || undefined}
                aria-keyshortcuts={
                  keyboardReviewable ? 'Enter a r e' : undefined
                }
                aria-label={
                  keyboardReviewable
                    ? `${statusLabel(memory.status)} memory. Press Enter or A to approve, R to reject, E to edit.`
                    : undefined
                }
                className={cn(
                  'p-2.5 outline-none',
                  busy && 'opacity-70',
                  keyboardReviewable &&
                    'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                )}
                id={`user-memory-${memory.id}`}
                key={memory.id}
                onKeyDown={(event) => handleRowKeyDown(event, memory)}
                tabIndex={keyboardReviewable ? 0 : -1}
              >
                <div className="grid gap-1.5 max-[680px]:gap-0.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <StatusBadge
                      className="w-fit"
                      tone={statusTone(memory.status)}
                    >
                      {statusLabel(memory.status)}
                    </StatusBadge>
                    <span className="text-xs text-muted-foreground">
                      {memory.project_id ? 'Project-scoped' : 'Global'}
                    </span>
                    {formatRelativeTime(memory.created_at) ? (
                      <>
                        <span aria-hidden className="text-xs text-muted-foreground">
                          ·
                        </span>
                        <time
                          className="text-xs text-muted-foreground"
                          dateTime={memory.created_at ?? undefined}
                          title={formatAbsoluteTime(memory.created_at) ?? undefined}
                        >
                          {formatRelativeTime(memory.created_at)}
                        </time>
                      </>
                    ) : null}
                  </div>

                  {isEditing ? (
                    <div className="grid gap-1">
                      <Textarea
                        aria-describedby={`edit-memory-help-${memory.id}`}
                        aria-label="Edit Memory Content"
                        autoFocus
                        className="min-h-16"
                        maxLength={USER_MEMORY_MAX_CHARS}
                        onChange={(event) => setEditDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Escape') {
                            event.preventDefault()
                            setEditingId(null)
                            setEditDraft('')
                            return
                          }
                          if (
                            (event.metaKey || event.ctrlKey) &&
                            event.key === 'Enter'
                          ) {
                            event.preventDefault()
                            void handleSaveEdit(memory)
                          }
                        }}
                        value={editDraft}
                      />
                      <p
                        className="text-xs text-muted-foreground"
                        id={`edit-memory-help-${memory.id}`}
                      >
                        <span
                          className={cn(
                            editDraft.length > USER_MEMORY_MAX_CHARS &&
                              'text-destructive',
                            editDraft.length >= USER_MEMORY_SOFT_HINT_CHARS &&
                              editDraft.length <= USER_MEMORY_MAX_CHARS &&
                              'text-amber-900 dark:text-amber-100',
                          )}
                        >
                          {editDraft.length}/{USER_MEMORY_MAX_CHARS}
                        </span>
                        {' · ⌘/Ctrl+Enter save · Esc cancel'}
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-1">
                      <p
                        className={cn(
                          'whitespace-pre-wrap text-sm leading-snug text-foreground',
                          !expandedIds[memory.id] &&
                            memory.content.length > 220 &&
                            'line-clamp-3',
                        )}
                      >
                        {memory.content}
                      </p>
                      {memory.content.length > 220 ? (
                        <Button
                          className="h-auto w-fit px-0 py-0 text-xs"
                          onClick={() =>
                            setExpandedIds((current) => ({
                              ...current,
                              [memory.id]: !current[memory.id],
                            }))
                          }
                          size="sm"
                          type="button"
                          variant="ghost"
                        >
                          {expandedIds[memory.id] ? 'Show less' : 'Show more'}
                        </Button>
                      ) : null}
                    </div>
                  )}

                  <DataListItemActions className="gap-1.5 max-[680px]:gap-0.5">
                    {memory.status === 'proposed' && !isEditing ? (
                      <>
                        <Button
                          disabled={busy}
                          onClick={() => void handleApprove(memory)}
                          size="sm"
                          type="button"
                        >
                          Approve
                        </Button>
                        <Button
                          disabled={busy}
                          onClick={() => {
                            setEditingId(memory.id)
                            setEditDraft(memory.content)
                          }}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          Edit
                        </Button>
                        <Button
                          disabled={busy}
                          onClick={() => void handleReject(memory)}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          Reject
                        </Button>
                      </>
                    ) : null}

                    {memory.status === 'proposed' && isEditing ? (
                      <>
                        <Button
                          disabled={
                            busy ||
                            editDraft.trim().length === 0 ||
                            editDraft.length > USER_MEMORY_MAX_CHARS
                          }
                          onClick={() => void handleSaveEdit(memory)}
                          size="sm"
                          type="button"
                        >
                          Save
                        </Button>
                        <Button
                          disabled={busy}
                          onClick={() => {
                            setEditingId(null)
                            setEditDraft('')
                          }}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          Cancel
                        </Button>
                      </>
                    ) : null}

                    {memory.status === 'approved' ? (
                      confirmRemoveId === memory.id ? (
                        <DataListItemActions
                          className="gap-1.5 max-[680px]:gap-0.5"
                          onKeyDown={(event) => {
                            if (event.key !== 'Tab') {
                              return
                            }
                            const confirm = document.getElementById(
                              `confirm-remove-${memory.id}`,
                            )
                            const keep = document.getElementById(
                              `keep-injection-${memory.id}`,
                            )
                            if (
                              !(confirm instanceof HTMLElement) ||
                              !(keep instanceof HTMLElement)
                            ) {
                              return
                            }
                            const ordered = [confirm, keep]
                            const active = document.activeElement
                            const index = ordered.findIndex(
                              (node) => node === active,
                            )
                            if (index < 0) {
                              return
                            }
                            event.preventDefault()
                            const nextIndex = event.shiftKey
                              ? (index - 1 + ordered.length) % ordered.length
                              : (index + 1) % ordered.length
                            ordered[nextIndex]?.focus()
                          }}
                        >
                          <Button
                            aria-describedby="memory-confirm-remove-hint"
                            aria-label="Confirm remove from injection"
                            disabled={busy}
                            id={`confirm-remove-${memory.id}`}
                            onClick={() => void handleReject(memory)}
                            size="sm"
                            type="button"
                            variant="danger"
                          >
                            Confirm remove
                          </Button>
                          <Button
                            aria-label="Keep In Injection"
                            disabled={busy}
                            id={`keep-injection-${memory.id}`}
                            onClick={() => {
                              const memoryId = memory.id
                              setConfirmRemoveId(null)
                              requestAnimationFrame(() => {
                                document
                                  .getElementById(`remove-injection-${memoryId}`)
                                  ?.focus()
                              })
                            }}
                            size="sm"
                            type="button"
                            variant="secondary"
                          >
                            Keep In Injection
                          </Button>
                        </DataListItemActions>
                      ) : (
                        <Button
                          disabled={busy}
                          id={`remove-injection-${memory.id}`}
                          onClick={() => setConfirmRemoveId(memory.id)}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          Remove from injection
                        </Button>
                      )
                    ) : null}

                    {memory.status === 'rejected' ? (
                      <DataListItemActions className="gap-1.5 max-[680px]:gap-0.5">
                        <Button
                          aria-label="Propose again from rejected memory"
                          onClick={() => {
                            setDraft(
                              memory.content.slice(0, USER_MEMORY_MAX_CHARS),
                            )
                            setProposeSuccess(null)
                            setProposeError(null)
                            setConfirmRemoveId(null)
                            requestAnimationFrame(() => {
                              document.getElementById(draftFieldId)?.focus()
                            })
                          }}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          Propose Again
                        </Button>
                        <span className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                          Not injectable until re-proposed and approved.
                        </span>
                      </DataListItemActions>
                    ) : null}
                  </DataListItemActions>
                </div>
              </DataListItem>
            )
          })}
        </DataList>
      ) : null}
    </Panel>
  )
}

function FilterEmptyState({
  filter,
  onPropose,
  onViewProposed,
}: {
  filter: MemoryStatusFilter
  onPropose(): void
  onViewProposed(): void
}) {
  const copy = emptyCopyForFilter(filter)
  return (
    <EmptyState
      className="gap-2 p-3 text-left"
      data-slot-state={`empty-${filter}`}
    >
      <p className="font-medium text-foreground/80">{copy.title}</p>
      <p className="text-xs leading-relaxed">{copy.body}</p>
      {filter === 'rejected' || filter === 'approved' ? (
        <div className="flex flex-wrap gap-2">
          <Button
            className="w-fit"
            onClick={onViewProposed}
            size="sm"
            type="button"
            variant="secondary"
          >
            View Proposed
          </Button>
          <Button
            className="w-fit"
            onClick={onPropose}
            size="sm"
            type="button"
            variant="secondary"
          >
            Focus Propose
          </Button>
        </div>
      ) : null}
      {filter === 'all' || filter === 'proposed' ? (
        <Button
          className="w-fit"
          onClick={onPropose}
          size="sm"
          type="button"
          variant="secondary"
        >
          Focus Propose
        </Button>
      ) : null}
    </EmptyState>
  )
}

function emptyCopyForFilter(filter: MemoryStatusFilter): {
  body: string
  title: string
} {
  if (filter === 'proposed') {
    return {
      body: 'Propose one above to start review. Only approved items inject.',
      title: 'No Proposed Memories',
    }
  }
  if (filter === 'approved') {
    return {
      body: 'Approve a proposal to enable chat injection as system context.',
      title: 'No Approved Memories',
    }
  }
  if (filter === 'rejected') {
    return {
      body: 'Rejected proposals and items removed from injection appear here. They never inject into chat.',
      title: 'No Rejected Memories',
    }
  }
  return {
    body: 'Propose one above, then approve it to enable chat injection.',
    title: 'No Memories Yet',
  }
}

function statusLabel(status: UserMemoryStatus): string {
  if (status === 'proposed') {
    return 'Proposed'
  }
  if (status === 'approved') {
    return 'Approved'
  }
  return 'Rejected'
}

function statusTone(
  status: UserMemoryStatus,
): 'neutral' | 'primary' | 'success' | 'warning' | 'danger' {
  if (status === 'approved') {
    return 'success'
  }
  if (status === 'proposed') {
    return 'warning'
  }
  if (status === 'rejected') {
    return 'danger'
  }
  return 'neutral'
}


function sortMemoriesForFilter(
  items: UserMemory[],
  filter: MemoryStatusFilter,
): UserMemory[] {
  const byNewest = (left: UserMemory, right: UserMemory) => {
    const leftTime = Date.parse(left.created_at ?? '') || 0
    const rightTime = Date.parse(right.created_at ?? '') || 0
    return rightTime - leftTime
  }
  if (filter !== 'all') {
    return [...items].sort(byNewest)
  }
  const rank: Record<UserMemoryStatus, number> = {
    proposed: 0,
    approved: 1,
    rejected: 2,
  }
  return [...items].sort((left, right) => {
    const statusDelta = rank[left.status] - rank[right.status]
    return statusDelta !== 0 ? statusDelta : byNewest(left, right)
  })
}

function MemoryListLoadingSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading Memories"
      className="grid w-full gap-2 p-1 max-[680px]:gap-0.5 max-[680px]:p-0.5"
      data-slot="memory-list-loading"
      role="status"
    >
      <span className="sr-only">Loading Memories…</span>
      <div aria-hidden="true" className="h-3 w-1/3 motion-safe:animate-pulse rounded bg-muted/25" />
      <div aria-hidden="true" className="h-3 w-full motion-safe:animate-pulse rounded bg-muted/35" />
      <div aria-hidden="true" className="h-3 w-11/12 motion-safe:animate-pulse rounded bg-muted/30" />
      <div aria-hidden="true" className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted/25" />
    </div>
  )
}

function focusAfterReview(memoryId: string, rowIndex: number): void {
  const current = document.getElementById(`user-memory-${memoryId}`)
  if (current instanceof HTMLElement) {
    current.focus()
    return
  }
  const reviewable = Array.from(
    document.querySelectorAll<HTMLElement>('[id^="user-memory-"][tabindex="0"]'),
  )
  if (reviewable.length > 0) {
    const index = Math.min(Math.max(rowIndex, 0), reviewable.length - 1)
    reviewable[index]?.focus()
    return
  }
  const empty = document.querySelector<HTMLElement>('[data-slot="empty-state"]')
  if (empty) {
    empty.setAttribute('tabindex', '-1')
    empty.focus()
    return
  }
  document.querySelector<HTMLElement>('[aria-label="Propose Memory"]')?.focus()
}

function formatRelativeTime(iso: string | null): string | null {
  if (iso === null || iso.trim().length === 0) {
    return null
  }
  const then = Date.parse(iso)
  if (Number.isNaN(then)) {
    return null
  }
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000))
  if (seconds < 60) {
    return 'Just now'
  }
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) {
    return `${minutes}m ago`
  }
  const hours = Math.round(minutes / 60)
  if (hours < 48) {
    return `${hours}h ago`
  }
  const days = Math.round(hours / 24)
  return `${days}d ago`
}

function formatAbsoluteTime(iso: string | null): string | null {
  if (iso === null || iso.trim().length === 0) {
    return null
  }
  const then = Date.parse(iso)
  if (Number.isNaN(then)) {
    return null
  }
  try {
    return new Date(then).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError || error instanceof Error) {
    return operatorSafeMessage(error.message, fallback)
  }
  return fallback
}
