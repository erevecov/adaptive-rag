import {
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Brain, ChevronDown, ChevronUp, MoreVertical, Plus, X } from 'lucide-react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button, IconButton } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { DataList, DataListItem } from '@/components/ui/data-list'
import * as DropdownMenu from '@/components/ui/dropdown-menu'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import {
  Panel,
  PanelBody,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@/components/ui/tabs'
import { useFocusTrap } from '@/lib/focusTrap'
import type {
  ChatHistoryProviderUsage,
  ChatHistoryRetrievedChunk,
  ChatHistoryRetrievalRun,
  ChatHistoryToolCall,
  ChatSessionDetailResponse,
  ChatSessionSummary,
  Source,
} from '@/lib/apiClient'
import {
  parseChatStepsFromMetadata,
  summarizeContextWindow,
  type ChatStep,
} from '@/lib/chatSteps'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import { cn } from '@/lib/utils'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type InspectorTab = 'context' | 'minimap'
export type SessionNavigationFilter = 'active' | 'training' | 'archived'
export type SourceViewerState = {
  citationSnippet: string | null
  error: string | null
  source: Source | null
  sourceId: string | null
  state: RequestState
}

/** Turn selected via answer ⋯ → Ver detalles (scoped Context mode). */
export type FocusedTurn = {
  question: string
  turnId: string
}

/**
 * Slice session detail to a single Q/A turn window.
 * Turn id matches transcript builders: assistant message_id, else user message_id.
 */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper for turn focus
export function filterSessionDetailToTurn(
  detail: ChatSessionDetailResponse,
  turnId: string,
): ChatSessionDetailResponse | null {
  const bounds = resolveTurnBounds(detail.messages, turnId)
  if (bounds === null) {
    return null
  }

  const { assistantIndex, turnEndMs, turnStartMs, userIndex } = bounds
  const turnMessages = detail.messages.filter((_, index) => {
    if (index === userIndex) {
      return true
    }
    return assistantIndex >= 0 && index === assistantIndex
  })

  const turnToolCalls = detail.tool_calls.filter((call) => {
    const createdAtMs = Date.parse(call.created_at)
    return createdAtMs >= turnStartMs && createdAtMs < turnEndMs
  })
  const turnToolCallIds = new Set(
    turnToolCalls.map((call) => call.tool_call_id),
  )
  const turnRetrievalRuns = detail.retrieval_runs.filter((run) => {
    if (run.tool_call_id !== null) {
      return turnToolCallIds.has(run.tool_call_id)
    }
    const createdAtMs = Date.parse(run.created_at)
    return createdAtMs >= turnStartMs && createdAtMs < turnEndMs
  })
  const turnProviderUsage = detail.provider_usage.filter((usage) => {
    const createdAtMs = Date.parse(usage.created_at)
    return createdAtMs >= turnStartMs && createdAtMs < turnEndMs
  })

  return {
    session: detail.session,
    messages: turnMessages,
    tool_calls: turnToolCalls,
    retrieval_runs: turnRetrievalRuns,
    provider_usage: turnProviderUsage,
  }
}

function resolveTurnBounds(
  messages: ChatSessionDetailResponse['messages'],
  turnId: string,
): {
  assistantIndex: number
  turnEndMs: number
  turnStartMs: number
  userIndex: number
} | null {
  let userIndex = -1
  let assistantIndex = -1

  const directIndex = messages.findIndex(
    (message) => message.message_id === turnId,
  )
  if (directIndex >= 0) {
    const matched = messages[directIndex]
    if (matched.role === 'assistant') {
      assistantIndex = directIndex
      for (let index = directIndex - 1; index >= 0; index -= 1) {
        if (messages[index]?.role === 'user') {
          userIndex = index
          break
        }
      }
    } else if (matched.role === 'user') {
      userIndex = directIndex
      for (let index = directIndex + 1; index < messages.length; index += 1) {
        if (messages[index]?.role === 'user') {
          break
        }
        if (messages[index]?.role === 'assistant') {
          assistantIndex = index
          break
        }
      }
    }
  }

  if (userIndex < 0) {
    for (let index = 0; index < messages.length; index += 1) {
      const message = messages[index]
      if (message?.role !== 'user') {
        continue
      }
      let foundAssistant = -1
      for (let next = index + 1; next < messages.length; next += 1) {
        if (messages[next]?.role === 'user') {
          break
        }
        if (messages[next]?.role === 'assistant') {
          foundAssistant = next
          break
        }
      }
      const resolvedId =
        (foundAssistant >= 0
          ? messages[foundAssistant]?.message_id
          : undefined) ??
        message.message_id ??
        `turn-${index}`
      if (resolvedId === turnId) {
        userIndex = index
        assistantIndex = foundAssistant
        break
      }
    }
  }

  if (userIndex < 0) {
    return null
  }

  const userMessage = messages[userIndex]
  if (userMessage === undefined) {
    return null
  }

  const turnStartMs = Date.parse(userMessage.created_at)
  let turnEndMs = Number.POSITIVE_INFINITY
  const scanFrom = assistantIndex >= 0 ? assistantIndex + 1 : userIndex + 1
  for (let index = scanFrom; index < messages.length; index += 1) {
    if (messages[index]?.role === 'user') {
      turnEndMs = Date.parse(messages[index].created_at)
      break
    }
  }

  return {
    assistantIndex,
    turnEndMs,
    turnStartMs,
    userIndex,
  }
}

const SESSION_FILTERS: {
  label: string
  name: string
  title: string
  value: SessionNavigationFilter
}[] = [
  {
    label: 'Activos',
    name: 'ACTIVOS',
    title: 'Sesiones activas',
    value: 'active',
  },
  {
    label: 'Train',
    name: 'TRAIN',
    title: 'Sesiones con entrenamiento',
    value: 'training',
  },
  {
    label: 'Archivados',
    name: 'ARCHIVADOS',
    title: 'Sesiones archivadas',
    value: 'archived',
  },
]
const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')

/** Fades the title into the age/⋮ column on row hover (beflow session-row mask). */
const SESSION_TITLE_GROUP_HOVER_MASK =
  'group-hover:[mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)] group-hover:[-webkit-mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)]'

export function SessionNavigationPanel({
  canLoadMore,
  statusFilter,
  error,
  onArchiveSession,
  onDeleteSession,
  onLoadMore,
  onRenameSession,
  onSelectSession,
  onStartNewSession,
  onStatusFilterChange,
  onUnarchiveSession,
  selectedSessionId,
  sessions,
  state,
}: {
  canLoadMore: boolean
  statusFilter: SessionNavigationFilter
  error: string | null
  onArchiveSession(sessionId: string): void
  onDeleteSession(sessionId: string): void
  onLoadMore(): void
  onRenameSession(sessionId: string, title: string): void
  onSelectSession(sessionId: string): void
  onStartNewSession(): void
  onStatusFilterChange(filter: SessionNavigationFilter): void
  onUnarchiveSession(sessionId: string): void
  selectedSessionId: string | null
  sessions: ChatSessionSummary[]
  state: RequestState
}) {
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState('')
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)
  const renameInputRef = useRef<HTMLInputElement | null>(null)
  const isLoading = state === 'loading'

  useEffect(() => {
    if (renamingSessionId === null) {
      return
    }
    // After Radix menu closes it restores focus; delay so we win the caret.
    const timeoutId = window.setTimeout(() => {
      const input = renameInputRef.current
      if (input === null) {
        return
      }
      input.focus()
      const end = input.value.length
      // Caret at end (not select-all) so the user can keep typing.
      input.setSelectionRange(end, end)
    }, 0)
    return () => window.clearTimeout(timeoutId)
  }, [renamingSessionId])

  function cancelRename() {
    setRenamingSessionId(null)
    setRenameDraft('')
  }

  useEffect(() => {
    if (copyFeedback === null) {
      return
    }
    const timeoutId = window.setTimeout(() => setCopyFeedback(null), 2000)
    return () => window.clearTimeout(timeoutId)
  }, [copyFeedback])

  async function handleCopySessionId(sessionId: string) {
    const ok = await copyTextToClipboard(sessionId)
    setCopyFeedback(
      ok ? 'ID de sesión copiado.' : 'No se pudo copiar el ID de sesión.',
    )
  }

  return (
    <Panel
      aria-labelledby="history-title"
      className="grid h-full min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-2 border-0 bg-transparent p-0 shadow-none max-[680px]:gap-0.5"
      role="complementary"
    >
      <h2 className="sr-only" id="history-title">
        Sesiones
      </h2>

      {/* Fixed chrome above the list — scrollbar starts at the first session. */}
      <div
        className="grid shrink-0 gap-2 pr-2.5 max-[680px]:gap-0.5 max-[680px]:pr-1"
        data-slot="session-list-chrome"
      >
        <Button
          className={cn(
            'h-auto w-full justify-center gap-1 rounded-md border border-dashed border-border bg-transparent py-2 text-xs font-medium text-muted-foreground shadow-none max-[680px]:gap-0.5 max-[680px]:py-0.5 max-[680px]:text-[0.5625rem]',
            'hover:border-primary/40 hover:bg-primary/15 hover:text-foreground',
          )}
          onClick={onStartNewSession}
          size="sm"
          type="button"
          variant="ghost"
        >
          <Plus aria-hidden="true" className="size-3.5 shrink-0" />
          Nuevo chat
        </Button>

        <SegmentedControl
          aria-label="Session Filters"
          className="grid w-full min-w-0 max-w-full grid-cols-[repeat(3,minmax(0,1fr))] gap-0.5 rounded-lg border-0 bg-muted/40 p-0.5 max-[680px]:rounded-md max-[680px]:border max-[680px]:border-primary/70"
        >
          {SESSION_FILTERS.map((filter) => (
            <SegmentedControlItem
              active={statusFilter === filter.value}
              aria-label={filter.title}
              className={cn(
                'h-auto min-h-0 min-w-0 w-full overflow-hidden px-0.5 py-1.5 text-[11px] leading-tight tracking-tight max-[680px]:min-h-11 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug',
                statusFilter === filter.value
                  ? 'font-semibold shadow-sm'
                  : 'font-medium',
              )}
              key={filter.value}
              onClick={() => onStatusFilterChange(filter.value)}
              title={filter.title}
            >
              <span className="block truncate">{filter.label}</span>
            </SegmentedControlItem>
          ))}
        </SegmentedControl>

        {error ? (
          <InlineFeedback tone="danger">{operatorSafeMessage(error)}</InlineFeedback>
        ) : null}
        {copyFeedback ? (
          <InlineFeedback
            data-slot="session-copy-feedback"
            role="status"
            tone="neutral"
          >
            {copyFeedback}
          </InlineFeedback>
        ) : null}
      </div>

      <div
        className="scrollbar-chat min-h-0 overflow-x-hidden overflow-y-auto"
        data-slot="session-list-scroll"
      >
      <DataList
        aria-label="Workspace Sessions"
        className="min-w-0 gap-0.5 pr-2.5 max-[680px]:pr-1"
      >
        {isLoading && sessions.length === 0 ? (
          <DataListItem className="border-0 bg-transparent p-2 shadow-none">
            <div
              aria-busy="true"
              aria-label="Cargando sesiones"
              className="grid w-full gap-2 max-[680px]:gap-0.5"
              data-slot="session-list-loading"
              role="status"
            >
              <span className="sr-only">Cargando...</span>
              <div aria-hidden="true" className="h-7 motion-safe:animate-pulse rounded-md bg-muted/25" />
              <div aria-hidden="true" className="h-7 w-11/12 motion-safe:animate-pulse rounded-md bg-muted/35" />
              <div aria-hidden="true" className="h-7 w-4/5 motion-safe:animate-pulse rounded-md bg-muted/30" />
            </div>
          </DataListItem>
        ) : sessions.length === 0 ? (
          <DataListItem className="border-0 bg-transparent p-2 shadow-none">
            <div
              data-slot="session-list-empty"
              data-status-filter={statusFilter}
            >
              <EmptyState className="border-dashed bg-transparent p-3 text-left text-xs tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                {sessionEmptyCopy(statusFilter)}
              </EmptyState>
            </div>
          </DataListItem>
        ) : (
          sessions.map((session) => {
            const title = sessionDisplayTitle(session)
            const isSelected = session.session_id === selectedSessionId
            const isArchived = session.archived_at !== null
            const hasTraining = sessionHasTraining(session)
            const isRenaming = renamingSessionId === session.session_id
            const trainingStatusLabel = hasTraining
              ? session.has_approved_training
                ? 'entrenamiento aprobado'
                : 'entrenamiento pendiente'
              : null
            const openSessionLabel =
              trainingStatusLabel === null
                ? `Abrir sesión ${title}`
                : `Abrir sesión ${title} (${trainingStatusLabel})`
            return (
              <DataListItem
                className={cn(
                  'group rounded-md border-0 bg-transparent p-0 text-muted-foreground shadow-none motion-safe:transition-colors',
                  isSelected
                    ? 'bg-primary/15 text-foreground'
                    : 'hover:bg-primary/15 hover:text-foreground',
                )}
                data-selected={isSelected ? '' : undefined}
                key={session.session_id}
              >
                {/* CSS grid so title shrinks; age/⋮ stay reserved. Title uses
                    beflow-style mask fade on hover / open menu. */}
                <div className="grid min-h-8 min-w-0 grid-cols-[1rem_minmax(0,1fr)_auto_1.75rem] items-center gap-1 px-1 py-0.5 max-[680px]:min-h-11 max-[680px]:grid-cols-[1rem_minmax(0,1fr)_auto_1.25rem] max-[680px]:gap-0.5">
                  <span
                    aria-hidden={!hasTraining}
                    className="flex w-4 items-center justify-start text-muted-foreground"
                    title={hasTraining ? 'Training' : undefined}
                  >
                    {hasTraining ? (
                      <Brain
                        aria-hidden="true"
                        className={cn(
                          'size-3.5 shrink-0',
                          session.has_approved_training
                            ? 'fill-primary/40 text-primary'
                            : 'text-primary/80',
                        )}
                      />
                    ) : null}
                  </span>
                  {isRenaming ? (
                    <form
                      className="min-w-0 py-0.5"
                      onSubmit={(event) => {
                        event.preventDefault()
                        const trimmedTitle = renameDraft.trim()
                        if (trimmedTitle.length === 0) {
                          cancelRename()
                          return
                        }
                        onRenameSession(session.session_id, trimmedTitle)
                        cancelRename()
                      }}
                    >
                      <Input
                        aria-label="Nuevo nombre de sesión"
                        className="h-7 text-xs max-[680px]:min-h-11 max-[680px]:text-[0.5625rem]"
                        maxLength={60}
                        onBlur={(event) => {
                          // Submit click blurs first — don't discard a pending save.
                          const next = event.relatedTarget
                          if (
                            next instanceof Element &&
                            next.closest('form') === event.currentTarget.form
                          ) {
                            return
                          }
                          const trimmedTitle = renameDraft.trim()
                          if (
                            trimmedTitle.length > 0 &&
                            trimmedTitle !== title
                          ) {
                            onRenameSession(session.session_id, trimmedTitle)
                          }
                          cancelRename()
                        }}
                        onChange={(event) => setRenameDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Escape') {
                            event.preventDefault()
                            cancelRename()
                          }
                        }}
                        ref={renameInputRef}
                        value={renameDraft}
                      />
                    </form>
                  ) : (
                    <Button
                      aria-current={isSelected ? 'true' : undefined}
                      aria-label={openSessionLabel}
                      className="h-auto min-h-8 w-full min-w-0 max-w-full justify-start overflow-hidden rounded-none px-0 py-1.5 text-left hover:bg-transparent focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background max-[680px]:min-h-11"
                      onClick={() => onSelectSession(session.session_id)}
                      title={title}
                      type="button"
                      variant="ghost"
                    >
                      <span
                        className={cn(
                          'block w-full min-w-0 truncate text-xs motion-safe:transition-[mask-image,-webkit-mask-image] motion-safe:duration-150',
                          // Soft trailing fade so glyphs don't collide with age/⋮.
                          'group-hover:text-clip group-focus-within:text-clip',
                          SESSION_TITLE_GROUP_HOVER_MASK,
                          'group-focus-within:[mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)]',
                          'group-focus-within:[-webkit-mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)]',
                          'group-has-[[data-state=open]]:text-clip',
                          'group-has-[[data-state=open]]:[mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)]',
                          'group-has-[[data-state=open]]:[-webkit-mask-image:linear-gradient(to_right,black_0%,black_62%,transparent_91%)]',
                        )}
                        data-slot="session-row-title"
                      >
                        {title}
                      </span>
                    </Button>
                  )}
                  <span
                    className={cn(
                      'justify-self-end min-w-[3ch] text-[10px] tabular-nums text-muted-foreground motion-safe:transition-opacity motion-safe:duration-150',
                      // beflow: age yields to the ⋮ on row hover / open menu
                      'group-hover:opacity-0 group-focus-within:opacity-0',
                      'group-has-[[data-state=open]]:opacity-0',
                    )}
                    data-slot="session-row-age"
                    title={sessionAgeTooltip(session)}
                  >
                    {formatRelativeSessionAge(sessionLastActivityAt(session))}
                  </span>
                  <div
                    className="flex items-center justify-end"
                    data-slot="session-row-actions"
                  >
                    <DropdownMenu.Root>
                      <DropdownMenu.Trigger asChild>
                        <Button
                          aria-label={`Opciones de ${title}`}
                          className="size-7 shrink-0 rounded-md p-0 text-muted-foreground/60 hover:bg-primary/15 hover:text-foreground group-hover:text-foreground group-focus-within:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background max-[680px]:size-11"
                          type="button"
                          variant="ghost"
                        >
                          <MoreVertical aria-hidden="true" className="size-4" />
                        </Button>
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Portal>
                        <DropdownMenu.Content
                          align="end"
                          className="z-50 grid min-w-[140px] gap-0.5 rounded-md border border-border bg-popover p-1 text-sm tracking-tight text-popover-foreground shadow-[var(--shadow-popover)] max-[680px]:text-[0.5625rem] max-[680px]:gap-0.5 max-[680px]:p-0.5"
                          data-slot="session-actions-menu"
                          onCloseAutoFocus={(event) => event.preventDefault()}
                          sideOffset={4}
                        >
                          <DropdownMenu.Item
                            className="justify-between gap-3 px-3 py-1.5 text-left max-[680px]:gap-0.5 max-[680px]:px-0.5 max-[680px]:py-0.5"
                            data-testid={`copy-id-${session.session_id}`}
                            onClick={() => {
                              void handleCopySessionId(session.session_id)
                            }}
                          >
                            <span>Copiar ID de sesión</span>
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            className="px-3 py-1.5 text-left max-[680px]:px-0.5 max-[680px]:py-0.5"
                            data-testid={`rename-${session.session_id}`}
                            onClick={() => {
                              setRenamingSessionId(session.session_id)
                              setRenameDraft(title)
                            }}
                          >
                            Renombrar
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            className="px-3 py-1.5 text-left max-[680px]:px-0.5 max-[680px]:py-0.5"
                            data-testid={`${isArchived ? 'unarchive' : 'archive'}-${session.session_id}`}
                            onClick={() => {
                              if (isArchived) {
                                onUnarchiveSession(session.session_id)
                              } else {
                                onArchiveSession(session.session_id)
                              }
                            }}
                          >
                            {isArchived ? 'Desarchivar' : 'Archivar'}
                          </DropdownMenu.Item>
                          <DropdownMenu.Item
                            className="px-3 py-1.5 text-left text-destructive max-[680px]:px-1 max-[680px]:py-0.5"
                            data-testid={`delete-${session.session_id}`}
                            onClick={() => {
                              if (
                                window.confirm(
                                  '¿Eliminar esta sesión de forma permanente? No se puede deshacer.',
                                )
                              ) {
                                onDeleteSession(session.session_id)
                              }
                            }}
                          >
                            Eliminar
                          </DropdownMenu.Item>
                        </DropdownMenu.Content>
                      </DropdownMenu.Portal>
                    </DropdownMenu.Root>
                  </div>
                </div>
              </DataListItem>
            )
          })
        )}
      </DataList>
      {canLoadMore ? (
        <Button
          className="h-auto w-full justify-center py-1.5 text-xs text-muted-foreground hover:bg-primary/15 hover:text-foreground max-[680px]:min-h-11 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug"
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
          variant="ghost"
        >
          {isLoading ? 'Cargando…' : 'Ver más'}
        </Button>
      ) : null}
      </div>
    </Panel>
  )
}

