import {
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button, IconButton } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { DataList, DataListItem } from '@/components/ui/data-list'
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
import type {
  ChatHistoryProviderUsage,
  ChatHistoryRetrievedChunk,
  ChatHistoryRetrievalRun,
  ChatHistoryToolCall,
  ChatSessionDetailResponse,
  ChatSessionSummary,
  Source,
} from '@/lib/apiClient'

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

const SESSION_FILTERS: { label: string; value: SessionNavigationFilter }[] = [
  { label: 'ACTIVOS', value: 'active' },
  { label: 'TRAIN', value: 'training' },
  { label: 'ARCHIVADOS', value: 'archived' },
]
const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')

export function SessionNavigationPanel({
  canLoadMore,
  statusFilter,
  error,
  onArchiveSession,
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
  const renameInputRef = useRef<HTMLInputElement | null>(null)
  const isLoading = state === 'loading'

  useEffect(() => {
    if (renamingSessionId !== null) {
      renameInputRef.current?.focus()
      renameInputRef.current?.select()
    }
  }, [renamingSessionId])

  return (
    <Panel
      aria-labelledby="history-title"
      className="grid gap-3 p-3"
      role="complementary"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="history-title" className="text-sm font-semibold text-foreground">
          Sesiones
        </h2>
        <Button onClick={onStartNewSession} size="sm" type="button">
          <PlusIcon />
          nuevo chat
        </Button>
      </div>

      <SegmentedControl
        aria-label="Session filters"
        className="max-w-full flex-wrap justify-start"
      >
        {SESSION_FILTERS.map((filter) => (
          <SegmentedControlItem
            active={statusFilter === filter.value}
            key={filter.value}
            onClick={() => onStatusFilterChange(filter.value)}
          >
            {filter.label}
          </SegmentedControlItem>
        ))}
      </SegmentedControl>

      {error ? <InlineFeedback role="status" tone="danger">{error}</InlineFeedback> : null}

      <DataList aria-label="Project sessions">
        {isLoading && sessions.length === 0 ? (
          <DataListItem>
            <span className="text-sm text-muted-foreground">Cargando...</span>
          </DataListItem>
        ) : sessions.length === 0 ? (
          <DataListItem>
            <span className="text-sm text-muted-foreground">
              {sessionEmptyCopy(statusFilter)}
            </span>
          </DataListItem>
        ) : (
          sessions.map((session) => {
            const title = sessionDisplayTitle(session)
            const isSelected = session.session_id === selectedSessionId
            const isArchived = session.archived_at !== null
            const hasTraining = sessionHasTraining(session)
            const isRenaming = renamingSessionId === session.session_id
            return (
              <DataListItem
                className={
                  isSelected
                    ? 'border-primary bg-primary/5'
                    : 'hover:border-border/80'
                }
                data-selected={isSelected ? '' : undefined}
                key={session.session_id}
              >
                <div className="grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-2">
                  <span
                    aria-hidden={!hasTraining}
                    className="text-primary"
                    title={hasTraining ? 'Training' : undefined}
                  >
                    {hasTraining ? (
                      <BrainIcon approved={session.has_approved_training} />
                    ) : null}
                  </span>
                  {isRenaming ? (
                    <form
                      onSubmit={(event) => {
                        event.preventDefault()
                        const trimmedTitle = renameDraft.trim()
                        if (trimmedTitle.length === 0) {
                          return
                        }
                        onRenameSession(session.session_id, trimmedTitle)
                        setRenamingSessionId(null)
                        setRenameDraft('')
                      }}
                    >
                      <Input
                        aria-label="Nuevo nombre de sesiÃ³n"
                        maxLength={60}
                        onChange={(event) => setRenameDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Escape') {
                            setRenamingSessionId(null)
                            setRenameDraft('')
                          }
                        }}
                        ref={renameInputRef}
                        value={renameDraft}
                      />
                    </form>
                  ) : (
                    <Button
                      aria-label={`Abrir sesiÃ³n ${title}`}
                      className="min-w-0 justify-start px-2"
                      onClick={() => onSelectSession(session.session_id)}
                      title={title}
                      type="button"
                      variant="ghost"
                    >
                      <span className="truncate">{title}</span>
                    </Button>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeSessionAge(session.created_at)}
                  </span>
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <IconButton label={`Opciones de ${title}`} variant="ghost">
                        <MoreVerticalIcon />
                      </IconButton>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Portal>
                      <DropdownMenu.Content
                        align="end"
                        className="z-20 grid min-w-36 gap-1 rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md"
                        data-slot="session-actions-menu"
                        onCloseAutoFocus={(event) => event.preventDefault()}
                        sideOffset={4}
                      >
                        <DropdownMenu.Item
                          className="flex min-h-8 cursor-pointer items-center rounded-sm px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                          onClick={() => {
                            setRenamingSessionId(session.session_id)
                            setRenameDraft(title)
                          }}
                        >
                          renombrar
                        </DropdownMenu.Item>
                        <DropdownMenu.Item
                          className="flex min-h-8 cursor-pointer items-center rounded-sm px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
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
                      </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                  </DropdownMenu.Root>
                </div>
              </DataListItem>
            )
          })
        )}
      </DataList>
      {canLoadMore ? (
        <Button
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
          variant="secondary"
        >
          {isLoading ? 'cargando...' : 'ver mÃ¡s'}
        </Button>
      ) : null}
    </Panel>
  )
}

