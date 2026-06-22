import { type FormEvent, type ReactNode, useMemo, useState } from 'react'
import './App.css'
import {
  ApiClientError,
  createApiClient,
  type ApiClient,
  type ChatObservabilityProviderUsageGroup,
  type ChatObservabilitySummary,
  type ChatHistoryProviderUsage,
  type ChatHistoryRetrievedChunk,
  type ChatHistoryRetrievalRun,
  type ChatHistoryToolCall,
  type ChatResponseBody,
  type ChatSessionDetailResponse,
  type ChatSessionSummary,
  type ChatToolCall,
} from './lib/apiClient'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_RETRIEVAL_LIMIT = 5
const HISTORY_LIMIT = 5
const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')
const STATUS_ORDER = ['failed', 'running', 'succeeded']

type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
type ActiveView = 'chat' | 'observability'

type AppProps = {
  apiClient?: ApiClient
  initialProjectId?: string
}

function App({ apiClient, initialProjectId = '' }: AppProps) {
  const client = useMemo(
    () =>
      apiClient ??
      createApiClient({
        baseUrl: getDefaultApiBaseUrl(),
      }),
    [apiClient],
  )
  const [projectId, setProjectId] = useState(initialProjectId)
  const [question, setQuestion] = useState('')
  const [retrievalLimit, setRetrievalLimit] = useState(DEFAULT_RETRIEVAL_LIMIT)
  const [response, setResponse] = useState<ChatResponseBody | null>(null)
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [sessionDetail, setSessionDetail] =
    useState<ChatSessionDetailResponse | null>(null)
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [historyState, setHistoryState] = useState<RequestState>('idle')
  const [detailState, setDetailState] = useState<RequestState>('idle')
  const [requestError, setRequestError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [activeRequestController, setActiveRequestController] =
    useState<AbortController | null>(null)
  const [activeView, setActiveView] = useState<ActiveView>('chat')
  const [createdAtFrom, setCreatedAtFrom] = useState('')
  const [createdAtTo, setCreatedAtTo] = useState('')
  const [observabilityStatus, setObservabilityStatus] = useState('')
  const [observabilitySummary, setObservabilitySummary] =
    useState<ChatObservabilitySummary | null>(null)
  const [observabilityState, setObservabilityState] =
    useState<RequestState>('idle')
  const [observabilityError, setObservabilityError] = useState<string | null>(
    null,
  )

  const isAsking = requestState === 'loading'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedProjectId = projectId.trim()
    const trimmedQuestion = question.trim()

    if (trimmedProjectId.length === 0 || trimmedQuestion.length === 0) {
      setRequestState('failed')
      setRequestError('Project ID and question are required.')
      return
    }

    setRequestState('loading')
    setRequestError(null)
    setHistoryError(null)
    setResponse(null)

    const requestBody = {
      message: trimmedQuestion,
      retrieval_limit: retrievalLimit,
    }
    const controller = new AbortController()
    let streamOpened = false
    const markStreamOpened = () => {
      streamOpened = true
    }
    setActiveRequestController(controller)
    try {
      const nextResponse = await client.askChatStream(
        trimmedProjectId,
        requestBody,
        {
          onAnswerDelta: (text) => {
            markStreamOpened()
            setResponse((current) => appendAnswerDelta(current, text))
          },
          onEvent: markStreamOpened,
          onSessionStarted: (sessionId) => {
            markStreamOpened()
            setResponse((current) => setResponseSessionId(current, sessionId))
          },
          onToolCall: (toolCall) => {
            markStreamOpened()
            setResponse((current) => appendToolCall(current, toolCall))
          },
        },
        { signal: controller.signal },
      )
      setResponse(nextResponse)
      setRequestState('succeeded')
      await handleRefreshHistory(trimmedProjectId)
    } catch (error) {
      if (isAbortError(error)) {
        setRequestState('canceled')
        setRequestError(null)
        return
      }
      if (!streamOpened && shouldFallbackToJsonChat(error)) {
        try {
          const nextResponse = await client.askChat(trimmedProjectId, requestBody)
          setResponse(nextResponse)
          setRequestState('succeeded')
          await handleRefreshHistory(trimmedProjectId)
          return
        } catch (fallbackError) {
          setRequestState('failed')
          setRequestError(getErrorMessage(fallbackError))
          return
        }
      }
      setRequestState('failed')
      setRequestError(getErrorMessage(error))
    } finally {
      setActiveRequestController((current) =>
        current === controller ? null : current,
      )
    }
  }

  function handleCancelRequest() {
    activeRequestController?.abort()
  }

  async function handleRefreshHistory(projectIdOverride?: string) {
    const trimmedProjectId = (projectIdOverride ?? projectId).trim()

    if (trimmedProjectId.length === 0) {
      setHistoryState('failed')
      setHistoryError('Project ID is required to refresh history.')
      return
    }

    setHistoryError(null)
    await refreshHistory(client, trimmedProjectId, {
      onError: setHistoryError,
      onItems: setSessions,
      onState: setHistoryState,
    })
  }

  async function handleSelectSession(sessionId: string) {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setDetailState('failed')
      setDetailError('Project ID is required to load session detail.')
      return
    }

    setSelectedSessionId(sessionId)
    setDetailState('loading')
    setDetailError(null)

    try {
      const detail = await client.getChatSession(trimmedProjectId, sessionId)
      setSessionDetail(detail)
      setDetailState('succeeded')
    } catch (error) {
      setDetailState('failed')
      setDetailError(getErrorMessage(error))
    }
  }

  async function handleRefreshObservability() {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setObservabilityState('failed')
      setObservabilityError('Project ID is required to refresh observability.')
      return
    }

    setObservabilityState('loading')
    setObservabilityError(null)

    try {
      const summary = await client.getChatObservabilitySummary(trimmedProjectId, {
        created_at_from: optionalFilterValue(createdAtFrom),
        created_at_to: optionalFilterValue(createdAtTo),
        status: optionalFilterValue(observabilityStatus),
      })
      setObservabilitySummary(summary)
      setObservabilityState('succeeded')
    } catch (error) {
      setObservabilityState('failed')
      setObservabilityError(getErrorMessage(error))
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace" aria-labelledby="workspace-title">
        <header className="workspace-header">
          <div>
            <h1 id="workspace-title">Adaptive RAG</h1>
            <p className="workspace-subtitle">
              Ask against an existing project and inspect the retrieved context.
            </p>
          </div>
          <div className="workspace-actions">
            <ViewSwitcher activeView={activeView} onChange={setActiveView} />
            <span className="status">Local API</span>
          </div>
        </header>

        {activeView === 'chat' ? (
          <div className="workspace-grid">
            <section className="panel panel-primary" aria-labelledby="chat-title">
              <div className="panel-heading">
                <div>
                  <p className="panel-label">Chat</p>
                  <h2 id="chat-title">Workspace</h2>
                </div>
                <span className={statusClassName(requestState)}>
                  {requestStatusLabel(requestState)}
                </span>
              </div>

              <form className="chat-form" onSubmit={handleSubmit}>
                <label className="field">
                  <span>Project ID</span>
                  <input
                    autoComplete="off"
                    name="project-id"
                    onChange={(event) => setProjectId(event.currentTarget.value)}
                    placeholder="Project UUID"
                    value={projectId}
                  />
                </label>

                <label className="field">
                  <span>Question</span>
                  <textarea
                    name="question"
                    onChange={(event) => setQuestion(event.currentTarget.value)}
                    placeholder="Ask a question about indexed sources"
                    rows={4}
                    value={question}
                  />
                </label>

                <div className="form-actions">
                  <label className="field field-compact">
                    <span>Retrieval limit</span>
                    <input
                      max={20}
                      min={1}
                      name="retrieval-limit"
                      onChange={(event) =>
                        setRetrievalLimit(normalizeLimit(event.currentTarget.value))
                      }
                      type="number"
                      value={retrievalLimit}
                    />
                  </label>
                  <button disabled={isAsking} type="submit">
                    {isAsking ? 'Asking...' : 'Ask'}
                  </button>
                  {isAsking ? (
                    <button
                      className="secondary-button"
                      onClick={handleCancelRequest}
                      type="button"
                    >
                      Cancel
                    </button>
                  ) : null}
                </div>

                {requestError ? (
                  <p className="form-feedback form-feedback-error" role="alert">
                    {requestError}
                  </p>
                ) : null}
              </form>

              <ResponsePanel response={response} state={requestState} />
            </section>

            <HistoryPanel
              detail={sessionDetail}
              detailError={detailError}
              detailState={detailState}
              error={historyError}
              onRefresh={() => void handleRefreshHistory()}
              onSelectSession={(sessionId) => void handleSelectSession(sessionId)}
              selectedSessionId={selectedSessionId}
              sessions={sessions}
              state={historyState}
            />
          </div>
        ) : (
          <ObservabilityPanel
            createdAtFrom={createdAtFrom}
            createdAtTo={createdAtTo}
            error={observabilityError}
            onCreatedAtFromChange={setCreatedAtFrom}
            onCreatedAtToChange={setCreatedAtTo}
            onProjectIdChange={setProjectId}
            onRefresh={() => void handleRefreshObservability()}
            onStatusChange={setObservabilityStatus}
            projectId={projectId}
            state={observabilityState}
            status={observabilityStatus}
            summary={observabilitySummary}
          />
        )}
      </section>
    </main>
  )
}