export function WorkspaceInspectorPanel({
  activeTab,
  detail,
  detailError,
  detailState,
  focusedTurn = null,
  layout,
  liveContextSteps = null,
  onActiveTabChange,
  onClearFocusedTurn,
  onClose,
  onNavigateMessage,
  onOpenSource,
  onStartNewSession,
  sourceViewer,
}: {
  activeTab: InspectorTab
  detail: ChatSessionDetailResponse | null
  detailError: string | null
  detailState: RequestState
  /** When set, Context shows only this turn’s tools/messages. */
  focusedTurn?: FocusedTurn | null
  layout: 'inline' | 'overlay'
  /** Freshest context packing step from the in-flight / latest chat response. */
  liveContextSteps?: ChatStep[] | null
  onActiveTabChange(tab: InspectorTab): void
  onClearFocusedTurn?(): void
  onClose(): void
  onNavigateMessage(messageId: string): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onStartNewSession?(): void
  sourceViewer: SourceViewerState
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const isOverlay = layout === 'overlay'
  const isTurnFocused = focusedTurn !== null
  const scopedDetail =
    isTurnFocused && detail !== null
      ? (filterSessionDetailToTurn(detail, focusedTurn.turnId) ?? {
          ...detail,
          messages: [],
          provider_usage: [],
          retrieval_runs: [],
          tool_calls: [],
        })
      : detail
  useFocusTrap(panelRef, isOverlay)

  useEffect(() => {
    // Inline dock stays open on Escape; only the modal overlay closes.
    if (!isOverlay) {
      return
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || event.defaultPrevented) {
        return
      }
      // Don't steal Escape from open menus/dialogs inside the panel.
      const target = event.target
      if (
        target instanceof HTMLElement &&
        target.closest(
          '[data-state="open"][role="menu"], [data-state="open"][role="listbox"], [role="dialog"][data-state="open"]',
        )
      ) {
        return
      }
      event.preventDefault()
      onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isOverlay, onClose])

  useEffect(() => {
    if (!isOverlay) {
      return
    }
    closeButtonRef.current?.focus()
  }, [isOverlay])

  return (
    <Panel
      aria-label="Workspace Inspector"
      aria-modal={isOverlay ? true : undefined}
      className={
        layout === 'inline'
          ? 'workspace-inspector-inline relative z-[1] grid h-full min-h-0 w-[360px] min-w-[330px] max-w-[390px] shrink-0 gap-3 overflow-hidden p-3 max-[680px]:gap-0.5 max-[680px]:p-0.5'
          : 'workspace-inspector-overlay fixed bottom-6 right-6 top-6 z-[70] grid min-h-0 max-h-none w-[min(420px,calc(100vw-48px))] gap-3 rounded-none border-y-0 border-r-0 border-l border-l-primary/25 p-3 shadow-[var(--shadow-inspector-overlay)] max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:inset-0 max-[680px]:w-auto max-[680px]:border-l-0 max-[680px]:pt-[max(0.25rem,env(safe-area-inset-top))] max-[680px]:pb-[max(0.25rem,env(safe-area-inset-bottom))]'
      }
      ref={panelRef}
      role={isOverlay ? 'dialog' : 'complementary'}
      tabIndex={isOverlay ? -1 : undefined}
    >
      <div className="flex items-center justify-between gap-2 max-[680px]:gap-0.5">
        <SegmentedControl
          aria-label="Inspector Panels"
          className="max-w-full flex-wrap"
          role="tablist"
        >
          <SegmentedControlItem
            active={activeTab === 'context'}
            aria-controls="context-panel"
            aria-selected={activeTab === 'context'}
            id="context-tab"
            onClick={() => onActiveTabChange('context')}
            role="tab"
          >
            Context
          </SegmentedControlItem>
          <SegmentedControlItem
            active={activeTab === 'minimap'}
            aria-controls="minimap-panel"
            aria-selected={activeTab === 'minimap'}
            id="minimap-tab"
            onClick={() => onActiveTabChange('minimap')}
            role="tab"
          >
            Minimap
          </SegmentedControlItem>
        </SegmentedControl>
        <IconButton
          label="Close Right Sidebar"
          onClick={onClose}
          ref={closeButtonRef}
          variant="ghost"
        >
          <X aria-hidden="true" className="size-4" />
        </IconButton>
      </div>

      {activeTab === 'context' ? (
        <div
          aria-labelledby="context-tab"
          className="grid min-h-0 gap-3 overflow-y-auto max-[680px]:gap-0.5"
          data-slot="context-inspector-stack"
          data-turn-focused={isTurnFocused ? 'true' : undefined}
          id="context-panel"
          role="tabpanel"
        >
          {focusedTurn !== null ? (
            <TurnFocusHeader
              onClearFocusedTurn={onClearFocusedTurn}
              question={focusedTurn.question}
            />
          ) : (
            /* 1. Primary: what thread / model / usage (scannable) */
            <SessionContextPanel
              detail={detail}
              liveContextSteps={liveContextSteps}
              onStartNewSession={onStartNewSession}
              state={detailState}
            />
          )}
          {/* Session load errors used to live under Messages; keep them visible in overview. */}
          {!isTurnFocused && detailError !== null && detailError.trim().length > 0 ? (
            <InlineFeedback role="alert" tone="danger">
              {operatorSafeMessage(detailError)}
            </InlineFeedback>
          ) : null}
          {/* 2. Only when a citation is open */}
          <SourceViewerPanel viewer={sourceViewer} />
          {/* 3. Session overview: pipeline summary only (no full message/turn dump).
              Per-turn messages + tool/retrieval detail: answer ⋯ → Ver detalles. */}
          <InternalActionStepper
            defaultOpen={isTurnFocused}
            detail={scopedDetail}
            state={detailState}
          />
          {isTurnFocused ? (
            <SessionDetailPanel
              detail={scopedDetail}
              error={detailError}
              onOpenSource={onOpenSource}
              state={detailState}
              turnScoped
            />
          ) : null}
        </div>
      ) : (
        <div
          aria-labelledby="minimap-tab"
          className="min-h-0 overflow-y-auto"
          id="minimap-panel"
          role="tabpanel"
        >
          <ConversationMinimap
            detail={detail}
            onNavigateMessage={onNavigateMessage}
            state={detailState}
          />
        </div>
      )}
    </Panel>
  )
}

function SourceViewerPanel({ viewer }: { viewer: SourceViewerState }) {
  if (viewer.state === 'idle' && viewer.sourceId === null) {
    return null
  }

  return (
    <Panel aria-label="Source Viewer" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <PanelTitle>Source Viewer</PanelTitle>
        <StatusBadge tone={sourceViewerTone(viewer.state)}>
          {sourceViewerStatusLabel(viewer.state)}
        </StatusBadge>
      </PanelHeader>
      <PanelBody className="grid gap-3 p-4 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">
        {viewer.state === 'loading' ? (
          <div
            aria-busy="true"
            aria-label={`Loading Source ${viewer.sourceId ?? ''}`}
            className="grid w-full gap-2 max-[680px]:gap-0.5"
            data-slot="source-viewer-loading"
            role="status"
          >
            <span className="sr-only">
              Loading Source {viewer.sourceId}...
            </span>
            <div
              aria-hidden="true"
              className="h-3 w-1/3 motion-safe:animate-pulse rounded bg-muted/25"
            />
            <div
              aria-hidden="true"
              className="h-3 w-full motion-safe:animate-pulse rounded bg-muted/35"
            />
            <div
              aria-hidden="true"
              className="h-3 w-11/12 motion-safe:animate-pulse rounded bg-muted/30"
            />
            <div
              aria-hidden="true"
              className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted/25"
            />
          </div>
        ) : null}

        {viewer.error ? (
          <InlineFeedback role="alert" tone="danger">
            {operatorSafeMessage(viewer.error)}
          </InlineFeedback>
        ) : null}

        {viewer.citationSnippet === null ? null : (
          <section className="grid gap-1 max-[680px]:gap-0.5">
            <h4 className="text-sm font-semibold text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
              Citation Snippet
            </h4>
            <p className="text-sm leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
              {viewer.citationSnippet}
            </p>
          </section>
        )}

        {viewer.source ? (
          <div className="grid gap-3 max-[680px]:gap-0.5">
            <div className="flex min-w-0 flex-wrap items-center gap-2 max-[680px]:gap-0.5">
              <p className="min-w-0 break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                {viewer.source.external_id}
              </p>
              {viewer.source.deleted_at ? (
                <StatusBadge className="w-fit shrink-0" tone="danger">
                  Deleted
                </StatusBadge>
              ) : null}
            </div>
            <dl className="grid gap-2 max-[680px]:gap-0.5">
              <MetadataItem label="ID" value={viewer.source.id} />
              <MetadataItem label="Type" value={viewer.source.source_type} />
              <MetadataItem label="Created" value={viewer.source.created_at} />
              <MetadataItem label="Updated" value={viewer.source.updated_at} />
              {viewer.source.deleted_at ? (
                <MetadataItem
                  label="Deleted"
                  value={formatSourceTimestamp(viewer.source.deleted_at)}
                />
              ) : null}
            </dl>

            <section className="grid gap-2 max-[680px]:gap-0.5">
              <h4 className="text-sm font-semibold text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">Tags</h4>
              {viewer.source.tags === null || viewer.source.tags.length === 0 ? (
                <EmptyState>No Tags Stored.</EmptyState>
              ) : (
                <div className="flex flex-wrap gap-2 max-[680px]:gap-0.5">
                  {viewer.source.tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
              )}
            </section>

            <section className="grid gap-2 max-[680px]:gap-0.5">
              <h4 className="text-sm font-semibold text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">Metadata</h4>
              {viewer.source.extra_metadata === null ||
              Object.keys(viewer.source.extra_metadata).length === 0 ? (
                <EmptyState>No Metadata Stored.</EmptyState>
              ) : (
                <dl className="grid gap-2 max-[680px]:gap-0.5">
                  {Object.entries(viewer.source.extra_metadata).map(([key, value]) => (
                    <MetadataItem
                      key={key}
                      label={key}
                      value={formatJsonValue(value)}
                    />
                  ))}
                </dl>
              )}
            </section>
          </div>
        ) : null}
      </PanelBody>
    </Panel>
  )
}

function ConversationMinimap({
  detail,
  onNavigateMessage,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  onNavigateMessage(messageId: string): void
  state: RequestState
}) {
  return (
    <Panel aria-label="Conversation Minimap" role="navigation">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <PanelTitle>Minimap</PanelTitle>
        <StatusBadge>
          {detail?.messages.length ?? 0}{' '}
          {(detail?.messages.length ?? 0) === 1 ? 'Message' : 'Messages'}
        </StatusBadge>
      </PanelHeader>
      <PanelBody className="p-4 pt-0 max-[680px]:p-0.5 max-[680px]:pt-0">
        {state === 'loading' ? (
          <InspectorLoadingSkeleton
            ariaLabel="Loading Conversation Minimap"
            slot="conversation-minimap-loading"
          />
        ) : detail === null || detail.messages.length === 0 ? (
          <EmptyState>Select A Session To Navigate Messages.</EmptyState>
        ) : (
          <DataList aria-label="Conversation Messages">
            {detail.messages.map((message) => (
              <DataListItem className="p-0 shadow-none" key={message.message_id}>
                <Button
                  aria-label={minimapMessageLabel(message.role, message.content)}
                  className="h-auto w-full justify-start whitespace-normal px-2 py-2 text-left max-[680px]:min-h-11"
                  onClick={() => onNavigateMessage(message.message_id)}
                  type="button"
                  variant="ghost"
                >
                  <span className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                    <strong className="text-sm capitalize text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                      {message.role}
                    </strong>
                    <span className="line-clamp-2 break-all text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                      {message.content}
                    </span>
                  </span>
                </Button>
              </DataListItem>
            ))}
          </DataList>
        )}
      </PanelBody>
    </Panel>
  )
}

function SessionContextPanel({
  detail,
  liveContextSteps = null,
  onStartNewSession,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  liveContextSteps?: ChatStep[] | null
  onStartNewSession?(): void
  state: RequestState
}) {
  const firstUsage = detail?.provider_usage[0] ?? null
  const contextWindow = resolveContextWindowSummary(detail, liveContextSteps)
  const messageCount = detail?.messages.length ?? 0
  const isContinuingThread = detail !== null && messageCount > 0
  const sessionTitle =
    detail?.session.title?.trim() ||
    (detail !== null ? shortSessionId(detail.session.session_id) : null)

  return (
    <Panel aria-label="Session Context" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-3 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <div className="grid min-w-0 gap-0.5">
          <PanelTitle>This thread</PanelTitle>
          <p className="text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]">
            Snapshot of the active chat session
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          {isContinuingThread ? (
            <StatusBadge tone="primary">Continuing</StatusBadge>
          ) : null}
          <StatusBadge tone={sessionStatusTone(detail?.session.status)}>
            {sessionStatusLabel(detail?.session.status)}
          </StatusBadge>
        </div>
      </PanelHeader>
      <PanelBody className="grid gap-3 p-3 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">
        {state === 'loading' ? (
          <InspectorLoadingSkeleton
            ariaLabel="Loading Session Context"
            slot="session-context-loading"
          />
        ) : detail === null ? (
          <EmptyState>
            Select a session to see model, usage, and context packing.
          </EmptyState>
        ) : (
          <>
            {/* 1. Identity + actions */}
            <section
              aria-label="Thread identity"
              className="grid gap-2 rounded-md border border-border/70 bg-muted/15 p-2.5 max-[680px]:gap-0.5 max-[680px]:p-0.5"
              data-slot="session-context-identity"
            >
              <div className="flex min-w-0 items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground max-[680px]:text-[0.6875rem]">
                    {sessionTitle}
                  </p>
                  <p
                    className="mt-0.5 break-all font-mono text-[11px] text-muted-foreground max-[680px]:text-[0.5625rem]"
                    title={detail.session.session_id}
                  >
                    {shortSessionId(detail.session.session_id)}
                    {messageCount > 0
                      ? ` · ${messageCount} message${messageCount === 1 ? '' : 's'}`
                      : ''}
                  </p>
                </div>
                {onStartNewSession !== undefined ? (
                  <Button
                    className="h-7 shrink-0 px-2 text-[11px]"
                    data-slot="session-context-new-thread"
                    onClick={onStartNewSession}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    New thread
                  </Button>
                ) : null}
              </div>
            </section>

            {/* 2. Model used */}
            <section
              aria-label="Model used"
              className="grid gap-1.5"
              data-slot="session-context-model"
            >
              <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:text-[0.5625rem]">
                Model
              </h3>
              <div className="grid gap-1 rounded-md border border-border/70 bg-card p-2.5 max-[680px]:p-0.5">
                <p className="break-words text-sm font-semibold text-foreground max-[680px]:text-[0.6875rem]">
                  {firstUsage?.model ?? 'Unknown model'}
                </p>
                <p className="text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]">
                  {firstUsage === null
                    ? 'No provider usage recorded yet'
                    : `${firstUsage.provider} · ${firstUsage.operation} · ${titleCaseToken(firstUsage.status)}`}
                </p>
                <p className="text-[11px] text-muted-foreground max-[680px]:text-[0.5625rem]">
                  Prompt {detail.session.prompt_version ?? 'unknown'}
                </p>
              </div>
            </section>

            {/* 3. Usage strip */}
            <section
              aria-label="Usage summary"
              className="grid gap-1.5"
              data-slot="session-context-usage"
            >
              <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:text-[0.5625rem]">
                Usage
              </h3>
              <div className="grid grid-cols-3 gap-1.5 max-[680px]:gap-0.5">
                <UsageCell
                  label="Cost"
                  value={formatSessionCost(detail.provider_usage)}
                />
                <UsageCell
                  label="Tokens"
                  value={formatSessionTokens(detail.provider_usage)}
                />
                <UsageCell
                  label="Latency"
                  value={formatSessionLatency(detail.provider_usage)}
                />
              </div>
              {detail.provider_usage.length > 0 ? (
                <p className="text-[10px] text-muted-foreground max-[680px]:text-[0.5625rem]">
                  {detail.provider_usage.length} provider record
                  {detail.provider_usage.length === 1 ? '' : 's'}
                </p>
              ) : null}
            </section>

            {/* 4. Context packing (only when meaningful) */}
            {contextWindow !== null || messageCount > 0 ? (
              <section
                aria-label="Context packing"
                className="grid gap-1.5"
                data-slot="session-context-window"
              >
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:text-[0.5625rem]">
                  Context window
                </h3>
                <ContextWindowCard
                  label={contextWindow?.label ?? `${messageCount} messages`}
                  summaryText={
                    contextWindow?.summaryFull ??
                    contextWindow?.summaryPreview ??
                    null
                  }
                />
              </section>
            ) : null}
          </>
        )}
      </PanelBody>
    </Panel>
  )
}

function UsageCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5 rounded-md border border-border/70 bg-card px-2 py-2 text-center max-[680px]:px-0.5 max-[680px]:py-0.5">
      <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground max-[680px]:text-[0.5rem]">
        {label}
      </span>
      <strong className="break-words text-xs font-semibold tabular-nums text-foreground max-[680px]:text-[0.625rem]">
        {value}
      </strong>
    </div>
  )
}

