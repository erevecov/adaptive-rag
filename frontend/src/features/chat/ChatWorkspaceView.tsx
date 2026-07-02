import {
  type Dispatch,
  type FormEvent,
  type Ref,
  type SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { ChatPipelineSteps } from '@/components/ChatPipelineSteps'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button, IconButton } from '@/components/ui/button'
import { Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldLabel } from '@/components/ui/field'
import { Panel, PanelBody } from '@/components/ui/panel'
import type {
  ChatHistoryProviderUsage,
  ChatResponseBody,
  ChatToolCall,
  KnowledgeProposal,
} from '@/lib/apiClient'
import type { ChatStep } from '@/lib/chatSteps'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type ChatKnowledgeDraftAction = 'approve' | 'request_approval' | string
export type ChatKnowledgeDraftStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'cancelled'
  | string
export type ChatKnowledgeDraft = {
  draftId: string
  error: string | null
  proposalId: string | null
  reviewAction: ChatKnowledgeDraftAction
  scope: string
  status: ChatKnowledgeDraftStatus
  text: string
}
export type ChatKnowledgeDraftMap = Record<string, ChatKnowledgeDraft>
export type ChatKnowledgeDraftSetter = Dispatch<SetStateAction<ChatKnowledgeDraftMap>>

type ChatKnowledgeLifecycleEvent = {
  action: 'approve' | 'cancel'
  allPending: boolean
  draftId: string | null
  key: string
}

export type ChatWorkspacePanelProps = {
  activeResponseQuestion: string | null
  drafts: ChatKnowledgeDraftMap
  isAsking: boolean
  isContextInspectorActive: boolean
  isMinimapInspectorActive: boolean
  isSpeechSupported: boolean
  onCancelRequest(): void
  onOpenContextInspector(): void
  onOpenMinimapInspector(): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onQuestionChange(value: string): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onStartSpeechRecognition(): void
  onStopSpeechRecognition(): void
  onSubmit(event: FormEvent<HTMLFormElement>): void
  onSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal>
  onTranscriptScroll?: () => void
  providerUsage: ChatHistoryProviderUsage[]
  question: string
  requestError: string | null
  requestState: RequestState
  response: ChatResponseBody | null
  setDrafts: ChatKnowledgeDraftSetter
  speechFeedback: string | null
  speechState: RequestState
  transcriptRef?: Ref<HTMLDivElement>
}

type ResponseUsageSummary = {
  costUsd: number | null
  inputTokens: number | null
  model: string | null
  outputTokens: number | null
  provider: string | null
  totalTokens: number | null
}

const QUESTION_PREVIEW_MAX_CHARS = 96
const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')

