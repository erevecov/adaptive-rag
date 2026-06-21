import { type FormEvent, useMemo, useState } from 'react'
import './App.css'
import {
  ApiClientError,
  createApiClient,
  type ApiClient,
  type ChatResponseBody,
  type ChatSessionSummary,
} from './lib/apiClient'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_RETRIEVAL_LIMIT = 5
const HISTORY_LIMIT = 5

type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed'

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
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [historyState, setHistoryState] = useState<RequestState>('idle')
  const [requestError, setRequestError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)

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

    try {
      const nextResponse = await client.askChat(trimmedProjectId, {
        message: trimmedQuestion,
        retrieval_limit: retrievalLimit,
      })
      setResponse(nextResponse)
      setRequestState('succeeded')
      await refreshHistory(client, trimmedProjectId, {
        onError: setHistoryError,
        onItems: setSessions,
        onState: setHistoryState,
      })
    } catch (error) {
      setRequestState('failed')
      setRequestError(getErrorMessage(error))
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
          <span className="status">Local API</span>
        </header>

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
            error={historyError}
            sessions={sessions}
            state={historyState}
          />
        </div>
      </section>
    </main>
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
  error,
  sessions,
  state,
}: {
  error: string | null
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
              <div>
                <span>{session.session_id}</span>
                <small>
                  {session.message_count} messages / {session.tool_call_count}{' '}
                  tool calls
                </small>
              </div>
              <strong>{session.status}</strong>
            </li>
          ))
        )}
      </ul>
    </aside>
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

function statusClassName(state: RequestState): string {
  return state === 'failed' ? 'status-dot status-dot-error' : 'status-dot'
}

function requestStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Asking'
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

export default App