/** Collapsed by default; expand shows full condensed history summary. */
const CONTEXT_WINDOW_COLLAPSE_CHARS = 180

function ContextWindowCard({
  label,
  summaryText,
}: {
  label: string
  summaryText: string | null
}) {
  const [expanded, setExpanded] = useState(false)
  const text = summaryText?.trim() ?? ''
  const canExpand = text.length > CONTEXT_WINDOW_COLLAPSE_CHARS

  return (
    <div
      className="rounded-md border border-border/70 bg-muted/15 p-2.5 max-[680px]:p-0.5"
      data-slot="context-window-card"
      data-expanded={expanded ? 'true' : 'false'}
    >
      <p className="text-sm font-medium text-foreground max-[680px]:text-[0.6875rem]">
        {label}
      </p>
      {text.length > 0 ? (
        <>
          <p
            className={cn(
              'mt-1 text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]',
              expanded
                ? 'max-h-64 overflow-y-auto whitespace-pre-wrap break-words'
                : 'line-clamp-3',
            )}
            data-slot="context-window-summary"
          >
            {text}
          </p>
          {canExpand ? (
            <Button
              aria-expanded={expanded}
              className="mt-1.5 h-7 gap-1 px-2 text-[11px] text-muted-foreground hover:text-foreground"
              data-slot="context-window-expand"
              onClick={() => setExpanded((current) => !current)}
              size="sm"
              type="button"
              variant="ghost"
            >
              {expanded ? (
                <ChevronUp aria-hidden="true" className="size-3.5" />
              ) : (
                <ChevronDown aria-hidden="true" className="size-3.5" />
              )}
              {expanded ? 'Contraer' : 'Expandir'}
            </Button>
          ) : null}
        </>
      ) : (
        <p className="mt-1 text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]">
          How much history is kept raw vs summarized for the model.
        </p>
      )}
    </div>
  )
}