export function ChatWorkspacePanel({
  activeResponseQuestion,
  drafts,
  isAsking,
  isContextInspectorActive,
  isMinimapInspectorActive,
  isSpeechSupported,
  onCancelRequest,
  onOpenContextInspector,
  onOpenMinimapInspector,
  onOpenSource,
  onQuestionChange,
  onRefineKnowledgeDraft,
  onStartSpeechRecognition,
  onStopSpeechRecognition,
  onSubmit,
  onSubmitKnowledgeDraft,
  onTranscriptScroll,
  providerUsage,
  question,
  requestError,
  requestState,
  response,
  setDrafts,
  speechFeedback,
  speechState,
  transcriptRef,
}: ChatWorkspacePanelProps) {
  return (
    <Panel
      aria-label="Chat workspace"
      className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto]"
      role="region"
    >
      <PanelBody className="grid min-h-0 gap-4 p-4">
        <div
          aria-label="Chat transcript"
          className="min-h-0 overflow-y-auto pr-1"
          onScroll={onTranscriptScroll}
          ref={transcriptRef}
          role="region"
        >
          <ResponsePanel
            drafts={drafts}
            onOpenSource={onOpenSource}
            onRefineKnowledgeDraft={onRefineKnowledgeDraft}
            onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
            providerUsage={providerUsage}
            question={activeResponseQuestion}
            response={response}
            setDrafts={setDrafts}
            state={requestState}
          />
        </div>

        <form className="grid gap-3 border-t border-border pt-4" onSubmit={onSubmit}>
          <Field>
            <FieldLabel htmlFor="chat-question">Question</FieldLabel>
            <FieldControl>
              <Textarea
                className="min-h-24"
                id="chat-question"
                name="question"
                onChange={(event) => onQuestionChange(event.currentTarget.value)}
                placeholder="Ask a question about indexed sources"
                rows={3}
                value={question}
              />
            </FieldControl>
          </Field>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <IconButton
                aria-pressed={isContextInspectorActive}
                label="Open context sidebar"
                onClick={onOpenContextInspector}
                variant={isContextInspectorActive ? 'primary' : 'secondary'}
              >
                <ContextRingIcon />
              </IconButton>
              <IconButton
                aria-pressed={isMinimapInspectorActive}
                label="Open minimap sidebar"
                onClick={onOpenMinimapInspector}
                variant={isMinimapInspectorActive ? 'primary' : 'secondary'}
              >
                <MinimapIcon />
              </IconButton>
              <SpeechInputControl
                feedback={speechFeedback}
                isSupported={isSpeechSupported}
                onStart={onStartSpeechRecognition}
                onStop={onStopSpeechRecognition}
                state={speechState}
              />
              <Button disabled={isAsking} type="submit">
                <SendIcon />
                <span>{isAsking ? 'Asking...' : 'Ask'}</span>
              </Button>
            </div>

            {isAsking ? (
              <Button onClick={onCancelRequest} type="button" variant="secondary">
                Cancel
              </Button>
            ) : null}
          </div>

          {requestError ? (
            <InlineFeedback tone="danger">{requestError}</InlineFeedback>
          ) : null}
        </form>
      </PanelBody>
    </Panel>
  )
}

function SpeechInputControl({
  feedback,
  isSupported,
  onStart,
  onStop,
  state,
}: {
  feedback: string | null
  isSupported: boolean
  onStart(): void
  onStop(): void
  state: RequestState
}) {
  const isListening = state === 'loading'
  const buttonLabel = !isSupported
    ? 'Transcript unavailable'
    : isListening
      ? 'Stop transcript'
      : 'Start transcript'
  const message =
    feedback ??
    (isSupported
      ? 'Speech input ready.'
      : 'Speech recognition is not supported in this browser.')

  return (
    <section
      aria-label="Transcript input"
      className="flex min-w-0 items-center gap-2"
    >
      <IconButton
        disabled={!isSupported}
        label={buttonLabel}
        onClick={isListening ? onStop : onStart}
        variant={isListening ? 'primary' : 'secondary'}
      >
        <TranscriptIcon active={isListening} />
      </IconButton>
      <InlineFeedback
        className="min-w-0 max-w-72"
        role={state === 'failed' ? 'alert' : 'status'}
        tone={state === 'failed' ? 'danger' : 'neutral'}
      >
        {message}
      </InlineFeedback>
    </section>
  )
}

function ResponsePanel({
  drafts,
  onOpenSource,
  onRefineKnowledgeDraft,
  onSubmitKnowledgeDraft,
  providerUsage,
  question,
  response,
  setDrafts,
  state,
}: {
  drafts: ChatKnowledgeDraftMap
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal>
  providerUsage: ChatHistoryProviderUsage[]
  question: string | null
  response: ChatResponseBody | null
  setDrafts: ChatKnowledgeDraftSetter
  state: RequestState
}) {
  if (state === 'loading') {
    if (response !== null) {
      return (
        <ResponseContent
          drafts={drafts}
          onOpenSource={onOpenSource}
          onRefineKnowledgeDraft={onRefineKnowledgeDraft}
          onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
          providerUsage={providerUsage}
          question={question}
          response={response}
          setDrafts={setDrafts}
          state={state}
        />
      )
    }
    return <EmptyState aria-live="polite">Waiting for response...</EmptyState>
  }

  if (response === null) {
    return <EmptyState>No response yet.</EmptyState>
  }

  return (
    <ResponseContent
      drafts={drafts}
      onOpenSource={onOpenSource}
      onRefineKnowledgeDraft={onRefineKnowledgeDraft}
      onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
      providerUsage={providerUsage}
      question={question}
      response={response}
      setDrafts={setDrafts}
      state={state}
    />
  )
}