function ViewSwitcher({
  activeView,
  onChange,
}: {
  activeView: ActiveView
  onChange(view: ActiveView): void
}) {
  return (
    <nav className="view-switcher" aria-label="Workspace views">
      <button
        aria-pressed={activeView === 'chat'}
        className={activeView === 'chat' ? 'view-tab view-tab-active' : 'view-tab'}
        onClick={() => onChange('chat')}
        type="button"
      >
        Chat
      </button>
      <button
        aria-pressed={activeView === 'observability'}
        className={
          activeView === 'observability' ? 'view-tab view-tab-active' : 'view-tab'
        }
        onClick={() => onChange('observability')}
        type="button"
      >
        Observability
      </button>
    </nav>
  )
}

function ObservabilityPanel({
  createdAtFrom,
  createdAtTo,
  error,
  onCreatedAtFromChange,
  onCreatedAtToChange,
  onProjectIdChange,
  onRefresh,
  onStatusChange,
  projectId,
  state,
  status,
  summary,
}: {
  createdAtFrom: string
  createdAtTo: string
  error: string | null
  onCreatedAtFromChange(value: string): void
  onCreatedAtToChange(value: string): void
  onProjectIdChange(value: string): void
  onRefresh(): void
  onStatusChange(value: string): void
  projectId: string
  state: RequestState
  status: string
  summary: ChatObservabilitySummary | null
}) {
  const isRefreshing = state === 'loading'

  return (
    <section className="panel observability-panel" aria-labelledby="observability-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Observability</p>
          <h2 id="observability-title">Dashboard shell</h2>
        </div>
        <span className={statusClassName(state)}>
          {observabilityStatusLabel(state)}
        </span>
      </div>

      <form
        className="observability-filters"
        onSubmit={(event) => {
          event.preventDefault()
          onRefresh()
        }}
      >
        <label className="field">
          <span>Project ID</span>
          <input
            autoComplete="off"
            name="observability-project-id"
            onChange={(event) => onProjectIdChange(event.currentTarget.value)}
            placeholder="Project UUID"
            value={projectId}
          />
        </label>
        <label className="field">
          <span>Created from</span>
          <input
            name="created-at-from"
            onChange={(event) => onCreatedAtFromChange(event.currentTarget.value)}
            placeholder="2026-06-21T00:00:00Z"
            value={createdAtFrom}
          />
        </label>
        <label className="field">
          <span>Created to</span>
          <input
            name="created-at-to"
            onChange={(event) => onCreatedAtToChange(event.currentTarget.value)}
            placeholder="2026-06-22T00:00:00Z"
            value={createdAtTo}
          />
        </label>
        <label className="field">
          <span>Status</span>
          <select
            name="observability-status"
            onChange={(event) => onStatusChange(event.currentTarget.value)}
            value={status}
          >
            <option value="">Any</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <button disabled={isRefreshing} type="submit">
          {isRefreshing ? 'Refreshing...' : 'Refresh summary'}
        </button>
      </form>

      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}

      <ObservabilityMetrics summary={summary} />
    </section>
  )
}