function resolveContextWindowSummary(
  detail: ChatSessionDetailResponse | null,
  liveContextSteps: ChatStep[] | null | undefined,
) {
  const live = summarizeContextWindow(liveContextSteps)
  if (live !== null) {
    return live
  }
  if (detail === null) {
    return null
  }
  for (let index = detail.messages.length - 1; index >= 0; index -= 1) {
    const message = detail.messages[index]
    if (message?.role !== 'assistant') {
      continue
    }
    const fromMetadata = summarizeContextWindow(
      parseChatStepsFromMetadata(message.metadata ?? null),
    )
    if (fromMetadata !== null) {
      return fromMetadata
    }
  }
  return null
}

function TurnFocusHeader({
  onClearFocusedTurn,
  question,
}: {
  onClearFocusedTurn?(): void
  question: string
}) {
  const preview =
    question.trim().length === 0
      ? 'Sin pregunta'
      : question.trim().length > 120
        ? `${question.trim().slice(0, 117)}…`
        : question.trim()

  return (
    <Panel
      aria-label="Detalles del turno"
      data-slot="turn-focus-header"
      role="region"
    >
      <PanelHeader className="flex-row items-start justify-between gap-2 p-3 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <div className="grid min-w-0 gap-0.5">
          <PanelTitle>Detalles del turno</PanelTitle>
          <p
            className="line-clamp-2 text-[11px] leading-snug text-muted-foreground max-[680px]:text-[0.5625rem]"
            title={question.trim() || undefined}
          >
            {preview}
          </p>
        </div>
        {onClearFocusedTurn !== undefined ? (
          <Button
            className="h-7 shrink-0 px-2 text-[11px]"
            data-slot="turn-focus-clear"
            onClick={onClearFocusedTurn}
            size="sm"
            type="button"
            variant="secondary"
          >
            Ver sesión completa
          </Button>
        ) : null}
      </PanelHeader>
    </Panel>
  )
}

