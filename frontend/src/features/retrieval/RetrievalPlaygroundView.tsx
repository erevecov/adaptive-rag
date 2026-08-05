import { type FormEvent, useState } from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/control'
import { DataList, DataListItem } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldLabel } from '@/components/ui/field'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import { Select } from '@/components/ui/select'
import {
  ApiClientError,
  type ApiClient,
  type RetrievalResult,
  type RetrievalStrategy,
} from '@/lib/apiClient'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed'

const STRATEGY_OPTIONS = [
  { label: 'dense + sparse (default)', value: 'dense_sparse' },
  { label: 'dense only', value: 'dense' },
  { label: 'sparse only', value: 'sparse' },
  { label: 'graph', value: 'graph' },
] as const

const RERANK_OPTIONS = [
  { label: 'Off', value: 'off' },
  { label: 'On', value: 'on' },
] as const

export type RetrievalPlaygroundPanelProps = {
  client: ApiClient
  projectId: string
}

export function RetrievalPlaygroundPanel({
  client,
  projectId,
}: RetrievalPlaygroundPanelProps) {
  const [query, setQuery] = useState('')
  const [strategy, setStrategy] = useState<RetrievalStrategy>('dense_sparse')
  const [limit, setLimit] = useState('10')
  const [rerankEnabled, setRerankEnabled] = useState(false)
  const [rerankCandidateLimit, setRerankCandidateLimit] = useState('20')
  const [state, setState] = useState<RequestState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<RetrievalResult[]>([])

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!projectId.trim()) {
      setError('Select a project before searching.')
      setState('failed')
      setResults([])
      return
    }
    const trimmed = query.trim()
    if (!trimmed) {
      setError('Enter a non-empty query.')
      setState('failed')
      setResults([])
      return
    }
    const parsedLimit = Number.parseInt(limit, 10)
    if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
      setError('Limit must be a positive integer.')
      setState('failed')
      setResults([])
      return
    }
    let rerank: { candidate_limit: number } | null = null
    if (rerankEnabled) {
      const candidateLimit = Number.parseInt(rerankCandidateLimit, 10)
      if (!Number.isFinite(candidateLimit) || candidateLimit < parsedLimit) {
        setError(
          'Rerank candidate limit must be an integer >= limit when rerank is on.',
        )
        setState('failed')
        setResults([])
        return
      }
      rerank = { candidate_limit: candidateLimit }
    }

    setState('loading')
    setError(null)
    setResults([])
    try {
      const response = await client.searchRetrieval(projectId, {
        query: trimmed,
        limit: parsedLimit,
        strategy,
        rerank,
      })
      setResults(response.results)
      setState('succeeded')
    } catch (err) {
      setResults([])
      setState('failed')
      setError(formatError(err))
    }
  }

  return (
    <Panel
      aria-labelledby="retrieval-playground-title"
      data-testid="retrieval-playground"
      role="region"
    >
      <PanelHeader className="p-4">
        <PanelTitle id="retrieval-playground-title">
          Retrieval playground
        </PanelTitle>
        <PanelDescription>
          Run project retrieval without chat. Inspect ranked chunks, scores, and
          strategy for the selected project.
        </PanelDescription>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0">
        <form
          className="grid gap-4"
          onSubmit={(event) => void handleSearch(event)}
        >
          <Field>
            <FieldLabel htmlFor="retrieval-query">Query</FieldLabel>
            <FieldControl>
              <Textarea
                id="retrieval-query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="What should retrieval return?"
                rows={3}
              />
            </FieldControl>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field>
              <FieldLabel htmlFor="retrieval-strategy">Strategy</FieldLabel>
              <FieldControl>
                <Select
                  id="retrieval-strategy"
                  value={strategy}
                  onValueChange={(value) =>
                    setStrategy(value as RetrievalStrategy)
                  }
                  options={STRATEGY_OPTIONS}
                />
              </FieldControl>
            </Field>
            <Field>
              <FieldLabel htmlFor="retrieval-limit">Limit</FieldLabel>
              <FieldControl>
                <Input
                  id="retrieval-limit"
                  inputMode="numeric"
                  value={limit}
                  onChange={(event) => setLimit(event.target.value)}
                />
              </FieldControl>
            </Field>
            <Field>
              <FieldLabel htmlFor="retrieval-rerank">Rerank</FieldLabel>
              <FieldControl>
                <Select
                  id="retrieval-rerank"
                  value={rerankEnabled ? 'on' : 'off'}
                  onValueChange={(value) => setRerankEnabled(value === 'on')}
                  options={RERANK_OPTIONS}
                />
              </FieldControl>
            </Field>
            <Field>
              <FieldLabel htmlFor="retrieval-rerank-limit">
                Rerank candidates
              </FieldLabel>
              <FieldControl>
                <Input
                  aria-describedby="rerank-limit-help"
                  id="retrieval-rerank-limit"
                  inputMode="numeric"
                  disabled={!rerankEnabled}
                  value={rerankCandidateLimit}
                  onChange={(event) =>
                    setRerankCandidateLimit(event.target.value)
                  }
                />
              </FieldControl>
              {!rerankEnabled ? (
                <p
                  className="text-xs text-muted-foreground"
                  id="rerank-limit-help"
                >
                  Enable rerank to edit candidate limit.
                </p>
              ) : null}
            </Field>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={state === 'loading'}>
              {state === 'loading' ? 'Searching…' : 'Search'}
            </Button>
            <StatusBadge
              aria-live="polite"
              role="status"
              tone={requestStateTone(state)}
            >
              {requestStateLabel(state)}
            </StatusBadge>
            {!projectId.trim() ? (
              <span className="text-sm text-muted-foreground">
                Select a project in the sidebar first.
              </span>
            ) : null}
          </div>
        </form>

        {error ? (
          <InlineFeedback role="alert" tone="danger">
            {error}
          </InlineFeedback>
        ) : null}

        <div
          aria-busy={state === 'loading' || undefined}
          aria-label="Retrieval results"
          className="grid gap-2"
          role="region"
        >
          {state === 'loading' ? (
            <EmptyState
              aria-busy="true"
              className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
              data-slot-state="loading"
              role="status"
            >
              <p className="font-medium text-foreground/90">Searching…</p>
              <span className="sr-only">Searching retrieval…</span>
            </EmptyState>
          ) : null}

          {state === 'idle' && results.length === 0 && !error ? (
            <EmptyState
              className="border-border/60 bg-muted/20 p-4 text-left"
              data-slot-state="empty"
              role="status"
            >
              <p className="font-medium text-foreground/90">
                Run a query to inspect ranked chunks.
              </p>
              <p className="text-xs text-muted-foreground">
                Choose strategy, optional rerank, then Search.
              </p>
            </EmptyState>
          ) : null}

          {state === 'succeeded' && results.length === 0 ? (
            <EmptyState
              className="border-border/60 bg-muted/20 p-4 text-left"
              data-slot-state="empty"
              role="status"
            >
              <p className="font-medium text-foreground/90">
                No chunks returned
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
                <li>Try strategy dense or sparse</li>
                <li>Confirm sources are ingested for this project</li>
                <li>Raise limit or adjust the query</li>
              </ul>
            </EmptyState>
          ) : null}

          {results.length > 0 ? (
            <DataList aria-label="Ranked retrieval results">
              {results.map((result, index) => (
                <DataListItem
                  className="grid gap-2"
                  key={result.chunk_id}
                  data-rank={index + 1}
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Badge className="tabular-nums" tone="neutral">
                      rank {index + 1}
                    </Badge>
                    <Badge className="font-mono tabular-nums">
                      {result.score.toFixed(4)}
                    </Badge>
                    <StatusBadge tone="neutral">
                      {result.strategy ?? '—'}
                    </StatusBadge>
                    {result.distance != null ? (
                      <span className="text-xs tabular-nums text-muted-foreground">
                        distance {result.distance.toFixed(4)}
                      </span>
                    ) : null}
                  </div>
                  <div className="grid min-w-0 gap-1">
                    <strong className="break-words text-sm font-semibold">
                      {result.citation.source_external_id}
                    </strong>
                    <small className="text-xs text-muted-foreground">
                      {result.citation.source_type}
                      {result.fallback_reason
                        ? ` · fallback: ${result.fallback_reason}`
                        : ''}
                    </small>
                    <p className="line-clamp-4 whitespace-pre-wrap text-sm text-muted-foreground">
                      {result.citation.snippet}
                    </p>
                  </div>
                </DataListItem>
              ))}
            </DataList>
          ) : null}
        </div>
      </PanelBody>
    </Panel>
  )
}

function requestStateTone(
  state: RequestState,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (state === 'loading') {
    return 'warning'
  }
  if (state === 'succeeded') {
    return 'success'
  }
  if (state === 'failed') {
    return 'danger'
  }
  return 'neutral'
}

function requestStateLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Searching'
  }
  if (state === 'succeeded') {
    return 'Done'
  }
  if (state === 'failed') {
    return 'Failed'
  }
  return 'Ready'
}

function formatError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (typeof error.detail === 'string') {
      return error.detail
    }
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Retrieval search failed.'
}