function ObservabilityMetrics({
  summary,
}: {
  summary: ChatObservabilitySummary | null
}) {
  if (summary === null) {
    return (
      <div className="observability-empty">
        <p className="empty-copy">
          No observability summary yet. Enter filters and refresh to inspect chat
          health.
        </p>
      </div>
    )
  }

  const slowestP95 = getSlowestP95Group(summary.provider_usage.groups)
  const errorCount =
    summary.errors.session_error_count + summary.errors.provider_error_count

  return (
    <>
      <div className="metric-grid" aria-label="Chat observability metrics">
        <MetricCard
          label="Sessions"
          value={String(summary.sessions.total)}
          detail="Filtered chat sessions"
        />
        <MetricCard
          label="Provider calls"
          value={String(summary.provider_usage.total_records)}
          detail={`${summary.provider_usage.missing_cost_count} missing cost`}
        />
        <MetricCard
          label="Estimated cost"
          value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
          detail="Known usage only"
        />
        <MetricCard
          label="Errors"
          value={String(errorCount)}
          detail={`${summary.errors.session_error_count} sessions / ${summary.errors.provider_error_count} providers`}
        />
        <MetricCard
          label="Latency"
          value={
            slowestP95 === null ? 'No p95' : `${slowestP95.latency_ms.p95} ms`
          }
          detail={
            slowestP95 === null
              ? 'No known provider latency'
              : `Slowest p95 ${slowestP95.provider} / ${slowestP95.model}`
          }
        />
      </div>
      <ObservabilityBreakdowns summary={summary} />
    </>
  )
}