function InternalActionStepper({
  defaultOpen = false,
  detail,
  state,
}: {
  defaultOpen?: boolean
  detail: ChatSessionDetailResponse | null
  state: RequestState
}) {
  const stepCount = countInternalSteps(detail)
  // Controlled open so turn-focus starts expanded; user can still collapse.
  // Key remounts when defaultOpen changes so initial open state resets without
  // an effect that calls setState (react-hooks/set-state-in-effect).
  return (
    <PipelineActivityDetailsBody
      detail={detail}
      initiallyOpen={defaultOpen}
      key={defaultOpen ? 'pipeline-open' : 'pipeline-closed'}
      state={state}
      stepCount={stepCount}
    />
  )
}

function PipelineActivityDetailsBody({
  detail,
  initiallyOpen,
  state,
  stepCount,
}: {
  detail: ChatSessionDetailResponse | null
  initiallyOpen: boolean
  state: RequestState
  stepCount: number
}) {
  const [isOpen, setIsOpen] = useState(initiallyOpen)

  return (
    <details
      className="group rounded-md border border-border/70 bg-card open:bg-card"
      data-slot="context-action-stepper-details"
      onToggle={(event) => {
        setIsOpen(event.currentTarget.open)
      }}
      open={isOpen}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 p-3 marker:content-none [&::-webkit-details-marker]:hidden max-[680px]:min-h-11 max-[680px]:p-0.5">
        <span className="text-sm font-semibold text-foreground max-[680px]:text-[0.6875rem]">
          Pipeline activity
        </span>
        <StatusBadge>
          {stepCount} Step{stepCount === 1 ? '' : 's'}
        </StatusBadge>
      </summary>
      <div
        aria-label="Internal Action Stepper"
        className="border-t border-border/60 p-3 pt-2 max-[680px]:p-0.5"
        role="region"
      >
        {state === 'loading' ? (
          <InspectorLoadingSkeleton
            ariaLabel="Loading Action Stepper"
            slot="action-stepper-loading"
          />
        ) : detail === null || stepCount === 0 ? (
          <EmptyState className="max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
            No tool or retrieval activity stored for this session.
          </EmptyState>
        ) : (
          <DataList>
            {detail.tool_calls.map((call) => (
              <DataListItem className="grid gap-1 max-[680px]:gap-0.5" key={`tool-${call.tool_call_id}`}>
                <Badge>
                  Tool Call {titleCaseToken(call.status)}
                </Badge>
                <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{call.tool_name}</strong>
                <p className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {formatJsonValue(call.arguments)}
                </p>
                <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {formatUnknownMs(call.latency_ms)}
                </small>
              </DataListItem>
            ))}
            {detail.retrieval_runs.map((run) => (
              <DataListItem
                className="grid gap-2 max-[680px]:gap-0.5"
                key={`retrieval-${run.retrieval_run_id}`}
              >
                <Badge>
                  Retrieval {titleCaseToken(run.strategy)}
                </Badge>
                <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{run.query}</strong>
                <p className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  Top {run.top_k} / {formatUnknownMs(run.latency_ms)}
                </p>
                <DataList>
                  {run.retrieved_chunks.map((chunk) => (
                    <DataListItem key={chunk.retrieved_chunk_id}>
                      <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                        Rank {chunk.rank}
                      </strong>
                      <small className="block text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                        {formatStepperScores(chunk)}
                      </small>
                    </DataListItem>
                  ))}
                </DataList>
              </DataListItem>
            ))}
            {detail.provider_usage.map((usage) => (
              <DataListItem
                className="grid gap-1 max-[680px]:gap-0.5"
                key={`provider-${usage.provider_usage_id}`}
              >
                <Badge>
                  Provider Usage {titleCaseToken(usage.status)}
                </Badge>
                <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{usage.model}</strong>
                <p className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {usage.provider} {usage.operation} /{' '}
                  {formatUnknownTokens(usage.total_tokens)} /{' '}
                  {formatUnknownCost(usage.estimated_cost_usd)}
                </p>
                <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {formatUnknownMs(usage.latency_ms)}
                </small>
              </DataListItem>
            ))}
          </DataList>
        )}
      </div>
    </details>
  )
}

