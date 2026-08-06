import { type FormEvent, useState } from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/control'
import { DataList, DataListItem } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldHelp, FieldLabel } from '@/components/ui/field'
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
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed'

const STRATEGY_OPTIONS = [
  { label: 'Dense + Sparse (Default)', value: 'dense_sparse' },
  { label: 'Dense Only', value: 'dense' },
  { label: 'Sparse Only', value: 'sparse' },
  { label: 'Graph', value: 'graph' },
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
      setError('Select a Project Before Searching.')
      setState('failed')
      setResults([])
      return
    }
    const trimmed = query.trim()
    if (!trimmed) {
      setError('Enter a Non-Empty Query.')
      setState('failed')
      setResults([])
      return
    }
    const parsedLimit = Number.parseInt(limit, 10)
    if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
      setError('Limit Must Be a Positive Integer.')
      setState('failed')
      setResults([])
      return
    }
    let rerank: { candidate_limit: number } | null = null
    if (rerankEnabled) {
      const candidateLimit = Number.parseInt(rerankCandidateLimit, 10)
      if (!Number.isFinite(candidateLimit) || candidateLimit < parsedLimit) {
        setError(
          'Rerank Candidate Limit Must Be an Integer >= Limit When Rerank Is On.',
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
      <PanelHeader className="p-4 max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <PanelTitle id="retrieval-playground-title">
          Retrieval Playground
        </PanelTitle>
        <PanelDescription>
          Run Project Retrieval Without Chat. Inspect Ranked Chunks, Scores, and
          Strategy for the Selected Project.
        </PanelDescription>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">
        <form
          className="grid gap-4 max-[680px]:gap-0.5"
          onSubmit={(event) => void handleSearch(event)}
        >
          <Field>
            <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor="retrieval-query">Query</FieldLabel>
            <FieldControl>
              <Textarea
                id="retrieval-query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="What Should Retrieval Return?"
                rows={3}
              />
            </FieldControl>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 max-[680px]:gap-0.5">
            <Field>
              <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor="retrieval-strategy">Strategy</FieldLabel>
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
              <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor="retrieval-limit">Limit</FieldLabel>
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
              <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor="retrieval-rerank">Rerank</FieldLabel>
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
              <FieldLabel className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor="retrieval-rerank-limit">
                Rerank Candidates
              </FieldLabel>
              <FieldControl>
                <Input
                  aria-describedby={
                    rerankEnabled ? undefined : 'rerank-limit-help'
                  }
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
                <FieldHelp id="rerank-limit-help">
                  Enable Rerank to Edit Candidate Limit.
                </FieldHelp>
              ) : null}
            </Field>
          </div>
          <div className="flex flex-wrap items-center gap-3 max-[680px]:gap-0.5">
            <Button className="max-[680px]:h-8 max-[680px]:px-2 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter" type="submit" disabled={state === 'loading'}>
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
              <span className="text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                Select a Project in the Sidebar First.
              </span>
            ) : null}
          </div>
        </form>

        {error && state !== 'failed' ? (
          <InlineFeedback className="max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" role="alert" tone="danger">
            {error}
          </InlineFeedback>
        ) : null}

        <div
          aria-busy={state === 'loading' || undefined}
          aria-label="Retrieval Results"
          className="grid gap-2 max-[680px]:gap-0.5"
          role="region"
        >
          {state === 'loading' ? (
            <EmptyState
              aria-busy="true"
              className="border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/35 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/30 max-[680px]:tracking-tighter"
              data-slot-state="loading"
              role="status"
            >
              <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">Searching…</p>
              <span className="sr-only">Searching Retrieval…</span>
            </EmptyState>
          ) : null}

          {state === 'failed' ? (
            <EmptyState
              className="border-destructive/40 bg-destructive/5 p-4 text-left tracking-tight max-[680px]:p-0.5"
              data-slot-state="failed"
              role="alert"
            >
              <p className="font-semibold text-destructive">Search Failed</p>
              <p className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                {error ?? 'Adjust Query or Strategy and Retry.'}
              </p>
            </EmptyState>
          ) : null}

          {state === 'idle' && results.length === 0 && !error ? (
            <EmptyState
              className="border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/35 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/30 max-[680px]:tracking-tighter"
              data-slot-state="empty"
              role="status"
            >
              <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                Run A Query To Inspect Ranked Chunks.
              </p>
              <p className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                Choose Strategy, Optional Rerank, Then Search.
              </p>
            </EmptyState>
          ) : null}

          {state === 'succeeded' && results.length === 0 ? (
            <EmptyState
              className="border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/35 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/30 max-[680px]:tracking-tighter"
              data-slot-state="empty"
              role="status"
            >
              <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                No Chunks Returned
              </p>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground max-[680px]:space-y-0 max-[680px]:pl-3 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                <li>Try Strategy Dense or Sparse</li>
                <li>Confirm Sources Are Ingested for This Project</li>
                <li>Raise Limit or Adjust the Query</li>
              </ul>
            </EmptyState>
          ) : null}

          {results.length > 0 ? (
            <DataList aria-label="Ranked Retrieval Results">
              {results.map((result, index) => (
                <DataListItem
                  className="grid gap-2 max-[680px]:gap-0.5"
                  key={result.chunk_id}
                  data-rank={index + 1}
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2 max-[680px]:gap-0.5">
                    <Badge
                      aria-label={`Rank ${index + 1}`}
                      className="min-w-[4.5ch] justify-center tabular-nums max-[680px]:min-w-[3.5ch] max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter"
                      tone="neutral"
                    >
                      #{index + 1}
                    </Badge>
                    <Badge
                      aria-label={`Score ${result.score.toFixed(4)}`}
                      className="min-w-[7ch] justify-center font-mono tabular-nums max-[680px]:min-w-[5.5ch] max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter"
                    >
                      {result.score.toFixed(4)}
                    </Badge>
                    <StatusBadge tone="neutral">
                      {retrievalStrategyDisplay(result.strategy)}
                    </StatusBadge>
                    {result.distance != null ? (
                      <span className="min-w-[8ch] text-xs tabular-nums text-muted-foreground max-[680px]:min-w-[6ch] max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter">
                        Dist {result.distance.toFixed(4)}
                      </span>
                    ) : null}
                  </div>
                  <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                    <strong className="break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                      {result.citation.source_external_id}
                    </strong>
                    <small className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                      {retrievalSourceTypeDisplay(result.citation.source_type)}
                      {result.fallback_reason
                        ? ` · Fallback: ${retrievalFallbackDisplay(result.fallback_reason)}`
                        : ''}
                    </small>
                    <p className="line-clamp-4 whitespace-pre-wrap text-sm tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
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
      return operatorSafeMessage(error.detail, error.message)
    }
    return operatorSafeMessage(error.message)
  }
  if (error instanceof Error) {
    return operatorSafeMessage(error.message)
  }
  return 'Retrieval Search Failed.'
}

function retrievalStrategyDisplay(strategy: string | null | undefined): string {
  if (strategy == null || strategy.trim().length === 0) {
    return '—'
  }
  const match = STRATEGY_OPTIONS.find((option) => option.value === strategy)
  if (match) {
    return match.label.replace(/ \(default\)$/, '')
  }
  return strategy.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function retrievalSourceTypeDisplay(sourceType: string): string {
  switch (sourceType) {
    case 'markdown':
      return 'Markdown'
    case 'text':
      return 'Text'
    case 'txt':
      return 'Txt'
    case 'url':
      return 'URL'
    case 'pdf':
      return 'PDF'
    case 'docx':
      return 'DOCX'
    default:
      return sourceType.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  }
}

function retrievalFallbackDisplay(reason: string): string {
  return reason.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}
