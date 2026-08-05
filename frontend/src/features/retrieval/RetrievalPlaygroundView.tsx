import { type FormEvent, useState } from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/control'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '@/components/ui/table'
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
      return
    }
    const trimmed = query.trim()
    if (!trimmed) {
      setError('Enter a non-empty query.')
      setState('failed')
      return
    }
    const parsedLimit = Number.parseInt(limit, 10)
    if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
      setError('Limit must be a positive integer.')
      setState('failed')
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
        return
      }
      rerank = { candidate_limit: candidateLimit }
    }

    setState('loading')
    setError(null)
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
    <Panel data-testid="retrieval-playground">
      <PanelHeader>
        <PanelTitle>Retrieval playground</PanelTitle>
        <PanelDescription>
          Run project retrieval without chat. Inspect ranked chunks, scores, and
          strategy for the selected project.
        </PanelDescription>
      </PanelHeader>
      <PanelBody className="grid gap-6">
        <form
          className="grid gap-4"
          onSubmit={(event) => void handleSearch(event)}
        >
          <Field>
            <FieldLabel htmlFor="retrieval-query">Query</FieldLabel>
            <FieldControl>
              <Textarea
                className="focus-visible:border-primary/40 focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-1"
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
                  aria-label="Strategy"
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
                  className="focus-visible:border-primary/40 focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-1"
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
                  aria-label="Rerank"
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
                  className="focus-visible:border-primary/40 focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-1"
                  id="retrieval-rerank-limit"
                  inputMode="numeric"
                  disabled={!rerankEnabled}
                  value={rerankCandidateLimit}
                  onChange={(event) =>
                    setRerankCandidateLimit(event.target.value)
                  }
                />
              </FieldControl>
            </Field>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={state === 'loading'}>
              {state === 'loading' ? 'Searching…' : 'Search'}
            </Button>
            <StatusBadge tone={requestStateTone(state)}>
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

        {state === 'succeeded' && results.length === 0 ? (
          <EmptyState className="p-4 text-left">
            No hits. Retrieval returned zero chunks for this query and strategy.
          </EmptyState>
        ) : null}

        {results.length > 0 ? (
          <TableScroll>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rank</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Snippet</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((result, index) => (
                  <TableRow key={result.chunk_id}>
                    <TableCell>{index + 1}</TableCell>
                    <TableCell>
                      <Badge>{result.score.toFixed(4)}</Badge>
                    </TableCell>
                    <TableCell>{result.strategy ?? '—'}</TableCell>
                    <TableCell>
                      <div className="grid gap-1">
                        <span className="font-medium">
                          {result.citation.source_external_id}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {result.citation.source_type}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-xl whitespace-pre-wrap text-sm">
                      {result.citation.snippet}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableScroll>
        ) : null}
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