function SessionDetailPanel({
  detail,
  error,
  onOpenSource,
  state,
  turnScoped = false,
}: {
  detail: ChatSessionDetailResponse | null
  error: string | null
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  state: RequestState
  turnScoped?: boolean
}) {
  if (state === 'loading') {
    return (
      <Panel aria-live="polite" role="region">
        <PanelHeader className="p-3 max-[680px]:p-0.5">
          <PanelTitle>Messages</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-3 pt-0 max-[680px]:p-0.5 max-[680px]:pt-0">
          <div
            aria-busy="true"
            aria-label="Loading Session Detail"
            className="grid w-full gap-3 max-[680px]:gap-0.5"
            data-slot="session-detail-loading"
            role="status"
          >
            <span className="sr-only">Loading Session Detail...</span>
            <div aria-hidden="true" className="grid gap-2 max-[680px]:gap-0.5">
              <div className="h-3 w-1/4 motion-safe:animate-pulse rounded bg-muted/25" />
              <div className="h-3 w-full motion-safe:animate-pulse rounded bg-muted/35" />
              <div className="h-3 w-11/12 motion-safe:animate-pulse rounded bg-muted/30" />
              <div className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted/25" />
            </div>
            <div aria-hidden="true" className="grid gap-2 pt-1 max-[680px]:gap-0.5 max-[680px]:pt-0.5">
              <div className="h-3 w-1/5 motion-safe:animate-pulse rounded bg-muted/25" />
              <div className="h-16 w-full motion-safe:animate-pulse rounded-md bg-muted/25" />
              <div className="h-16 w-full motion-safe:animate-pulse rounded-md bg-muted/25" />
            </div>
          </div>
        </PanelBody>
      </Panel>
    )
  }

  if (error) {
    return (
      <Panel role="region">
        <PanelHeader className="p-3 max-[680px]:p-0.5">
          <PanelTitle>Messages</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-3 pt-0 max-[680px]:p-0.5 max-[680px]:pt-0">
          <InlineFeedback role="alert" tone="danger">
            {operatorSafeMessage(error)}
          </InlineFeedback>
        </PanelBody>
      </Panel>
    )
  }

  if (detail === null) {
    return (
      <Panel role="region">
        <PanelHeader className="p-3 max-[680px]:p-0.5">
          <PanelTitle>Messages</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-3 pt-0 max-[680px]:p-0.5 max-[680px]:pt-0">
          <EmptyState>Select a session to inspect stored history.</EmptyState>
        </PanelBody>
      </Panel>
    )
  }

  return (
    <Panel aria-label="Selected Session Detail" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-3 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
          <PanelTitle>{turnScoped ? 'Turn messages' : 'Messages'}</PanelTitle>
          <p className="break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
            {turnScoped
              ? `${detail.messages.length} in this turn`
              : detail.session.session_id}
          </p>
        </div>
        <StatusBadge tone={sessionStatusTone(detail.session.status)}>
          {sessionStatusLabel(detail.session.status)}
        </StatusBadge>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">
        <section className="grid gap-2 max-[680px]:gap-0.5" aria-labelledby="messages-title">
          <h4 id="messages-title" className="text-sm font-semibold text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
            Messages
          </h4>
          <DataList aria-label="Session Messages">
            {detail.messages.length === 0 ? (
              <EmptyState className="max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                {turnScoped
                  ? 'No messages stored for this turn yet.'
                  : 'No Messages In This Session.'}
              </EmptyState>
            ) : (
              detail.messages.map((message) => (
                <DataListItem key={message.message_id}>
                  <article
                    aria-label={`${message.role} message`}
                    className="grid gap-1 max-[680px]:gap-0.5"
                    id={messageElementId(message.message_id)}
                    tabIndex={-1}
                  >
                    <strong className="text-sm capitalize text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                      {message.role}
                    </strong>
                    <p className="text-sm leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                      {message.content}
                    </p>
                  </article>
                </DataListItem>
              ))
            )}
          </DataList>
        </section>

        <DetailSection id="history-tools-title" title="Tool Calls">
          <CompactStateList
            emptyLabel="No Stored Tool Calls."
            items={detail.tool_calls}
            renderItem={(call) => (
              <ToolCallDetail call={call} key={call.tool_call_id} />
            )}
          />
        </DetailSection>

        <DetailSection id="retrieval-runs-title" title="Retrieval Runs">
          <CompactStateList
            emptyLabel="No Stored Retrieval Runs."
            items={detail.retrieval_runs}
            renderItem={(run) => (
              <RetrievalRunDetail
                key={run.retrieval_run_id}
                onOpenSource={onOpenSource}
                run={run}
              />
            )}
          />
        </DetailSection>

        <DetailSection id="provider-usage-title" title="Provider Usage">
          <CompactStateList
            emptyLabel="No Provider Usage Stored."
            items={detail.provider_usage}
            renderItem={(usage) => (
              <ProviderUsageDetail key={usage.provider_usage_id} usage={usage} />
            )}
          />
        </DetailSection>
      </PanelBody>
    </Panel>
  )
}