function ResponseContent({
  drafts,
  onOpenSource,
  onRefineKnowledgeDraft,
  onSubmitKnowledgeDraft,
  providerUsage,
  question,
  response,
  setDrafts,
  state,
}: {
  drafts: ChatKnowledgeDraftMap
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal>
  providerUsage: ChatHistoryProviderUsage[]
  question: string | null
  response: ChatResponseBody
  setDrafts: ChatKnowledgeDraftSetter
  state: RequestState
}) {
  const isStreaming = state === 'loading'
  const processedLifecycleEvents = useRef<Set<string>>(new Set())
  const lifecycleEvents = useMemo(
    () => extractKnowledgeLifecycleEvents(response.tool_calls),
    [response.tool_calls],
  )

  useEffect(() => {
    const nextDrafts = extractKnowledgeDrafts(response.tool_calls)
    setDrafts((current) => {
      const merged = { ...current }
      for (const draft of nextDrafts) {
        const existing = merged[draft.draftId]
        merged[draft.draftId] =
          existing === undefined
            ? draft
            : {
                ...existing,
                reviewAction: draft.reviewAction,
                scope: draft.scope,
                status:
                  existing.status === 'draft' ? draft.status : existing.status,
                text:
                  existing.status === 'draft' && existing.text !== draft.text
                    ? draft.text
                    : existing.text,
              }
      }
      for (const event of lifecycleEvents) {
        if (event.action !== 'cancel') {
          continue
        }
        if (event.allPending) {
          for (const draftId of Object.keys(merged)) {
            if (
              merged[draftId].status !== 'approved' &&
              merged[draftId].status !== 'cancelled'
            ) {
              merged[draftId] = {
                ...merged[draftId],
                error: null,
                status: 'cancelled',
              }
            }
          }
          continue
        }
        if (event.draftId !== null && merged[event.draftId] !== undefined) {
          merged[event.draftId] = {
            ...merged[event.draftId],
            error: null,
            status: 'cancelled',
          }
        }
      }
      return merged
    })
  }, [lifecycleEvents, response.tool_calls, setDrafts])

  const handleSubmitDraft = useCallback(
    async (draft: ChatKnowledgeDraft) => {
      setDrafts((current) => ({
        ...current,
        [draft.draftId]: {
          ...current[draft.draftId],
          error: null,
        },
      }))
      try {
        const proposal = await onSubmitKnowledgeDraft(
          drafts[draft.draftId] ?? draft,
          response.session_id,
        )
        setDrafts((current) => ({
          ...current,
          [draft.draftId]: {
            ...current[draft.draftId],
            error: null,
            proposalId: proposal.id,
            status: proposal.status,
            text: proposal.refined_text ?? proposal.proposed_text,
          },
        }))
      } catch (error) {
        setDrafts((current) => ({
          ...current,
          [draft.draftId]: {
            ...current[draft.draftId],
            error: getErrorMessage(error),
          },
        }))
      }
    },
    [drafts, onSubmitKnowledgeDraft, response.session_id, setDrafts],
  )

  useEffect(() => {
    for (const event of lifecycleEvents) {
      if (event.action !== 'approve' || event.draftId === null) {
        continue
      }
      if (processedLifecycleEvents.current.has(event.key)) {
        continue
      }
      const draft = drafts[event.draftId]
      if (draft === undefined || draft.status !== 'draft') {
        continue
      }
      processedLifecycleEvents.current.add(event.key)
      void handleSubmitDraft(draft)
    }
  }, [drafts, handleSubmitDraft, lifecycleEvents])

  const knowledgeDrafts = Object.values(drafts)

  function handleDraftTextChange(draftId: string, text: string) {
    setDrafts((current) => ({
      ...current,
      [draftId]: {
        ...current[draftId],
        error: null,
        text,
      },
    }))
  }

  function handleCancelDraft(draftId: string) {
    setDrafts((current) => ({
      ...current,
      [draftId]: {
        ...current[draftId],
        error: null,
        status: 'cancelled',
      },
    }))
  }
  const steps = response.steps ?? []
  const hasStepDetails = isStreaming || steps.length > 0

  return (
    <div aria-label="Chat response" className="grid gap-4">
      <QuestionPrompt key={question ?? 'empty-question'} question={question} />

      {response.answer.trim().length > 0 || !isStreaming ? (
        <article className="rounded-md border border-border bg-card p-4 text-card-foreground">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {response.answer}
          </p>
        </article>
      ) : null}

      {hasStepDetails ? (
        <ChatPipelineSteps
          isStreaming={isStreaming}
          sourceCount={response.citations.length}
          steps={steps}
        >
          <ResponseDetailsContent
            embedded
            onOpenSource={onOpenSource}
            providerUsage={providerUsage}
            response={response}
          />
        </ChatPipelineSteps>
      ) : null}

      {!hasStepDetails ? (
        <ResponseDetailsPanel
          key={response.session_id ?? response.answer}
          onOpenSource={onOpenSource}
          providerUsage={providerUsage}
          response={response}
        />
      ) : null}

      {knowledgeDrafts.length === 0 ? null : (
        <section aria-label="Knowledge drafts" className="grid gap-3">
          {knowledgeDrafts.map((draft) => (
            <KnowledgeDraftCard
              draft={draft}
              key={draft.draftId}
              onCancel={() => handleCancelDraft(draft.draftId)}
              onRefine={() => onRefineKnowledgeDraft(draft)}
              onSubmit={() => void handleSubmitDraft(draft)}
              onTextChange={(text) =>
                handleDraftTextChange(draft.draftId, text)
              }
            />
          ))}
        </section>
      )}
    </div>
  )
}