function ObservabilityBreakdowns({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <div className="observability-breakdowns">
      <StatusBreakdown summary={summary} />
      <ErrorMessages summary={summary} />
      <ProviderUsageTable summary={summary} />
      <SessionHealth summary={summary} />
    </div>
  )
}

function StatusBreakdown({ summary }: { summary: ChatObservabilitySummary }) {
  const rows = getStatusBreakdown(summary.sessions.by_status)

  return (
    <section
      className="breakdown-card"
      aria-labelledby="status-breakdown-title"
    >
      <BreakdownHeader
        id="status-breakdown-title"
        label={`${summary.sessions.total} total`}
        title="Status breakdown"
      />
      {rows.length === 0 ? (
        <p className="empty-copy">No status data yet.</p>
      ) : (
        <ul className="status-breakdown-list">
          {rows.map((row) => (
            <li key={row.status}>
              <div>
                <strong>{row.status}</strong>
                <small>{formatPercent(row.count, summary.sessions.total)}</small>
              </div>
              <span>{formatCount(row.count, 'session')}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function ErrorMessages({ summary }: { summary: ChatObservabilitySummary }) {
  return (
    <section className="breakdown-card" aria-labelledby="error-messages-title">
      <BreakdownHeader
        id="error-messages-title"
        label={`${summary.errors.top_messages.length} messages`}
        title="Error messages"
      />
      {summary.errors.top_messages.length === 0 ? (
        <p className="empty-copy">No error messages yet.</p>
      ) : (
        <ul className="compact-list">
          {summary.errors.top_messages.map((error) => (
            <li key={error.message}>
              <strong>{error.message}</strong>
              <span>{formatCount(error.count, 'occurrence')}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function ProviderUsageTable({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <section
      className="breakdown-card breakdown-card-wide"
      aria-labelledby="provider-usage-title"
    >
      <BreakdownHeader
        id="provider-usage-title"
        label={`${summary.provider_usage.groups.length} groups`}
        title="Provider usage"
      />
      {summary.provider_usage.groups.length === 0 ? (
        <p className="empty-copy">No provider usage groups yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="observability-table">
            <thead>
              <tr>
                <th scope="col">Operation</th>
                <th scope="col">Provider</th>
                <th scope="col">Model</th>
                <th scope="col">Calls</th>
                <th scope="col">Tokens</th>
                <th scope="col">Cost</th>
                <th scope="col">P95</th>
              </tr>
            </thead>
            <tbody>
              {summary.provider_usage.groups.map((group) => (
                <tr key={`${group.operation}-${group.provider}-${group.model}`}>
                  <td>{group.operation}</td>
                  <td>{group.provider}</td>
                  <td>{group.model}</td>
                  <td>{formatNumber(group.record_count)}</td>
                  <td>{formatNullableNumber(group.total_tokens)}</td>
                  <td>{formatNullableUsd(group.estimated_cost_usd)}</td>
                  <td>{formatNullableMs(group.latency_ms.p95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function SessionHealth({ summary }: { summary: ChatObservabilitySummary }) {
  const total = summary.sessions.total
  const succeeded = summary.sessions.by_status.succeeded ?? 0
  const failed = summary.sessions.by_status.failed ?? 0
  const running = summary.sessions.by_status.running ?? 0

  return (
    <section className="breakdown-card" aria-labelledby="session-health-title">
      <BreakdownHeader
        id="session-health-title"
        label="Current filter"
        title="Session health"
      />
      {total === 0 ? (
        <p className="empty-copy">No sessions in this filter window.</p>
      ) : (
        <div className="health-summary">
          <strong>{formatPercent(succeeded, total)} success</strong>
          <span>{formatCount(failed, 'failed session')}</span>
          <span>{formatCount(running, 'running session')}</span>
        </div>
      )}
    </section>
  )
}

function BreakdownHeader({
  id,
  label,
  title,
}: {
  id: string
  label: string
  title: string
}) {
  return (
    <div className="breakdown-heading">
      <h3 id={id}>{title}</h3>
      <span>{label}</span>
    </div>
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
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

function ResponsePanel({
  response,
  state,
}: {
  response: ChatResponseBody | null
  state: RequestState
}) {
  if (state === 'loading') {
    if (response !== null) {
      return <ResponseContent response={response} />
    }
    return (
      <div className="message-card message-card-muted" aria-live="polite">
        <span className="message-role">Assistant</span>
        <p>Waiting for response...</p>
      </div>
    )
  }

  if (response === null) {
    return (
      <div className="message-card message-card-muted">
        <span className="message-role">Assistant</span>
        <p>No response yet.</p>
      </div>
    )
  }

  return (
    <ResponseContent response={response} />
  )
}

function ResponseContent({ response }: { response: ChatResponseBody }) {
  return (
    <div className="response-stack" aria-label="Chat response">
      <div className="message-card">
        <div className="message-card-header">
          <span className="message-role">Assistant</span>
          {response.session_id ? (
            <span className="session-chip">{response.session_id}</span>
          ) : null}
        </div>
        <p>{response.answer}</p>
      </div>

      <section className="result-section" aria-labelledby="citations-title">
        <h3 id="citations-title">Citations</h3>
        {response.citations.length === 0 ? (
          <p className="empty-copy">No citations returned.</p>
        ) : (
          <ol className="citation-list">
            {response.citations.map((result) => (
              <li key={result.chunk_id}>
                <div>
                  <strong>{result.citation.source_external_id}</strong>
                  <p>{result.citation.snippet}</p>
                </div>
                <span>{formatScore(result.score)}</span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="result-section" aria-labelledby="tool-calls-title">
        <h3 id="tool-calls-title">Tool calls</h3>
        {response.tool_calls.length === 0 ? (
          <p className="empty-copy">No tool calls returned.</p>
        ) : (
          <ul className="tool-call-list">
            {response.tool_calls.map((call) => (
              <li key={`${call.name}-${call.query}`}>
                <strong>{call.name}</strong>
                <span>{call.query}</span>
                <small>
                  limit {call.limit} / {call.result_count} results
                </small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function HistoryPanel({
  detail,
  detailError,
  detailState,
  error,
  onRefresh,
  onSelectSession,
  selectedSessionId,
  sessions,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  detailError: string | null
  detailState: RequestState
  error: string | null
  onRefresh(): void
  onSelectSession(sessionId: string): void
  selectedSessionId: string | null
  sessions: ChatSessionSummary[]
  state: RequestState
}) {
  return (
    <aside className="panel" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">History</p>
          <h2 id="history-title">Recent sessions</h2>
        </div>
        <span className={statusClassName(state)}>
          {historyStatusLabel(state)}
        </span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh history'}
      </button>

      {error ? (
        <p className="history-error" role="status">
          {error}
        </p>
      ) : null}

      <ul className="session-list" aria-label="Recent sessions">
        {sessions.length === 0 ? (
          <li>
            <span>No refreshed sessions yet</span>
            <strong>Empty</strong>
          </li>
        ) : (
          sessions.map((session) => (
            <li key={session.session_id}>
              <button
                aria-label={session.session_id}
                className={
                  session.session_id === selectedSessionId
                    ? 'session-button session-button-selected'
                    : 'session-button'
                }
                onClick={() => onSelectSession(session.session_id)}
                type="button"
              >
                <span>{session.session_id}</span>
                <small>
                  {session.message_count} messages / {session.tool_call_count}{' '}
                  tool calls
                </small>
                <strong>{session.status}</strong>
              </button>
            </li>
          ))
        )}
      </ul>

      <SessionDetailPanel
        detail={detail}
        error={detailError}
        state={detailState}
      />
    </aside>
  )
}

function SessionDetailPanel({
  detail,
  error,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  error: string | null
  state: RequestState
}) {
  if (state === 'loading') {
    return (
      <section className="detail-panel" aria-live="polite">
        <h3>Session detail</h3>
        <p className="empty-copy">Loading session detail...</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="detail-panel">
        <h3>Session detail</h3>
        <p className="history-error" role="status">
          {error}
        </p>
      </section>
    )
  }

  if (detail === null) {
    return (
      <section className="detail-panel">
        <h3>Session detail</h3>
        <p className="empty-copy">Select a session to inspect stored history.</p>
      </section>
    )
  }

  return (
    <section className="detail-panel" aria-label="Selected session detail">
      <div className="detail-heading">
        <h3>Session detail</h3>
        <span>{detail.session.status}</span>
      </div>
      <p className="detail-session-id">{detail.session.session_id}</p>

      <section className="detail-section" aria-labelledby="messages-title">
        <h4 id="messages-title">Messages</h4>
        <ol className="detail-list">
          {detail.messages.map((message) => (
            <li key={message.message_id}>
              <strong>{message.role}</strong>
              <p>{message.content}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="detail-section" aria-labelledby="history-tools-title">
        <h4 id="history-tools-title">Tool calls</h4>
        <CompactStateList
          emptyLabel="No stored tool calls."
          items={detail.tool_calls}
          renderItem={(call) => <ToolCallDetail call={call} />}
        />
      </section>

      <section className="detail-section" aria-labelledby="retrieval-runs-title">
        <h4 id="retrieval-runs-title">Retrieval runs</h4>
        <CompactStateList
          emptyLabel="No stored retrieval runs."
          items={detail.retrieval_runs}
          renderItem={(run) => <RetrievalRunDetail run={run} />}
        />
      </section>

      <section className="detail-section" aria-labelledby="provider-usage-title">
        <h4 id="provider-usage-title">Provider usage</h4>
        <CompactStateList
          emptyLabel="No provider usage stored."
          items={detail.provider_usage}
          renderItem={(usage) => <ProviderUsageDetail usage={usage} />}
        />
      </section>
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
    return <p className="empty-copy">{emptyLabel}</p>
  }

  return <ul className="detail-list">{items.map(renderItem)}</ul>
}

function ToolCallDetail({ call }: { call: ChatHistoryToolCall }) {
  return (
    <li key={call.tool_call_id}>
      <strong>{call.tool_name}</strong>
      <p>{formatJsonValue(call.arguments)}</p>
      <small>{call.status}</small>
    </li>
  )
}

function RetrievalRunDetail({ run }: { run: ChatHistoryRetrievalRun }) {
  return (
    <li key={run.retrieval_run_id}>
      <strong>{run.query}</strong>
      <p>
        {run.strategy} / top {run.top_k}
      </p>
      <ul className="retrieved-chunk-list">
        {run.retrieved_chunks.map((chunk) => (
          <RetrievedChunkDetail chunk={chunk} key={chunk.retrieved_chunk_id} />
        ))}
      </ul>
    </li>
  )
}

function RetrievedChunkDetail({ chunk }: { chunk: ChatHistoryRetrievedChunk }) {
  return (
    <li>
      <span>#{chunk.rank}</span>
      <p>{getCitationText(chunk.citation, 'snippet')}</p>
    </li>
  )
}

function ProviderUsageDetail({ usage }: { usage: ChatHistoryProviderUsage }) {
  return (
    <li key={usage.provider_usage_id}>
      <strong>
        {usage.provider} / {usage.model}
      </strong>
      <p>
        {usage.total_tokens ?? 'unknown'} tokens
        {usage.estimated_cost_usd === null
          ? ''
          : ` / $${usage.estimated_cost_usd.toFixed(4)}`}
      </p>
      <small>{usage.status}</small>
    </li>
  )
}

async function refreshHistory(
  client: ApiClient,
  projectId: string,
  callbacks: {
    onError(error: string | null): void
    onItems(items: ChatSessionSummary[]): void
    onState(state: RequestState): void
  },
) {
  callbacks.onState('loading')
  try {
    const history = await client.listChatSessions(projectId, {
      limit: HISTORY_LIMIT,
    })
    callbacks.onItems(history.items)
    callbacks.onState('succeeded')
  } catch (error) {
    callbacks.onError(getErrorMessage(error))
    callbacks.onState('failed')
  }
}

function getDefaultApiBaseUrl(): string {
  const configured = (
    import.meta.env.VITE_ADAPTIVE_RAG_API_BASE_URL ?? ''
  ).trim()
  return configured.length > 0 ? configured : DEFAULT_API_BASE_URL
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Request failed.'
}

function appendAnswerDelta(
  response: ChatResponseBody | null,
  text: string,
): ChatResponseBody {
  const current = response ?? emptyChatResponse()
  return {
    ...current,
    answer: `${current.answer}${text}`,
  }
}

function appendToolCall(
  response: ChatResponseBody | null,
  toolCall: ChatToolCall,
): ChatResponseBody {
  const current = response ?? emptyChatResponse()
  return {
    ...current,
    tool_calls: [...current.tool_calls, toolCall],
  }
}

function emptyChatResponse(): ChatResponseBody {
  return {
    answer: '',
    citations: [],
    session_id: null,
    tool_calls: [],
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function setResponseSessionId(
  response: ChatResponseBody | null,
  sessionId: string,
): ChatResponseBody {
  const current = response ?? emptyChatResponse()
  return {
    ...current,
    session_id: sessionId,
  }
}

function shouldFallbackToJsonChat(error: unknown): boolean {
  if (error instanceof ApiClientError) {
    return error.status === 404 || error.status === 405 || error.status >= 500
  }
  return true
}

function normalizeLimit(value: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return DEFAULT_RETRIEVAL_LIMIT
  }
  return Math.min(20, Math.max(1, Math.trunc(parsed)))
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

function statusClassName(state: RequestState): string {
  return state === 'failed' ? 'status-dot status-dot-error' : 'status-dot'
}

function requestStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Asking'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Answered'
  }
  return 'Ready'
}

function historyStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Refreshing'
  }
  if (state === 'failed') {
    return 'Error'
  }
  return 'Latest'
}

function observabilityStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Refreshing'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Loaded'
  }
  return 'Ready'
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`
}

function formatNullableUsd(value: number | null): string {
  return value === null ? 'n/a' : formatUsd(value)
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}

function formatNullableNumber(value: number | null): string {
  return value === null ? 'n/a' : formatNumber(value)
}

function formatNullableMs(value: number | null): string {
  return value === null ? 'n/a' : `${value} ms`
}

function formatPercent(value: number, total: number): string {
  if (total === 0) {
    return '0.0%'
  }
  return `${((value / total) * 100).toFixed(1)}%`
}

function formatCount(value: number, singularLabel: string): string {
  if (value === 1) {
    return `1 ${singularLabel}`
  }
  return `${formatNumber(value)} ${singularLabel}s`
}

function optionalFilterValue(value: string): string | null {
  const trimmedValue = value.trim()
  return trimmedValue.length > 0 ? trimmedValue : null
}

function getStatusBreakdown(
  byStatus: Record<string, number>,
): { count: number; status: string }[] {
  return Object.entries(byStatus)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ count, status }))
    .sort((left, right) => {
      const leftIndex = STATUS_ORDER.indexOf(left.status)
      const rightIndex = STATUS_ORDER.indexOf(right.status)
      if (leftIndex !== -1 || rightIndex !== -1) {
        return normalizeStatusIndex(leftIndex) - normalizeStatusIndex(rightIndex)
      }
      return right.count - left.count
    })
}

function normalizeStatusIndex(index: number): number {
  return index === -1 ? Number.MAX_SAFE_INTEGER : index
}

function getSlowestP95Group(
  groups: ChatObservabilityProviderUsageGroup[],
): ChatObservabilityProviderUsageGroup | null {
  let slowest: ChatObservabilityProviderUsageGroup | null = null
  for (const group of groups) {
    if (group.latency_ms.p95 === null) {
      continue
    }
    if (slowest === null || group.latency_ms.p95 > slowest.latency_ms.p95!) {
      slowest = group
    }
  }
  return slowest
}

export default App