export function WorkspaceInspectorPanel({
  activeTab,
  detail,
  detailError,
  detailState,
  layout,
  onActiveTabChange,
  onClose,
  onNavigateMessage,
  onOpenSource,
  sourceViewer,
}: {
  activeTab: InspectorTab
  detail: ChatSessionDetailResponse | null
  detailError: string | null
  detailState: RequestState
  layout: 'inline' | 'overlay'
  onActiveTabChange(tab: InspectorTab): void
  onClose(): void
  onNavigateMessage(messageId: string): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  sourceViewer: SourceViewerState
}) {
  return (
    <Panel
      aria-label="Workspace inspector"
      className={
        layout === 'inline'
          ? 'workspace-inspector-inline grid min-h-0 gap-3 p-3'
          : 'workspace-inspector-overlay fixed inset-y-0 right-0 z-40 grid w-[min(420px,calc(100vw-24px))] min-h-0 gap-3 rounded-none border-y-0 border-r-0 p-3 shadow-xl'
      }
      role="complementary"
    >
      <div className="flex items-center justify-between gap-2">
        <SegmentedControl
          aria-label="Inspector panels"
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
        <IconButton label="Close right sidebar" onClick={onClose} variant="ghost">
          <XIcon />
        </IconButton>
      </div>

      {activeTab === 'context' ? (
        <div
          aria-labelledby="context-tab"
          className="grid min-h-0 gap-4 overflow-y-auto"
          id="context-panel"
          role="tabpanel"
        >
          <SourceViewerPanel viewer={sourceViewer} />
          <SessionContextPanel detail={detail} />
          <InternalActionStepper detail={detail} />
          <SessionDetailPanel
            detail={detail}
            error={detailError}
            onOpenSource={onOpenSource}
            state={detailState}
          />
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
    <Panel aria-label="Source viewer" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4">
        <PanelTitle>Source viewer</PanelTitle>
        <StatusBadge tone={sourceViewerTone(viewer.state)}>
          {sourceViewerStatusLabel(viewer.state)}
        </StatusBadge>
      </PanelHeader>
      <PanelBody className="grid gap-3 p-4 pt-0">
        {viewer.state === 'loading' ? (
          <EmptyState>Loading source {viewer.sourceId}...</EmptyState>
        ) : null}

        {viewer.error ? (
          <InlineFeedback role="alert" tone="danger">
            {viewer.error}
          </InlineFeedback>
        ) : null}

        {viewer.citationSnippet === null ? null : (
          <section className="grid gap-1">
            <h4 className="text-sm font-semibold text-foreground">
              Citation snippet
            </h4>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {viewer.citationSnippet}
            </p>
          </section>
        )}

        {viewer.source ? (
          <div className="grid gap-3">
            <p className="break-all text-xs text-muted-foreground">
              {viewer.source.external_id}
            </p>
            <dl className="grid gap-2">
              <MetadataItem label="ID" value={viewer.source.id} />
              <MetadataItem label="Type" value={viewer.source.source_type} />
              <MetadataItem label="Created" value={viewer.source.created_at} />
              <MetadataItem label="Updated" value={viewer.source.updated_at} />
            </dl>

            <section className="grid gap-2">
              <h4 className="text-sm font-semibold text-foreground">Tags</h4>
              {viewer.source.tags === null || viewer.source.tags.length === 0 ? (
                <EmptyState>No tags stored.</EmptyState>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {viewer.source.tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
              )}
            </section>

            <section className="grid gap-2">
              <h4 className="text-sm font-semibold text-foreground">Metadata</h4>
              {viewer.source.extra_metadata === null ||
              Object.keys(viewer.source.extra_metadata).length === 0 ? (
                <EmptyState>No metadata stored.</EmptyState>
              ) : (
                <dl className="grid gap-2">
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
}: {
  detail: ChatSessionDetailResponse | null
  onNavigateMessage(messageId: string): void
}) {
  return (
    <Panel aria-label="Conversation minimap" role="navigation">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4">
        <PanelTitle>Minimap</PanelTitle>
        <StatusBadge>{detail?.messages.length ?? 0} turns</StatusBadge>
      </PanelHeader>
      <PanelBody className="p-4 pt-0">
        {detail === null || detail.messages.length === 0 ? (
          <EmptyState>Select a session to navigate messages.</EmptyState>
        ) : (
          <DataList aria-label="Conversation messages">
            {detail.messages.map((message) => (
              <DataListItem key={message.message_id}>
                <Button
                  aria-label={`${message.role}: ${message.content}`}
                  className="h-auto w-full justify-start whitespace-normal px-2 py-2 text-left"
                  onClick={() => onNavigateMessage(message.message_id)}
                  type="button"
                  variant="ghost"
                >
                  <span className="grid min-w-0 gap-1">
                    <strong className="text-sm text-foreground">{message.role}</strong>
                    <span className="line-clamp-2 text-sm text-muted-foreground">
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
}: {
  detail: ChatSessionDetailResponse | null
}) {
  const firstUsage = detail?.provider_usage[0] ?? null

  return (
    <Panel aria-label="Session context" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4">
        <PanelTitle>Session context</PanelTitle>
        <StatusBadge>{detail?.session.status ?? 'empty'}</StatusBadge>
      </PanelHeader>
      <PanelBody className="p-4 pt-0">
        {detail === null ? (
          <EmptyState>
            Select a session to inspect model, prompt and usage context.
          </EmptyState>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricCard
              detail={detail.session.session_id}
              label="Prompt"
              value={`prompt ${detail.session.prompt_version ?? 'unknown'}`}
            />
            <MetricCard
              detail={
                firstUsage === null
                  ? 'unknown provider'
                  : `${firstUsage.provider} ${firstUsage.operation} ${firstUsage.status}`
              }
              label="Model"
              value={firstUsage?.model ?? 'unknown model'}
            />
            <MetricCard
              detail={`${detail.provider_usage.length} provider records`}
              label="Cost"
              value={formatSessionCost(detail.provider_usage)}
            />
            <MetricCard
              detail="Known usage only"
              label="Tokens"
              value={formatSessionTokens(detail.provider_usage)}
            />
            <MetricCard
              detail="Average known latency"
              label="Latency"
              value={formatSessionLatency(detail.provider_usage)}
            />
          </div>
        )}
      </PanelBody>
    </Panel>
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
  return (
    <article className="grid min-h-28 gap-2 rounded-md border border-border bg-card p-4 text-card-foreground">
      <span className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </span>
      <strong className="break-words text-xl font-semibold leading-none">
        {value}
      </strong>
      <small className="text-sm leading-relaxed text-muted-foreground">
        {detail}
      </small>
    </article>
  )
}

function InternalActionStepper({
  detail,
}: {
  detail: ChatSessionDetailResponse | null
}) {
  return (
    <Panel aria-label="Internal action stepper" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4">
        <PanelTitle>Action stepper</PanelTitle>
        <StatusBadge>{countInternalSteps(detail)} steps</StatusBadge>
      </PanelHeader>
      <PanelBody className="p-4 pt-0">
        {detail === null || countInternalSteps(detail) === 0 ? (
          <EmptyState>No stored internal actions for this session.</EmptyState>
        ) : (
          <DataList>
            {detail.tool_calls.map((call) => (
              <DataListItem className="grid gap-1" key={`tool-${call.tool_call_id}`}>
                <Badge>tool call {call.status}</Badge>
                <strong className="text-sm text-foreground">{call.tool_name}</strong>
                <p className="text-sm text-muted-foreground">
                  {formatJsonValue(call.arguments)}
                </p>
                <small className="text-xs text-muted-foreground">
                  {formatUnknownMs(call.latency_ms)}
                </small>
              </DataListItem>
            ))}
            {detail.retrieval_runs.map((run) => (
              <DataListItem
                className="grid gap-2"
                key={`retrieval-${run.retrieval_run_id}`}
              >
                <Badge>retrieval {run.strategy}</Badge>
                <strong className="text-sm text-foreground">{run.query}</strong>
                <p className="text-sm text-muted-foreground">
                  top {run.top_k} / {formatUnknownMs(run.latency_ms)}
                </p>
                <DataList>
                  {run.retrieved_chunks.map((chunk) => (
                    <DataListItem key={chunk.retrieved_chunk_id}>
                      <strong className="text-sm text-foreground">
                        rank {chunk.rank}
                      </strong>
                      <small className="block text-xs text-muted-foreground">
                        {formatStepperScores(chunk)}
                      </small>
                    </DataListItem>
                  ))}
                </DataList>
              </DataListItem>
            ))}
            {detail.provider_usage.map((usage) => (
              <DataListItem
                className="grid gap-1"
                key={`provider-${usage.provider_usage_id}`}
              >
                <Badge>provider usage {usage.status}</Badge>
                <strong className="text-sm text-foreground">{usage.model}</strong>
                <p className="text-sm text-muted-foreground">
                  {usage.provider} {usage.operation} /{' '}
                  {formatUnknownTokens(usage.total_tokens)} /{' '}
                  {formatUnknownCost(usage.estimated_cost_usd)}
                </p>
                <small className="text-xs text-muted-foreground">
                  {formatUnknownMs(usage.latency_ms)}
                </small>
              </DataListItem>
            ))}
          </DataList>
        )}
      </PanelBody>
    </Panel>
  )
}

function SessionDetailPanel({
  detail,
  error,
  onOpenSource,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  error: string | null
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  state: RequestState
}) {
  if (state === 'loading') {
    return (
      <Panel aria-live="polite" role="region">
        <PanelHeader className="p-4">
          <PanelTitle>Session detail</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-4 pt-0">
          <EmptyState>Loading session detail...</EmptyState>
        </PanelBody>
      </Panel>
    )
  }

  if (error) {
    return (
      <Panel role="region">
        <PanelHeader className="p-4">
          <PanelTitle>Session detail</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-4 pt-0">
          <InlineFeedback role="status" tone="danger">
            {error}
          </InlineFeedback>
        </PanelBody>
      </Panel>
    )
  }

  if (detail === null) {
    return (
      <Panel role="region">
        <PanelHeader className="p-4">
          <PanelTitle>Session detail</PanelTitle>
        </PanelHeader>
        <PanelBody className="p-4 pt-0">
          <EmptyState>Select a session to inspect stored history.</EmptyState>
        </PanelBody>
      </Panel>
    )
  }

  return (
    <Panel aria-label="Selected session detail" role="region">
      <PanelHeader className="flex-row items-start justify-between gap-2 p-4">
        <div className="grid min-w-0 gap-1">
          <PanelTitle>Session detail</PanelTitle>
          <p className="break-all text-xs text-muted-foreground">
            {detail.session.session_id}
          </p>
        </div>
        <StatusBadge>{detail.session.status}</StatusBadge>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0">
        <section className="grid gap-2" aria-labelledby="messages-title">
          <h4 id="messages-title" className="text-sm font-semibold text-foreground">
            Messages
          </h4>
          <DataList aria-label="Session messages">
            {detail.messages.map((message) => (
              <DataListItem key={message.message_id}>
                <article
                  aria-label={`${message.role} message`}
                  className="grid gap-1"
                  id={messageElementId(message.message_id)}
                  tabIndex={-1}
                >
                  <strong className="text-sm text-foreground">{message.role}</strong>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {message.content}
                  </p>
                </article>
              </DataListItem>
            ))}
          </DataList>
        </section>

        <DetailSection id="history-tools-title" title="Tool calls">
          <CompactStateList
            emptyLabel="No stored tool calls."
            items={detail.tool_calls}
            renderItem={(call) => (
              <ToolCallDetail call={call} key={call.tool_call_id} />
            )}
          />
        </DetailSection>

        <DetailSection id="retrieval-runs-title" title="Retrieval runs">
          <CompactStateList
            emptyLabel="No stored retrieval runs."
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

        <DetailSection id="provider-usage-title" title="Provider usage">
          <CompactStateList
            emptyLabel="No provider usage stored."
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
    <section className="grid gap-2" aria-labelledby={id}>
      <h4 id={id} className="text-sm font-semibold text-foreground">
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
      <strong className="text-sm text-foreground">{call.tool_name}</strong>
      <p className="text-sm text-muted-foreground">
        {formatJsonValue(call.arguments)}
      </p>
      <small className="text-xs text-muted-foreground">{call.status}</small>
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
    <DataListItem className="grid gap-2" key={run.retrieval_run_id}>
      <strong className="text-sm text-foreground">{run.query}</strong>
      <div className="flex flex-wrap gap-2">
        <Badge>{retrievalStrategyLabel(run)}</Badge>
        <Badge>top {run.top_k}</Badge>
        {run.latency_ms === null ? null : <Badge>latency {run.latency_ms} ms</Badge>}
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
    formatOptionalScore('dense score', chunk.dense_score),
    formatOptionalScore('lexical score', chunk.lexical_score),
    formatOptionalScore('rrf score', chunk.rrf_score),
    formatOptionalScore('rerank score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  const sourceId = getJsonString(chunk.citation, 'source_id')
  const citationSnippet = getJsonString(chunk.citation, 'snippet')
  const sourceLabel =
    getJsonString(chunk.citation, 'source_external_id') ?? sourceId

  return (
    <DataListItem className="grid gap-2">
      <Badge>rank {chunk.rank}</Badge>
      <div className="grid gap-2">
        <p className="text-sm text-muted-foreground">
          {getCitationText(chunk.citation, 'snippet')}
        </p>
        {scores.length > 0 ? (
          <small className="text-xs text-muted-foreground">
            {scores.join(' / ')}
          </small>
        ) : null}
        {sourceId !== null ? (
          <Button
            aria-label={`View source ${sourceLabel}`}
            onClick={() => onOpenSource(sourceId, citationSnippet)}
            size="sm"
            type="button"
            variant="secondary"
          >
            View source
          </Button>
        ) : null}
      </div>
    </DataListItem>
  )
}

function ProviderUsageDetail({ usage }: { usage: ChatHistoryProviderUsage }) {
  return (
    <DataListItem key={usage.provider_usage_id}>
      <strong className="text-sm text-foreground">
        {usage.provider} / {usage.model}
      </strong>
      <p className="text-sm text-muted-foreground">
        {usage.total_tokens ?? 'unknown'} tokens
        {usage.estimated_cost_usd === null
          ? ''
          : ` / $${usage.estimated_cost_usd.toFixed(4)}`}
      </p>
      <small className="text-xs text-muted-foreground">{usage.status}</small>
    </DataListItem>
  )
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3">
      <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-foreground">{value}</dd>
    </div>
  )
}

function sessionHasTraining(session: ChatSessionSummary): boolean {
  return session.has_pending_training || session.has_approved_training
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
    return 'Sin sesiones con entrenamiento.'
  }
  if (filter === 'archived') {
    return 'Sin sesiones archivadas.'
  }
  return 'Sin sesiones activas.'
}

function formatRelativeSessionAge(iso: string): string {
  const createdAt = new Date(iso).getTime()
  if (!Number.isFinite(createdAt)) {
    return ''
  }
  const diffMs = Math.max(0, Date.now() - createdAt)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < hour) {
    return `${Math.max(1, Math.floor(diffMs / minute))}m`
  }
  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)}hr`
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

function formatStepperScores(chunk: ChatHistoryRetrievedChunk): string {
  const scores = [
    formatOptionalScore('dense score', chunk.dense_score),
    formatOptionalScore('lexical score', chunk.lexical_score),
    formatOptionalScore('rrf score', chunk.rrf_score),
    formatOptionalScore('rerank score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  return scores.length > 0 ? scores.join(' / ') : 'unknown score'
}

function formatSessionCost(usages: ChatHistoryProviderUsage[]): string {
  const knownCosts = usages
    .map((usage) => usage.estimated_cost_usd)
    .filter((value): value is number => value !== null)
  if (knownCosts.length === 0) {
    return 'unknown cost'
  }
  return formatUsd(knownCosts.reduce((total, value) => total + value, 0))
}

function formatSessionTokens(usages: ChatHistoryProviderUsage[]): string {
  const knownTokens = usages
    .map((usage) => usage.total_tokens)
    .filter((value): value is number => value !== null)
  if (knownTokens.length === 0) {
    return 'unknown tokens'
  }
  return `${formatNumber(knownTokens.reduce((total, value) => total + value, 0))} tokens`
}

function formatSessionLatency(usages: ChatHistoryProviderUsage[]): string {
  const knownLatencies = usages
    .map((usage) => usage.latency_ms)
    .filter((value): value is number => value !== null)
  if (knownLatencies.length === 0) {
    return 'unknown latency'
  }
  const average =
    knownLatencies.reduce((total, value) => total + value, 0) /
    knownLatencies.length
  return `${Math.round(average)} ms`
}

function retrievalStrategyLabel(run: ChatHistoryRetrievalRun): string {
  if (run.strategy === 'dense' && !run.used_rerank) {
    return 'default dense retrieval'
  }
  return run.used_rerank ? `${run.strategy} with rerank` : `${run.strategy} retrieval`
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

function formatOptionalScore(label: string, score: number | null): string | null {
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
    return 'No citation text stored.'
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return typeof nextValue === 'string' && nextValue.length > 0
    ? nextValue
    : 'No citation text stored.'
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
  return value === null ? 'unknown cost' : formatUsd(value)
}

function formatUnknownTokens(value: number | null): string {
  return value === null ? 'unknown tokens' : `${formatNumber(value)} tokens`
}

function formatUnknownMs(value: number | null): string {
  return value === null ? 'unknown latency' : `${value} ms`
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}

function XIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function MoreVerticalIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M12 5h.01M12 12h.01M12 19h.01" />
    </svg>
  )
}

function BrainIcon({ approved }: { approved: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={approved ? 'ui-icon brain-icon brain-icon-approved' : 'ui-icon brain-icon'}
      focusable="false"
      viewBox="0 0 24 24"
    >
      <path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v.2A3.2 3.2 0 0 0 4 11.2c0 1.2.7 2.3 1.7 2.8A3.8 3.8 0 0 0 9.5 19H11V5.7a3.4 3.4 0 0 0-1.5-1.2Z" />
      <path d="M14.5 4.5A3.5 3.5 0 0 1 18 8v.2a3.2 3.2 0 0 1 2 3c0 1.2-.7 2.3-1.7 2.8a3.8 3.8 0 0 1-3.8 5H13V5.7a3.4 3.4 0 0 1 1.5-1.2Z" />
      <path d="M8 10h3M13 10h3M8.5 14H11M13 14h2.5" />
    </svg>
  )
}