function QuestionPrompt({ question }: { question: string | null }) {
  const [expanded, setExpanded] = useState(false)
  const trimmedQuestion = question?.trim() ?? ''
  if (trimmedQuestion.length === 0) {
    return null
  }

  const shouldCollapse = trimmedQuestion.length > QUESTION_PREVIEW_MAX_CHARS
  const displayQuestion =
    shouldCollapse && !expanded
      ? `${trimmedQuestion.slice(0, QUESTION_PREVIEW_MAX_CHARS).trimEnd()}...`
      : trimmedQuestion

  return (
    <div className="sticky top-0 z-10" data-slot="chat-question-sticky">
      {shouldCollapse ? (
        <Button
          aria-expanded={expanded}
          aria-label={expanded ? 'Collapse full question' : 'Expand full question'}
          className="max-w-full justify-start whitespace-normal text-left"
          onClick={() => setExpanded((current) => !current)}
          title={trimmedQuestion}
          type="button"
          variant="secondary"
        >
          {displayQuestion}
        </Button>
      ) : (
        <p className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground">
          {displayQuestion}
        </p>
      )}
    </div>
  )
}

function ResponseDetailsPanel({
  onOpenSource,
  providerUsage,
  response,
}: {
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  providerUsage: ChatHistoryProviderUsage[]
  response: ChatResponseBody
}) {
  const [expanded, setExpanded] = useState(false)
  const usage = summarizeResponseUsage(response.steps ?? [], providerUsage)
  const sourceCount = response.citations.length
  const toolCallCount = response.tool_calls.length
  const hasDetails = sourceCount > 0 || toolCallCount > 0 || usage !== null

  if (!hasDetails) {
    return null
  }

  const summaryParts = [
    formatCount(sourceCount, 'source'),
    formatCount(toolCallCount, 'tool call'),
  ]
  if (usage !== null) {
    summaryParts.push('usage')
  }

  return (
    <section
      aria-label="Response details"
      className="rounded-md border border-border bg-muted/40 p-3"
    >
      <Button
        aria-expanded={expanded}
        aria-label={expanded ? 'Collapse response details' : 'Expand response details'}
        className="w-full justify-start"
        onClick={() => setExpanded((current) => !current)}
        type="button"
        variant="secondary"
      >
        <span aria-hidden="true">{expanded ? 'v' : '>'}</span>
        details - {summaryParts.join(' - ')}
      </Button>

      {expanded ? (
        <ResponseDetailsContent
          onOpenSource={onOpenSource}
          providerUsage={providerUsage}
          response={response}
        />
      ) : null}
    </section>
  )
}