function DetailSection({
  children,
  id,
  title,
}: {
  children: ReactNode
  id: string
  title: string
}) {
  return (
    <section className="grid gap-2 max-[680px]:gap-0.5" aria-labelledby={id}>
      <h4 id={id} className="text-sm font-semibold tracking-tight text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {title}
      </h4>
      {children}
    </section>
  )
}

function CompactStateList<T>({
  emptyLabel,
  items,
  renderItem,
}: {
  emptyLabel: string
  items: T[]
  renderItem(item: T): ReactNode
}) {
  if (items.length === 0) {
    return <EmptyState>{emptyLabel}</EmptyState>
  }

  return <DataList>{items.map(renderItem)}</DataList>
}

function ToolCallDetail({ call }: { call: ChatHistoryToolCall }) {
  return (
    <DataListItem key={call.tool_call_id}>
      <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{call.tool_name}</strong>
      <p className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {formatJsonValue(call.arguments)}
      </p>
      <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{call.status}</small>
    </DataListItem>
  )
}

function RetrievalRunDetail({
  onOpenSource,
  run,
}: {
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  run: ChatHistoryRetrievalRun
}) {
  return (
    <DataListItem className="grid gap-2 max-[680px]:gap-0.5" key={run.retrieval_run_id}>
      <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">{run.query}</strong>
      <div className="flex flex-wrap gap-2 max-[680px]:gap-0.5">
        <Badge>{retrievalStrategyLabel(run)}</Badge>
        <Badge>Top {run.top_k}</Badge>
        {run.latency_ms === null ? null : (
          <Badge>Latency {run.latency_ms} ms</Badge>
        )}
      </div>
      <DataList>
        {run.retrieved_chunks.map((chunk) => (
          <RetrievedChunkDetail
            chunk={chunk}
            key={chunk.retrieved_chunk_id}
            onOpenSource={onOpenSource}
          />
        ))}
      </DataList>
    </DataListItem>
  )
}

function RetrievedChunkDetail({
  chunk,
  onOpenSource,
}: {
  chunk: ChatHistoryRetrievedChunk
  onOpenSource(sourceId: string, citationSnippet: string | null): void
}) {
  const scores = [
    formatOptionalScore('Dense Score', chunk.dense_score),
    formatOptionalScore('Lexical Score', chunk.lexical_score),
    formatOptionalScore('RRF Score', chunk.rrf_score),
    formatOptionalScore('Rerank Score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  const sourceId = getJsonString(chunk.citation, 'source_id')
  const citationSnippet = getJsonString(chunk.citation, 'snippet')
  const sourceLabel =
    getJsonString(chunk.citation, 'source_external_id') ?? sourceId
  const isCascadeDeleted = chunk.chunk_id === null

  return (
    <DataListItem className="grid gap-2 max-[680px]:gap-0.5">
      <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
        <Badge>Rank {chunk.rank}</Badge>
        {isCascadeDeleted ? (
          <StatusBadge className="w-fit" tone="warning">
            Source Removed
          </StatusBadge>
        ) : null}
      </div>
      <div className="grid gap-2 max-[680px]:gap-0.5">
        <p
          className={cn(
            'text-sm text-muted-foreground',
            isCascadeDeleted && 'italic',
          )}
        >
          {getCitationText(chunk.citation, 'snippet')}
        </p>
        {scores.length > 0 ? (
          <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
            {scores.join(' / ')}
          </small>
        ) : null}
        {sourceId !== null ? (
          <Button
            aria-label={`View Source ${sourceLabel}`}
            onClick={() => onOpenSource(sourceId, citationSnippet)}
            size="sm"
            type="button"
            variant="secondary"
          >
            View Source
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug" role="status">
            No Openable Source (Deleted Or Uncited)
          </span>
        )}
      </div>
    </DataListItem>
  )
}

function ProviderUsageDetail({ usage }: { usage: ChatHistoryProviderUsage }) {
  return (
    <DataListItem key={usage.provider_usage_id}>
      <strong className="text-sm text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {usage.provider} / {usage.model}
      </strong>
      <p className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {usage.total_tokens ?? 'Unknown'} Tokens
        {usage.estimated_cost_usd === null
          ? ''
          : ` / $${usage.estimated_cost_usd.toFixed(4)}`}
      </p>
      <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {titleCaseToken(usage.status)}
      </small>
    </DataListItem>
  )
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/15 p-3 max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:bg-card max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95">
      <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-foreground max-[680px]:mt-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
        {value}
      </dd>
    </div>
  )
}


function InspectorLoadingSkeleton({
  ariaLabel,
  slot,
}: {
  ariaLabel: string
  slot: string
}) {
  return (
    <div
      aria-busy="true"
      aria-label={ariaLabel}
      className="grid w-full gap-2 max-[680px]:gap-0.5"
      data-slot={slot}
      role="status"
    >
      <span className="sr-only">{ariaLabel}…</span>
      <div aria-hidden="true" className="h-3 w-1/3 motion-safe:animate-pulse rounded bg-muted/25" />
      <div aria-hidden="true" className="h-3 w-full motion-safe:animate-pulse rounded bg-muted/35" />
      <div aria-hidden="true" className="h-3 w-11/12 motion-safe:animate-pulse rounded bg-muted/30" />
      <div aria-hidden="true" className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted/25" />
    </div>
  )
}

function sessionHasTraining(session: ChatSessionSummary): boolean {
  return session.has_pending_training || session.has_approved_training
}

const MINIMAP_ARIA_MAX_CHARS = 96

function minimapMessageLabel(role: string, content: string): string {
  const trimmed = content.trim()
  if (trimmed.length <= MINIMAP_ARIA_MAX_CHARS) {
    return `${role}: ${trimmed}`
  }
  return `${role}: ${trimmed.slice(0, MINIMAP_ARIA_MAX_CHARS - 1)}…`
}

function sessionDisplayTitle(session: ChatSessionSummary): string {
  const title = session.title?.trim()
  if (title !== undefined && title.length > 0) {
    return title
  }
  return shortSessionId(session.session_id)
}

function sessionEmptyCopy(filter: SessionNavigationFilter): string {
  if (filter === 'training') {
    return 'Aún no hay entrenamiento.'
  }
  if (filter === 'archived') {
    return 'Aún no hay conversaciones archivadas.'
  }
  return 'Aún no hay conversaciones.'
}

async function copyTextToClipboard(text: string): Promise<boolean> {
  if (
    typeof navigator !== 'undefined' &&
    navigator.clipboard !== undefined &&
    typeof navigator.clipboard.writeText === 'function'
  ) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Fall through to execCommand path.
    }
  }

  if (typeof document === 'undefined') {
    return false
  }

  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}