function ResponseDetailsContent({
  embedded = false,
  onOpenSource,
  providerUsage,
  response,
}: {
  embedded?: boolean
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  providerUsage: ChatHistoryProviderUsage[]
  response: ChatResponseBody
}) {
  const usage = summarizeResponseUsage(response.steps ?? [], providerUsage)
  const sourceCount = response.citations.length
  const toolCallCount = response.tool_calls.length
  const hasDetails = sourceCount > 0 || toolCallCount > 0 || usage !== null

  if (!hasDetails) {
    return null
  }

  return (
    <div className={embedded ? 'grid gap-3 pt-2' : 'grid gap-3 pt-3'}>
      {usage !== null ? <ResponseUsageStrip usage={usage} /> : null}
      {toolCallCount > 0 ? (
        <section aria-label="Tool calls detail" className="grid gap-2">
          <h3 className="text-sm font-semibold text-foreground">
            tool calls - {toolCallCount}
          </h3>
          <DataList>
            {response.tool_calls.map((call) => (
              <DataListItem
                className="grid gap-1"
                key={`${call.name}-${call.query}`}
              >
                <strong className="text-sm text-foreground">{call.name}</strong>
                <span className="text-sm text-muted-foreground">
                  {call.query ?? 'No query stored.'}
                </span>
                <small className="text-xs text-muted-foreground">
                  limit {call.limit ?? 'unknown'} /{' '}
                  {call.result_count ?? 'unknown'} results
                </small>
              </DataListItem>
            ))}
          </DataList>
        </section>
      ) : null}
      {sourceCount > 0 ? (
        <section aria-label="Sources detail" className="grid gap-2">
          <h3 className="text-sm font-semibold text-foreground">
            sources - {sourceCount}
          </h3>
          <DataList>
            {response.citations.map((result) => (
              <DataListItem
                className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
                key={result.chunk_id}
              >
                <div className="grid min-w-0 gap-2">
                  <strong className="break-words text-sm text-foreground">
                    {result.citation.source_external_id}
                  </strong>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {result.citation.snippet}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{result.citation.source_type} source</Badge>
                    <Badge>
                      version {result.citation.document_version_number}
                    </Badge>
                    <Badge>
                      chars {result.citation.char_start}-{result.citation.char_end}
                    </Badge>
                  </div>
                </div>
                <DataListItemActions className="justify-start md:justify-end">
                  <StatusBadge>score {formatScore(result.score)}</StatusBadge>
                  <Button
                    aria-label={`View source ${result.citation.source_external_id}`}
                    onClick={() =>
                      onOpenSource(
                        result.citation.source_id,
                        result.citation.snippet,
                      )
                    }
                    type="button"
                    variant="secondary"
                  >
                    View source
                  </Button>
                </DataListItemActions>
              </DataListItem>
            ))}
          </DataList>
        </section>
      ) : null}
    </div>
  )
}

function ResponseUsageStrip({ usage }: { usage: ResponseUsageSummary }) {
  return (
    <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
      {usage.model !== null ? (
        <UsageItem label="model" value={usage.model} />
      ) : null}
      {usage.provider !== null ? (
        <UsageItem label="provider" value={usage.provider} />
      ) : null}
      <UsageItem label="tokens" value={formatNullableTokens(usage.totalTokens)} />
      <UsageItem label="input" value={formatNullableTokenCount(usage.inputTokens)} />
      <UsageItem label="output" value={formatNullableTokenCount(usage.outputTokens)} />
      <UsageItem label="cost" value={formatNullableUsageCost(usage.costUsd)} />
    </dl>
  )
}

function UsageItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-semibold text-foreground">
        {value}
      </dd>
    </div>
  )
}

function KnowledgeDraftCard({
  draft,
  onCancel,
  onRefine,
  onSubmit,
  onTextChange,
}: {
  draft: ChatKnowledgeDraft
  onCancel(): void
  onRefine(): void
  onSubmit(): void
  onTextChange(text: string): void
}) {
  const canEdit = draft.status === 'draft'
  const canCancel = draft.status !== 'approved' && draft.status !== 'cancelled'
  const primaryAction =
    draft.reviewAction === 'approve' ? 'Approve knowledge' : 'Request approval'

  return (
    <article
      aria-label={`Knowledge draft ${draft.draftId}`}
      className="grid gap-3 rounded-md border border-border bg-card p-4 text-card-foreground"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="grid min-w-0 gap-1">
          <span className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
            Knowledge draft
          </span>
          <strong className="break-words text-sm text-foreground">
            {draft.scope}
          </strong>
        </div>
        <StatusBadge>{draft.status}</StatusBadge>
      </div>
      <Field>
        <FieldLabel htmlFor={`knowledge-draft-${draft.draftId}`}>
          Knowledge draft text
        </FieldLabel>
        <FieldControl>
          <Textarea
            aria-label="Knowledge draft text"
            disabled={!canEdit}
            id={`knowledge-draft-${draft.draftId}`}
            onChange={(event) => onTextChange(event.currentTarget.value)}
            rows={3}
            value={draft.text}
          />
        </FieldControl>
      </Field>
      {draft.proposalId === null ? null : (
        <p className="text-sm text-muted-foreground">Proposal {draft.proposalId}</p>
      )}
      {draft.error === null ? null : (
        <InlineFeedback tone="danger">{draft.error}</InlineFeedback>
      )}
      <div className="flex flex-wrap gap-2">
        <Button disabled={!canEdit} onClick={onSubmit} type="button">
          {primaryAction}
        </Button>
        <Button
          disabled={!canEdit}
          onClick={onRefine}
          type="button"
          variant="secondary"
        >
          Refine in chat
        </Button>
        <Button
          disabled={!canCancel}
          onClick={onCancel}
          type="button"
          variant="secondary"
        >
          Cancel draft
        </Button>
      </div>
    </article>
  )
}

function extractKnowledgeDrafts(toolCalls: ChatToolCall[]): ChatKnowledgeDraft[] {
  return toolCalls
    .map((call) => extractKnowledgeDraft(call))
    .filter((draft): draft is ChatKnowledgeDraft => draft !== null)
}

function extractKnowledgeDraft(call: ChatToolCall): ChatKnowledgeDraft | null {
  if (call.name !== 'commit_knowledge' && call.name !== 'refine_knowledge') {
    return null
  }
  const draftId = getJsonString(call.result_summary, 'draft_id')
  const summaryText = getJsonString(call.result_summary, 'proposed_text')
  const argumentText = getJsonString(call.arguments, 'knowledge_text')
  const text = summaryText ?? argumentText
  if (draftId === null || text === null) {
    return null
  }
  return {
    draftId,
    error: null,
    proposalId: getJsonString(call.result_summary, 'proposal_id'),
    reviewAction:
      getJsonString(call.result_summary, 'review_action') ?? 'request_approval',
    scope: getJsonString(call.result_summary, 'scope') ?? 'message',
    status: getJsonString(call.result_summary, 'status') ?? 'draft',
    text,
  }
}

function extractKnowledgeLifecycleEvents(
  toolCalls: ChatToolCall[],
): ChatKnowledgeLifecycleEvent[] {
  return toolCalls
    .map((call, index) => extractKnowledgeLifecycleEvent(call, index))
    .filter(
      (event): event is ChatKnowledgeLifecycleEvent => event !== null,
    )
}

function extractKnowledgeLifecycleEvent(
  call: ChatToolCall,
  index: number,
): ChatKnowledgeLifecycleEvent | null {
  const lifecycle = getJsonObject(call.result_summary, 'knowledge_lifecycle')
  const action =
    getJsonString(lifecycle, 'action') ?? knowledgeLifecycleAction(call.name)
  if (action !== 'approve' && action !== 'cancel') {
    return null
  }
  const draftId =
    getJsonString(lifecycle, 'draft_id') ??
    getJsonString(call.result_summary, 'draft_id') ??
    getJsonString(call.arguments, 'draft_id')
  const allPending =
    getJsonBoolean(lifecycle, 'all_pending') ||
    (call.name === 'cancel_knowledge' && draftId === null)
  if (draftId === null && !allPending) {
    return null
  }
  return {
    action,
    allPending,
    draftId,
    key: `${call.name}:${index}:${draftId ?? 'all'}`,
  }
}

function knowledgeLifecycleAction(name: string): 'approve' | 'cancel' | null {
  if (name === 'approve_knowledge') {
    return 'approve'
  }
  if (name === 'cancel_knowledge') {
    return 'cancel'
  }
  return null
}