/** Prefer last update (activity) over created_at — matches beflow "hace X". */
function sessionLastActivityAt(session: ChatSessionSummary): string {
  const updated = session.updated_at?.trim()
  if (updated !== undefined && updated.length > 0) {
    return updated
  }
  return session.created_at
}

function sessionAgeTooltip(session: ChatSessionSummary): string {
  const iso = sessionLastActivityAt(session)
  const parsed = new Date(iso)
  if (!Number.isFinite(parsed.getTime())) {
    return 'Última actividad desconocida'
  }
  return `Última actividad: ${parsed.toLocaleString()}`
}

function formatSourceTimestamp(iso: string): string {
  const parsed = new Date(iso)
  if (!Number.isFinite(parsed.getTime())) {
    return iso
  }
  return parsed.toLocaleString()
}

function formatRelativeSessionAge(iso: string): string {
  const at = new Date(iso).getTime()
  if (!Number.isFinite(at)) {
    return ''
  }
  const diffMs = Math.max(0, Date.now() - at)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < minute) {
    return 'ahora'
  }
  if (diffMs < hour) {
    return `${Math.max(1, Math.floor(diffMs / minute))}m`
  }
  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)}h`
  }
  return `${Math.floor(diffMs / day)}d`
}

function shortSessionId(sessionId: string): string {
  if (sessionId.length <= 12) {
    return sessionId
  }
  return sessionId.slice(0, 8)
}

function countInternalSteps(detail: ChatSessionDetailResponse | null): number {
  if (detail === null) {
    return 0
  }
  return (
    detail.tool_calls.length +
    detail.retrieval_runs.length +
    detail.provider_usage.length
  )
}

function messageElementId(messageId: string): string {
  return `chat-message-${messageId}`
}

function titleCaseToken(value: string | null | undefined): string {
  if (value == null || value.trim().length === 0) {
    return '—'
  }
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function sessionStatusLabel(status: string | null | undefined): string {
  if (status === null || status === undefined || status === '') {
    return 'Empty'
  }
  if (status === 'failed') {
    return 'Failed'
  }
  if (status === 'succeeded') {
    return 'Succeeded'
  }
  if (status === 'running') {
    return 'Running'
  }
  if (status === 'loading') {
    return 'Loading'
  }
  if (status === 'canceled' || status === 'cancelled') {
    return 'Canceled'
  }
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function sessionStatusTone(
  status: string | null | undefined,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (status === 'failed') {
    return 'danger'
  }
  if (status === 'succeeded') {
    return 'success'
  }
  if (status === 'running' || status === 'loading') {
    return 'warning'
  }
  return 'neutral'
}

function formatStepperScores(chunk: ChatHistoryRetrievedChunk): string {
  const scores = [
    formatOptionalScore('Dense Score', chunk.dense_score),
    formatOptionalScore('Lexical Score', chunk.lexical_score),
    formatOptionalScore('RRF Score', chunk.rrf_score),
    formatOptionalScore('Rerank Score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  return scores.length > 0 ? scores.join(' / ') : 'Unknown Score'
}

function formatSessionCost(usages: ChatHistoryProviderUsage[]): string {
  const knownCosts = usages
    .map((usage) => usage.estimated_cost_usd)
    .filter((value): value is number => value !== null)
  if (knownCosts.length === 0) {
    return 'Unknown Cost'
  }
  return formatUsd(knownCosts.reduce((total, value) => total + value, 0))
}

function formatSessionTokens(usages: ChatHistoryProviderUsage[]): string {
  const knownTokens = usages
    .map((usage) => usage.total_tokens)
    .filter((value): value is number => value !== null)
  if (knownTokens.length === 0) {
    return 'Unknown Tokens'
  }
  return `${formatNumber(knownTokens.reduce((total, value) => total + value, 0))} Tokens`
}

function formatSessionLatency(usages: ChatHistoryProviderUsage[]): string {
  const knownLatencies = usages
    .map((usage) => usage.latency_ms)
    .filter((value): value is number => value !== null)
  if (knownLatencies.length === 0) {
    return 'Unknown Latency'
  }
  const average =
    knownLatencies.reduce((total, value) => total + value, 0) /
    knownLatencies.length
  return `${Math.round(average)} ms`
}

function retrievalStrategyLabel(run: ChatHistoryRetrievalRun): string {
  if (run.strategy === 'dense' && !run.used_rerank) {
    return 'Default Dense Retrieval'
  }
  return run.used_rerank
    ? `${titleCaseToken(run.strategy)} With Rerank`
    : `${titleCaseToken(run.strategy)} Retrieval`
}

function sourceViewerStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Loading'
  }
  if (state === 'failed') {
    return 'Unavailable'
  }
  if (state === 'succeeded') {
    return 'Loaded'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Idle'
}

function sourceViewerTone(state: RequestState): 'danger' | 'neutral' | 'success' {
  if (state === 'failed') {
    return 'danger'
  }
  if (state === 'succeeded') {
    return 'success'
  }
  return 'neutral'
}

function formatOptionalScore(
  label: string,
  score: number | null,
): string | null {
  return score === null ? null : `${label} ${formatScore(score)}`
}

function formatScore(score: number): string {
  return score.toFixed(2)
}

function formatJsonValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'None'
  }
  if (typeof value === 'string') {
    return value
  }
  return JSON.stringify(value)
}

function getCitationText(value: unknown, key: string): string {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return 'No Citation Text Stored.'
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return typeof nextValue === 'string' && nextValue.length > 0
    ? nextValue
    : 'No Citation Text Stored.'
}

function getJsonString(value: unknown, key: string): string | null {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return null
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return typeof nextValue === 'string' && nextValue.length > 0
    ? nextValue
    : null
}

function formatUnknownCost(value: number | null): string {
  return value === null ? 'Unknown Cost' : formatUsd(value)
}

function formatUnknownTokens(value: number | null): string {
  return value === null ? 'Unknown Tokens' : `${formatNumber(value)} Tokens`
}

function formatUnknownMs(value: number | null): string {
  return value === null ? 'Unknown Latency' : `${value} ms`
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}