function summarizeResponseUsage(
  steps: ChatStep[],
  providerUsage: ChatHistoryProviderUsage[],
): ResponseUsageSummary | null {
  const stepUsages = steps
    .map((step) => step.usage)
    .filter((usage): usage is NonNullable<ChatStep['usage']> => usage !== undefined)
  if (stepUsages.length > 0) {
    const lastUsage = stepUsages[stepUsages.length - 1]
    return {
      costUsd: sumOptionalNumbers(
        stepUsages.map((usage) => usage.estimated_cost_usd),
      ),
      inputTokens: sumOptionalNumbers(
        stepUsages.map((usage) => usage.input_tokens),
      ),
      model: lastUsage.model,
      outputTokens: sumOptionalNumbers(
        stepUsages.map((usage) => usage.output_tokens),
      ),
      provider: lastUsage.provider,
      totalTokens: sumOptionalNumbers(
        stepUsages.map((usage) => usage.total_tokens),
      ),
    }
  }

  if (providerUsage.length === 0) {
    return null
  }

  const firstUsage = providerUsage[0]
  return {
    costUsd: sumOptionalNumbers(
      providerUsage.map((usage) => usage.estimated_cost_usd),
    ),
    inputTokens: sumOptionalNumbers(
      providerUsage.map((usage) => usage.input_tokens),
    ),
    model: firstUsage?.model ?? null,
    outputTokens: sumOptionalNumbers(
      providerUsage.map((usage) => usage.output_tokens),
    ),
    provider: firstUsage?.provider ?? null,
    totalTokens: sumOptionalNumbers(
      providerUsage.map((usage) => usage.total_tokens),
    ),
  }
}

function sumOptionalNumbers(values: Array<number | null | undefined>): number | null {
  const knownValues = values.filter(
    (value): value is number => value !== null && value !== undefined,
  )
  if (knownValues.length === 0) {
    return null
  }
  return knownValues.reduce((total, value) => total + value, 0)
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

function getJsonBoolean(value: unknown, key: string): boolean {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return false
  }

  return (value as Record<string, unknown>)[key] === true
}

function getJsonObject(
  value: unknown,
  key: string,
): Record<string, unknown> | null {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return null
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return nextValue !== null &&
    typeof nextValue === 'object' &&
    !Array.isArray(nextValue)
    ? (nextValue as Record<string, unknown>)
    : null
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Request failed.'
}

function formatScore(score: number): string {
  return score.toFixed(2)
}

function formatNullableUsageCost(value: number | null): string {
  return value === null ? 'unknown cost' : formatUsd(value)
}

function formatNullableTokens(value: number | null): string {
  return value === null ? 'unknown tokens' : `${formatNumber(value)} tokens`
}

function formatNullableTokenCount(value: number | null): string {
  return value === null ? 'unknown' : formatNumber(value)
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`
}

function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value)
}

function formatCount(value: number, singularLabel: string): string {
  if (value === 1) {
    return `1 ${singularLabel}`
  }
  return `${formatNumber(value)} ${singularLabel}s`
}

function ContextRingIcon() {
  return (
    <svg
      aria-hidden="true"
      className="ui-icon context-ring-icon"
      focusable="false"
      viewBox="0 0 24 24"
    >
      <circle className="context-ring-track" cx="12" cy="12" r="8" />
      <path className="context-ring-fill" d="M12 4a8 8 0 0 1 7.6 5.5" />
      <circle cx="12" cy="12" r="2.8" />
    </svg>
  )
}

function MinimapIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <rect height="14" rx="2" width="14" x="5" y="5" />
      <path d="M8 9h3M8 12h5M8 15h2M15 9h1M15 15h1" />
    </svg>
  )
}

function TranscriptIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      {active ? (
        <rect height="10" rx="1.5" width="10" x="7" y="7" />
      ) : (
        <>
          <path d="M12 5a3 3 0 0 0-3 3v4a3 3 0 0 0 6 0V8a3 3 0 0 0-3-3Z" />
          <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
        </>
      )}
    </svg>
  )
}

function SendIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="m5 12 14-7-5 14-3-6-6-1Z" />
      <path d="m11 13 8-8" />
    </svg>
  )
}
