import {
  type Dispatch,
  type FormEvent,
  type KeyboardEvent,
  type Ref,
  type SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Copy,
  Map as MapIcon,
  Mic,
  RefreshCw,
  Square,
} from 'lucide-react'

import { ChatPipelineSteps } from '@/components/ChatPipelineSteps'
import { MarkdownAnswer } from '@/components/MarkdownAnswer'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { Callout, EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldLabel } from '@/components/ui/field'
import { Panel } from '@/components/ui/panel'
import type {
  ChatHistoryProviderUsage,
  ChatResponseBody,
  ChatToolCall,
  KnowledgeProposal,
  UserMemory,
} from '@/lib/apiClient'
import type { ChatStep } from '@/lib/chatSteps'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import { cn } from '@/lib/utils'

/** Compact circular tool control — beflow-style dock chrome. */
const COMPOSER_TOOL_BUTTON_CLASS =
  'size-auto shrink-0 rounded-full border border-border bg-card p-1.5 text-muted-foreground shadow-sm hover:bg-primary/15 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background max-[680px]:min-h-11 max-[680px]:min-w-11 max-[680px]:p-0.5'

const COMPOSER_PRIMARY_ACTION_CLASS =
  'shrink-0 rounded-md px-3 py-1.5 text-xs font-semibold sm:px-4 max-[680px]:min-h-11 max-[680px]:w-full max-[680px]:px-4'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type ChatKnowledgeDraftAction = 'approve' | 'request_approval' | string
export type ChatKnowledgeDraftStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'cancelled'
  | string
export type ChatKnowledgeDraft = {
  approvedSourceId: string | null
  draftId: string
  error: string | null
  /** Latest known ingestion job status for the approved source, if any. */
  ingestStatus: string | null
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

/** Prior multi-turn Q/A already stored for the selected session. */
export type ChatTranscriptTurn = {
  answer: string
  citations: ChatResponseBody['citations']
  id: string
  question: string
  steps: ChatResponseBody['steps']
  tool_calls: ChatResponseBody['tool_calls']
}

export type ChatWorkspacePanelProps = {
  activeResponseQuestion: string | null
  appliedMemories?: UserMemory[]
  /** When set, follow-ups continue this multi-turn session. */
  continuingSessionId?: string | null
  drafts: ChatKnowledgeDraftMap
  /** Elapsed ms from last SSE heartbeat while a request is in flight. */
  heartbeatElapsedMs?: number | null
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
  /** Re-run the last succeeded answer without archiving it into prior turns. */
  onRegenerateLastAnswer?(): void
  /** Resend the last failed/canceled question without retyping. */
  onRetryLastQuestion?(): void
  onStartNewSession?(): void
  /** Load a prior/current user question into the composer (optional fork of later turns). */
  onEditQuestion?(text: string, turnId?: string): void
  onStartSpeechRecognition(): void
  onStopSpeechRecognition(): void
  onSubmit(event: FormEvent<HTMLFormElement>): void
  onSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal>
  onTranscriptScroll?: () => void
  /** Earlier turns in the selected session (newest last). */
  priorTurns?: ChatTranscriptTurn[]
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
  appliedMemories = [],
  continuingSessionId = null,
  drafts,
  heartbeatElapsedMs = null,
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
  onRegenerateLastAnswer,
  onRetryLastQuestion,
  onStartNewSession,
  onEditQuestion,
  onStartSpeechRecognition,
  onStopSpeechRecognition,
  onSubmit,
  onSubmitKnowledgeDraft,
  onTranscriptScroll,
  priorTurns = [],
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
  const questionInputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (question.length > 0) {
      return
    }
    const el = questionInputRef.current
    if (el !== null) {
      el.style.height = ''
    }
  }, [question])

  return (
    <Panel
      aria-label="Chat Workspace"
      className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] border-0 bg-transparent shadow-none"
      role="region"
    >
      {/* Transcript + composer are direct grid children so the form pins bottom. */}
      <div
        aria-busy={isAsking || requestState === 'loading' || undefined}
        aria-label="Chat Transcript"
        className="min-h-0 overflow-y-auto px-0.5 pr-1"
        data-slot="chat-transcript"
        onScroll={onTranscriptScroll}
        ref={transcriptRef}
        role="region"
      >
        <div className="grid gap-4 max-[680px]:gap-3">
          {priorTurns.map((turn) => (
            <ResponseContent
              key={turn.id}
              appliedMemories={[]}
              drafts={{}}
              onEditQuestion={
                onEditQuestion === undefined
                  ? undefined
                  : (text) => onEditQuestion(text, turn.id)
              }
              onOpenSource={onOpenSource}
              onRefineKnowledgeDraft={onRefineKnowledgeDraft}
              onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
              providerUsage={[]}
              question={turn.question}
              response={{
                answer: turn.answer,
                citations: turn.citations,
                session_id: continuingSessionId,
                steps: turn.steps,
                tool_calls: turn.tool_calls,
              }}
              setDrafts={setDrafts}
              state="succeeded"
            />
          ))}
          <ResponsePanel
            appliedMemories={appliedMemories}
            drafts={drafts}
            errorDetail={requestError}
            heartbeatElapsedMs={heartbeatElapsedMs}
            onEditQuestion={onEditQuestion}
            onOpenSource={onOpenSource}
            onQuestionChange={onQuestionChange}
            onRefineKnowledgeDraft={onRefineKnowledgeDraft}
            onRegenerateLastAnswer={onRegenerateLastAnswer}
            onRetryLastQuestion={onRetryLastQuestion}
            onStartNewSession={onStartNewSession}
            onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
            providerUsage={providerUsage}
            question={activeResponseQuestion}
            response={response}
            setDrafts={setDrafts}
            state={requestState}
          />
        </div>
      </div>

      <div
        className={cn(
          'relative shrink-0 bg-background',
          // Keep Ask docked above the fold on narrow shells / soft keyboards.
          'max-[680px]:sticky max-[680px]:bottom-0 max-[680px]:z-20',
          'max-[680px]:border-t max-[680px]:border-primary/70',
          // Purple hairline above sticky Ask dock (mirrors question sticky).
          'max-[680px]:shadow-[0_-1px_0_0] max-[680px]:shadow-primary/65',
          'max-[680px]:pb-[max(0.25rem,env(safe-area-inset-bottom))]',
        )}
        data-slot="chat-composer-shell"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-8 h-8 bg-gradient-to-b from-background/0 via-background/80 to-background max-[680px]:-top-5 max-[680px]:h-5"
          data-slot="chat-composer-gradient"
        />
        <form
          className="relative mx-auto w-full max-w-3xl px-1 pb-3 pt-1 sm:px-2 sm:pb-4 max-[680px]:px-1 max-[680px]:pb-1.5 max-[680px]:pt-1"
          data-slot="chat-composer"
          id="chat-composer"
          onSubmit={onSubmit}
          tabIndex={-1}
        >
          {continuingSessionId ? (
            <div
              aria-label="Continuing thread"
              className="mb-1.5 flex min-w-0 items-center gap-2 max-[680px]:mb-1 max-[680px]:gap-1.5"
              data-slot="chat-session-continuity"
              role="status"
            >
              <StatusBadge className="shrink-0" tone="primary">
                Continuing thread
              </StatusBadge>
              <span
                className="min-w-0 truncate font-mono text-[11px] text-muted-foreground max-[680px]:text-xs"
                title={continuingSessionId}
              >
                {shortSessionId(continuingSessionId)}
              </span>
              <ContextWindowChip
                priorTurnCount={priorTurns.length}
                steps={response?.steps ?? []}
              />
              {onStartNewSession !== undefined ? (
                <Button
                  className="ml-auto h-7 px-2 text-[11px]"
                  data-slot="chat-start-new-thread"
                  onClick={onStartNewSession}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  New thread
                </Button>
              ) : null}
            </div>
          ) : null}
          <Field className="gap-0">
            <FieldLabel className="sr-only" htmlFor="chat-question">
              Question
            </FieldLabel>
            <FieldControl className="gap-0">
              <Textarea
                className={cn(
                  'max-h-48 min-h-[3.5rem] w-full resize-none overflow-y-auto rounded-xl border-border bg-muted/15 px-4 py-2.5 text-sm leading-relaxed max-[680px]:min-h-11 max-[680px]:text-base',
                  'placeholder:text-muted-foreground',
                  'focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                )}
                id="chat-question"
                name="question"
                onChange={(event) => {
                  const el = event.currentTarget
                  onQuestionChange(el.value)
                  el.style.height = 'auto'
                  el.style.height = `${Math.min(el.scrollHeight, 192)}px`
                }}
                onInput={(event) => {
                  const el = event.currentTarget
                  el.style.height = 'auto'
                  el.style.height = `${Math.min(el.scrollHeight, 192)}px`
                }}
                onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
                  if (event.key === 'Escape' && isAsking) {
                    event.preventDefault()
                    onCancelRequest()
                    return
                  }
                  if (
                    event.key === 'Enter' &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault()
                    if (isAsking || question.trim().length === 0) {
                      return
                    }
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
                placeholder="Ask a question about indexed sources"
                ref={questionInputRef}
                rows={2}
                title="Enter to send · Shift+Enter for a new line · Escape to cancel"
                value={question}
              />
            </FieldControl>
          </Field>

          <div
            className="mt-2 flex flex-wrap items-center justify-between gap-2 max-[680px]:mt-1.5 max-[680px]:gap-1.5"
            data-slot="chat-composer-actions"
          >
            <p
              className="order-last w-full text-[11px] leading-snug text-muted-foreground sm:order-none sm:w-auto max-[680px]:text-xs"
              data-slot="chat-composer-shortcuts"
            >
              <ComposerShortcutHint keys="Enter" label="Send" />
              <span aria-hidden="true" className="mx-1.5 text-border">
                ·
              </span>
              <ComposerShortcutHint keys="⇧Enter" label="New line" />
              {isAsking ? (
                <>
                  <span aria-hidden="true" className="mx-1.5 text-border">
                    ·
                  </span>
                  <ComposerShortcutHint keys="Esc" label="Cancel" />
                </>
              ) : null}
            </p>
            <div className="ml-auto flex min-w-0 flex-wrap items-center justify-end gap-1.5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:gap-1">
              <div className="flex min-w-0 flex-wrap items-center gap-1.5 max-[680px]:gap-1">
                <Button
                  aria-label="Open Context Sidebar"
                  aria-pressed={isContextInspectorActive}
                  className={cn(
                    COMPOSER_TOOL_BUTTON_CLASS,
                    isContextInspectorActive &&
                      'border-primary bg-primary/25 text-foreground',
                  )}
                  onClick={onOpenContextInspector}
                  type="button"
                  variant="ghost"
                >
                  <CircleDot aria-hidden="true" className="size-4" />
                </Button>
                <Button
                  aria-label="Open Minimap Sidebar"
                  aria-pressed={isMinimapInspectorActive}
                  className={cn(
                    COMPOSER_TOOL_BUTTON_CLASS,
                    isMinimapInspectorActive &&
                      'border-primary bg-primary/25 text-foreground',
                  )}
                  onClick={onOpenMinimapInspector}
                  type="button"
                  variant="ghost"
                >
                  <MapIcon aria-hidden="true" className="size-4" />
                </Button>
                <SpeechInputControl
                  feedback={speechFeedback}
                  isSupported={isSpeechSupported}
                  onStart={onStartSpeechRecognition}
                  onStop={onStopSpeechRecognition}
                  state={speechState}
                />
              </div>

              {isAsking ? (
                <Button
                  className={cn(
                    COMPOSER_PRIMARY_ACTION_CLASS,
                    'border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive',
                  )}
                  onClick={onCancelRequest}
                  size="sm"
                  type="button"
                  variant="secondary"
                >
                  Cancel Request
                </Button>
              ) : (
                <Button
                  aria-label="Ask"
                  className={COMPOSER_PRIMARY_ACTION_CLASS}
                  disabled={question.trim().length === 0}
                  size="sm"
                  title="Enter to send"
                  type="submit"
                >
                  Ask
                </Button>
              )}
            </div>
          </div>

          {/* Error detail is co-located with the transcript failure/cancel state
              (see ResponsePanel). Avoid a second under-composer callout. */}
        </form>
      </div>
    </Panel>
  )
}

function ContextWindowChip({
  priorTurnCount,
  steps,
}: {
  priorTurnCount: number
  steps: ChatResponseBody['steps']
}) {
  const contextStep = (steps ?? []).find((step) => step.id === 'context')
  const detail = contextStep?.detail
  const summarized =
    detail !== null &&
    detail !== undefined &&
    typeof detail === 'object' &&
    'summarized_messages' in detail &&
    typeof (detail as { summarized_messages: unknown }).summarized_messages ===
      'number'
      ? (detail as { summarized_messages: number }).summarized_messages
      : 0
  const kept =
    detail !== null &&
    detail !== undefined &&
    typeof detail === 'object' &&
    'kept_recent' in detail &&
    typeof (detail as { kept_recent: unknown }).kept_recent === 'number'
      ? (detail as { kept_recent: number }).kept_recent
      : null
  const total =
    detail !== null &&
    detail !== undefined &&
    typeof detail === 'object' &&
    'total_messages' in detail &&
    typeof (detail as { total_messages: unknown }).total_messages === 'number'
      ? (detail as { total_messages: number }).total_messages
      : priorTurnCount * 2
  if (total <= 0 && priorTurnCount <= 0) {
    return null
  }
  const label =
    summarized > 0
      ? `Context: ${kept ?? 'recent'} recent + ${summarized} summarized`
      : `Context: ${total > 0 ? total : priorTurnCount * 2} messages`
  return (
    <span
      className="truncate text-[11px] text-muted-foreground max-[680px]:text-xs"
      data-slot="chat-context-window"
      title={
        detail !== null &&
        detail !== undefined &&
        typeof detail === 'object' &&
        'summary_preview' in detail &&
        typeof (detail as { summary_preview: unknown }).summary_preview ===
          'string'
          ? (detail as { summary_preview: string }).summary_preview
          : label
      }
    >
      {label}
    </span>
  )
}

function ComposerShortcutHint({
  keys,
  label,
}: {
  keys: string
  label: string
}) {
  return (
    <span className="inline-flex items-center gap-1">
      <kbd className="rounded border border-border bg-muted/40 px-1 py-px font-mono text-[10px] font-medium text-foreground/80 max-[680px]:text-[11px]">
        {keys}
      </kbd>
      <span>{label}</span>
    </span>
  )
}

function shortSessionId(sessionId: string): string {
  if (sessionId.length <= 12) {
    return sessionId
  }
  return sessionId.slice(0, 8)
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
    ? 'Transcript Unavailable'
    : isListening
      ? 'Stop Transcript'
      : 'Start Transcript'
  // Idle "Speech input ready." crowded the toolbar — only show status when useful.
  const showStatus =
    feedback !== null ||
    state === 'failed' ||
    state === 'loading' ||
    !isSupported
  const message =
    feedback ??
    (isListening
      ? 'Listening…'
      : isSupported
        ? null
        : 'Speech recognition is not supported in this browser.')

  return (
    <section
      aria-label="Transcript Input"
      className="flex min-w-0 flex-wrap items-center gap-1.5 max-[680px]:w-full max-[680px]:gap-0.5"
      data-slot="speech-input"
    >
      <Button
        aria-label={buttonLabel}
        className={cn(
          COMPOSER_TOOL_BUTTON_CLASS,
          isListening && 'border-primary bg-primary/25 text-foreground',
        )}
        disabled={!isSupported}
        onClick={isListening ? onStop : onStart}
        title={buttonLabel}
        type="button"
        variant="ghost"
      >
        {isListening ? (
          <Square aria-hidden="true" className="size-4" />
        ) : (
          <Mic aria-hidden="true" className="size-4" />
        )}
      </Button>
      {showStatus && message !== null ? (
        <InlineFeedback
          className={cn(
            'min-w-0 text-xs',
            // Desktop: compact chip beside mic. Mobile: full-width row under tools.
            'max-w-48 truncate max-[680px]:order-last max-[680px]:w-full max-[680px]:max-w-none',
            'max-[680px]:basis-full max-[680px]:whitespace-normal max-[680px]:break-words',
          )}
          data-slot="speech-status"
          role={state === 'failed' ? 'alert' : 'status'}
          title={message}
          tone={state === 'failed' ? 'danger' : 'neutral'}
        >
          {message}
        </InlineFeedback>
      ) : null}
    </section>
  )
}

const SAMPLE_QUESTIONS = [
  'What is the release mascot?',
  'What is the project codename?',
  'Which sources cover deployment?',
] as const

function ResponsePanel({
  appliedMemories,
  drafts,
  errorDetail = null,
  heartbeatElapsedMs = null,
  onEditQuestion,
  onOpenSource,
  onQuestionChange,
  onRefineKnowledgeDraft,
  onRegenerateLastAnswer,
  onRetryLastQuestion,
  onStartNewSession,
  onSubmitKnowledgeDraft,
  providerUsage,
  question,
  response,
  setDrafts,
  state,
}: {
  appliedMemories: UserMemory[]
  drafts: ChatKnowledgeDraftMap
  errorDetail?: string | null
  heartbeatElapsedMs?: number | null
  onEditQuestion?(text: string, turnId?: string): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onQuestionChange?(value: string): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onRegenerateLastAnswer?(): void
  onRetryLastQuestion?(): void
  onStartNewSession?(): void
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
          appliedMemories={appliedMemories}
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
    const elapsedSeconds =
      heartbeatElapsedMs !== null && heartbeatElapsedMs >= 10_000
        ? Math.round(heartbeatElapsedMs / 1000)
        : null
    return (
      <div
        aria-live="polite"
        className="grid min-h-[8rem] place-items-center px-3 py-6 max-[680px]:min-h-[6rem] max-[680px]:px-2 max-[680px]:py-4"
      >
        <EmptyState
          aria-busy="true"
          className="w-full max-w-lg border-border/60 bg-muted/15 p-5 text-center max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-relaxed max-[680px]:tracking-tight"
          data-slot-state="loading"
          role="status"
        >
          <p className="font-medium text-foreground/90 max-[680px]:text-sm max-[680px]:leading-snug">
            Waiting for response…
          </p>
          <p
            className="text-xs text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug"
            data-slot="chat-stall-indicator"
          >
            {elapsedSeconds === null
              ? 'Connecting and retrieving sources…'
              : `Still working on the provider — ${elapsedSeconds}s`}
          </p>
          <div
            aria-hidden="true"
            className="space-y-3 rounded-lg border border-border/60 bg-card p-4 text-left max-[680px]:space-y-2 max-[680px]:rounded-md max-[680px]:border-border/70 max-[680px]:p-3"
          >
            <div className="h-2.5 w-1/3 motion-safe:animate-pulse rounded-full bg-muted/40" />
            <div className="space-y-2 max-[680px]:space-y-1.5">
              <div className="h-3 motion-safe:animate-pulse rounded bg-muted/40" />
              <div className="h-3 w-11/12 motion-safe:animate-pulse rounded bg-muted/40" />
              <div className="h-3 w-4/5 motion-safe:animate-pulse rounded bg-muted/40" />
              <div className="h-3 w-2/3 motion-safe:animate-pulse rounded bg-muted/40" />
            </div>
            <div className="flex gap-1.5 pt-1 max-[680px]:gap-1.5 max-[680px]:pt-1">
              <div className="h-5 w-16 motion-safe:animate-pulse rounded-full bg-muted/40" />
              <div className="h-5 w-20 motion-safe:animate-pulse rounded-full bg-muted/40" />
              <div className="h-5 w-14 motion-safe:animate-pulse rounded-full bg-muted/40" />
            </div>
          </div>
        </EmptyState>
      </div>
    )
  }

  if (response === null) {
    if (state === 'failed') {
      const failedDetail =
        errorDetail !== null && errorDetail.trim().length > 0
          ? operatorSafeMessage(errorDetail)
          : 'Transient provider errors are often fixable with retry.'
      return (
        <div className="grid min-h-[8rem] place-items-center px-3 py-6 max-[680px]:min-h-[6rem] max-[680px]:px-2 max-[680px]:py-4">
          <EmptyState
            className="max-w-md border-destructive/30 bg-destructive/5 p-5 text-left max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-relaxed max-[680px]:tracking-tight"
            data-slot-state="failed"
            role="alert"
          >
            <p className="font-medium text-destructive max-[680px]:text-sm max-[680px]:leading-snug">
              Request failed
            </p>
            <p
              className="text-xs leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug"
              data-slot="chat-error-detail"
            >
              {failedDetail}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {onRetryLastQuestion !== undefined && question !== null ? (
                <Button
                  data-slot="chat-retry"
                  onClick={onRetryLastQuestion}
                  type="button"
                  variant="secondary"
                >
                  Try again
                </Button>
              ) : null}
              {onStartNewSession !== undefined ? (
                <Button
                  data-slot="chat-start-new-on-error"
                  onClick={onStartNewSession}
                  type="button"
                  variant="ghost"
                >
                  New thread
                </Button>
              ) : null}
            </div>
          </EmptyState>
        </div>
      )
    }
    if (state === 'canceled') {
      return (
        <div className="grid min-h-[8rem] place-items-center px-3 py-6 max-[680px]:min-h-[6rem] max-[680px]:px-2 max-[680px]:py-4">
          <EmptyState
            className="max-w-md border-border/60 bg-muted/15 p-5 text-left max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-relaxed max-[680px]:tracking-tight"
            data-slot-state="canceled"
            role="status"
          >
            <p className="font-medium text-foreground/90 max-[680px]:text-sm max-[680px]:leading-snug">
              Request canceled
            </p>
            <p className="text-xs leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug">
              The session stays open so you can continue the thread. The
              canceled turn is marked failed in history when it was started.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {onRetryLastQuestion !== undefined && question !== null ? (
                <Button
                  data-slot="chat-retry"
                  onClick={onRetryLastQuestion}
                  type="button"
                  variant="secondary"
                >
                  Try again
                </Button>
              ) : null}
              {onStartNewSession !== undefined ? (
                <Button
                  onClick={onStartNewSession}
                  type="button"
                  variant="ghost"
                >
                  New thread
                </Button>
              ) : null}
            </div>
          </EmptyState>
        </div>
      )
    }
    return (
      <div className="grid min-h-[8rem] place-items-center px-3 py-6 max-[680px]:min-h-[6rem] max-[680px]:px-2 max-[680px]:py-4">
        <EmptyState
          className="max-w-md border-border/60 bg-muted/15 p-5 max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-relaxed max-[680px]:tracking-tight"
          data-slot-state="empty"
          role="status"
        >
          <p className="font-medium text-foreground/90 max-[680px]:text-sm max-[680px]:leading-snug">
            No response yet
          </p>
          <p className="text-xs leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug">
            Ask about indexed sources. Enter to send · Shift+Enter for a new
            line.
          </p>
          {onQuestionChange !== undefined ? (
            <div
              className="mt-3 flex flex-wrap justify-center gap-1.5"
              data-slot="chat-sample-questions"
            >
              {SAMPLE_QUESTIONS.map((sample) => (
                <Button
                  key={sample}
                  className="h-auto max-w-full whitespace-normal rounded-full px-2.5 py-1 text-[11px]"
                  onClick={() => onQuestionChange(sample)}
                  size="sm"
                  type="button"
                  variant="secondary"
                >
                  {sample}
                </Button>
              ))}
            </div>
          ) : null}
        </EmptyState>
      </div>
    )
  }

  const failedBannerDetail =
    errorDetail !== null && errorDetail.trim().length > 0
      ? operatorSafeMessage(errorDetail)
      : null
  const terminalBanner =
    state === 'failed' || state === 'canceled' ? (
      <div data-slot="chat-terminal-banner" data-slot-state={state}>
        <Callout
          className="mx-0.5"
          role={state === 'failed' ? 'alert' : 'status'}
          tone={state === 'failed' ? 'danger' : 'neutral'}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span data-slot="chat-error-detail">
              {state === 'failed'
                ? (failedBannerDetail ??
                  'Request failed. Partial answer below may be incomplete.')
                : 'Stopped — partial answer below may be incomplete. You can retry or continue.'}
            </span>
            {onRetryLastQuestion !== undefined ? (
              <Button
                data-slot="chat-retry"
                onClick={onRetryLastQuestion}
                size="sm"
                type="button"
                variant="secondary"
              >
                Try again
              </Button>
            ) : null}
          </div>
        </Callout>
      </div>
    ) : null

  return (
    <div className="grid gap-3 max-[680px]:gap-2">
      {terminalBanner}
      <ResponseContent
        appliedMemories={appliedMemories}
        drafts={drafts}
        onEditQuestion={
          state === 'loading' || onEditQuestion === undefined
            ? undefined
            : (text) => onEditQuestion(text)
        }
        onOpenSource={onOpenSource}
        onRefineKnowledgeDraft={onRefineKnowledgeDraft}
        onRegenerateLastAnswer={
          state === 'succeeded' ? onRegenerateLastAnswer : undefined
        }
        onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
        providerUsage={providerUsage}
        question={question}
        response={response}
        setDrafts={setDrafts}
        state={state}
      />
    </div>
  )
}

function ResponseContent({
  appliedMemories,
  drafts,
  onEditQuestion,
  onOpenSource,
  onRefineKnowledgeDraft,
  onRegenerateLastAnswer,
  onSubmitKnowledgeDraft,
  providerUsage,
  question,
  response,
  setDrafts,
  state,
}: {
  appliedMemories: UserMemory[]
  drafts: ChatKnowledgeDraftMap
  onEditQuestion?(text: string): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onRegenerateLastAnswer?(): void
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

  const inFlightDraftSubmits = useRef<Set<string>>(new Set())

  const handleSubmitDraft = useCallback(
    async (draft: ChatKnowledgeDraft) => {
      if (inFlightDraftSubmits.current.has(draft.draftId)) {
        return
      }
      if (
        draft.status === 'approved' ||
        draft.status === 'cancelled' ||
        draft.status === 'rejected'
      ) {
        return
      }
      inFlightDraftSubmits.current.add(draft.draftId)
      setDrafts((current) => ({
        ...current,
        [draft.draftId]: {
          ...current[draft.draftId],
          error: null,
          status: 'pending',
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
            approvedSourceId: proposal.approved_source_id,
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
            status: current[draft.draftId]?.status ?? draft.status,
          },
        }))
      } finally {
        inFlightDraftSubmits.current.delete(draft.draftId)
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
      // Durable chat commits start as pending; auto-approve still allowed once.
      if (
        draft === undefined ||
        (draft.status !== 'draft' && draft.status !== 'pending')
      ) {
        continue
      }
      if (draft.reviewAction !== 'approve') {
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
    <div aria-label="Chat Response" className="grid gap-4 max-[680px]:gap-2" role="region">
      <QuestionPrompt
        key={question ?? 'empty-question'}
        onEdit={
          onEditQuestion !== undefined &&
          !isStreaming &&
          question !== null &&
          question.trim().length > 0
            ? () => onEditQuestion(question)
            : undefined
        }
        question={question}
      />

      {response.answer.trim().length > 0 || !isStreaming ? (
        <article
          className="rounded-lg border border-border bg-card p-3.5 text-card-foreground tracking-tight focus-within:border-primary max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-3 max-[680px]:shadow-none"
          data-slot="chat-message"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2 max-[680px]:mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:text-xs">
              Answer
            </span>
            {isStreaming ? (
              <StatusBadge className="w-fit" tone="primary">
                Streaming
              </StatusBadge>
            ) : null}
            <div className="ml-auto flex items-center gap-1">
              {response.answer.trim().length > 0 ? (
                <CopyAnswerButton text={response.answer} />
              ) : null}
              {onRegenerateLastAnswer !== undefined &&
              !isStreaming &&
              question !== null &&
              question.trim().length > 0 ? (
                <Button
                  aria-label="Regenerate answer"
                  className="h-7 gap-1 px-2 text-[11px]"
                  onClick={onRegenerateLastAnswer}
                  size="sm"
                  slotName="chat-regenerate"
                  type="button"
                  variant="ghost"
                >
                  <RefreshCw aria-hidden="true" className="size-3.5" />
                  Regenerate
                </Button>
              ) : null}
            </div>
          </div>
          {response.answer.trim().length > 0 ? (
            <MarkdownAnswer
              onCitationClick={(ordinal) => {
                const citation = response.citations[ordinal - 1]
                if (citation === undefined) {
                  return
                }
                onOpenSource(
                  citation.citation.source_id,
                  citation.citation.snippet,
                )
              }}
            >
              {response.answer}
            </MarkdownAnswer>
          ) : (
            <p className="text-sm leading-relaxed tracking-tight text-muted-foreground">
              <span className="inline-flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="size-1.5 rounded-full bg-muted-foreground motion-safe:animate-pulse"
                />
                Drafting answer…
              </span>
            </p>
          )}
          {!isStreaming &&
          response.answer.trim().length > 0 &&
          response.citations.length === 0 ? (
            <Callout
              className="mt-3"
              data-slot="chat-no-sources"
              role="status"
              tone="neutral"
            >
              No sources cited. The answer may be general knowledge or retrieval
              returned nothing useful — verify before trusting project claims.
            </Callout>
          ) : null}
          {response.citations.length > 0 ? (
            <div
              aria-label="Answer Citations"
              className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-2.5 max-[680px]:mt-2.5 max-[680px]:gap-1.5 max-[680px]:pt-2"
              data-slot="chat-answer-citations"
              role="group"
            >
              {response.citations.map((citation, index) => {
                const ordinal = index + 1
                const label =
                  citation.citation.source_external_id ||
                  citation.citation.source_id ||
                  `Source ${ordinal}`
                const snippet = citation.citation.snippet?.trim() ?? ''
                const chipKey = [
                  citation.chunk_id ?? 'no-chunk',
                  citation.citation.source_id ?? 'no-source',
                  index,
                ].join('-')
                return (
                  <Button
                    aria-label={`Open Source ${label}`}
                    className={cn(
                      'h-auto max-w-full gap-1.5 truncate rounded-full px-2.5 py-1 text-[11px] font-medium',
                      'hover:border-primary/50 hover:bg-primary/15',
                      'max-[680px]:min-h-11 max-[680px]:rounded-md max-[680px]:px-2.5 max-[680px]:py-1 max-[680px]:text-xs',
                    )}
                    key={chipKey}
                    onClick={() =>
                      onOpenSource(
                        citation.citation.source_id,
                        citation.citation.snippet,
                      )
                    }
                    size="sm"
                    title={snippet.length > 0 ? `${label} — ${snippet}` : label}
                    type="button"
                    variant="secondary"
                  >
                    <span
                      aria-hidden="true"
                      className="inline-flex size-4 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-semibold tabular-nums text-foreground"
                    >
                      {ordinal}
                    </span>
                    <span className="min-w-0 truncate">{label}</span>
                  </Button>
                )
              })}
            </div>
          ) : null}
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

      {appliedMemories.length > 0 ? (
        <section
          aria-label="Memory Applied"
          className="grid gap-2 rounded-md border border-border/80 bg-muted/20 p-3 max-[680px]:gap-1.5 max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-2.5 max-[680px]:shadow-none"
          data-slot="chat-memory-applied"
        >
          <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-1.5">
            <StatusBadge className="w-fit" tone="success">
              Memory Applied
            </StatusBadge>
            <span className="text-xs text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug">
              {appliedMemories.length} approved item
              {appliedMemories.length === 1 ? '' : 's'} injected as system
              context (not a user turn).
            </span>
          </div>
          <ul className="grid gap-1.5 max-[680px]:gap-1.5">
            {appliedMemories.map((memory) => (
              <li
                className="text-sm leading-relaxed tracking-tight text-foreground max-[680px]:text-sm max-[680px]:leading-relaxed"
                key={memory.id}
              >
                {memory.content}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {knowledgeDrafts.length === 0 ? null : (
        <section aria-label="Knowledge Drafts" className="grid gap-3 max-[680px]:gap-2">
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

function QuestionPrompt({
  onEdit,
  question,
}: {
  onEdit?(): void
  question: string | null
}) {
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
    <div
      className="sticky top-0 z-10 border-b border-border bg-background/95 pb-2 backdrop-blur-sm shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:border-border max-[680px]:pb-1.5 max-[680px]:shadow-border/80"
      data-slot="chat-question-sticky"
    >
      <div className="mb-1 flex items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:text-xs">
          Your question
        </p>
        {onEdit !== undefined ? (
          <Button
            aria-label="Edit question"
            className="ml-auto h-7 px-2 text-[11px]"
            data-slot="chat-edit-question"
            onClick={onEdit}
            size="sm"
            type="button"
            variant="ghost"
          >
            Edit
          </Button>
        ) : null}
      </div>
      {shouldCollapse ? (
        <Button
          aria-expanded={expanded}
          aria-label={expanded ? 'Collapse full question' : 'Expand full question'}
          className="max-w-full justify-start whitespace-normal text-left max-[680px]:min-h-11 max-[680px]:text-sm"
          onClick={() => setExpanded((current) => !current)}
          title={trimmedQuestion}
          type="button"
          variant="secondary"
        >
          {displayQuestion}
        </Button>
      ) : (
        <p className="rounded-md border border-border bg-muted/15 px-3 py-2 text-sm leading-relaxed text-foreground max-[680px]:rounded-md max-[680px]:border-border max-[680px]:px-2.5 max-[680px]:py-2 max-[680px]:text-sm max-[680px]:leading-relaxed max-[680px]:shadow-none">
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
    formatCount(sourceCount, 'Source'),
    formatCount(toolCallCount, 'Tool Call'),
  ]
  if (usage !== null) {
    summaryParts.push('Usage')
  }

  return (
    <section
      aria-label="Response Details"
      className="rounded-md border border-border bg-muted/15 p-3 max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-2 max-[680px]:shadow-none"
    >
      <Button
        aria-expanded={expanded}
        aria-label={expanded ? 'Collapse Response Details' : 'Expand Response Details'}
        className="h-auto w-full min-w-0 justify-start gap-2 px-2 py-2 text-left max-[680px]:min-h-11 max-[680px]:gap-2 max-[680px]:text-sm"
        onClick={() => setExpanded((current) => !current)}
        type="button"
        variant="secondary"
      >
        {expanded ? (
          <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="min-w-0 truncate">
          Details · {summaryParts.join(' · ')}
        </span>
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
    <div
      className={
        embedded
          ? 'grid gap-3 pt-2 max-[680px]:gap-2 max-[680px]:pt-2'
          : 'grid gap-3 pt-3 max-[680px]:gap-2 max-[680px]:pt-2'
      }
    >
      {usage !== null ? <ResponseUsageStrip usage={usage} /> : null}
      {toolCallCount > 0 ? (
        <section
          aria-label="Tool Calls Detail"
          className="grid gap-2 max-[680px]:gap-1.5"
        >
          <h3 className="text-sm font-semibold text-foreground max-[680px]:text-sm max-[680px]:leading-snug">
            Tool Calls · {toolCallCount}
          </h3>
          <DataList>
            {response.tool_calls.map((call, index) => (
              <DataListItem
                className="grid gap-1 max-[680px]:gap-1"
                key={`${call.name}-${call.query ?? 'no-query'}-${index}`}
              >
                <strong className="text-sm text-foreground max-[680px]:text-sm max-[680px]:leading-snug">
                  {call.name}
                </strong>
                <span className="text-sm text-muted-foreground max-[680px]:text-sm max-[680px]:leading-snug">
                  {call.query ?? 'No Query Stored.'}
                </span>
                <small className="text-xs text-muted-foreground max-[680px]:text-xs max-[680px]:leading-snug">
                  Limit {call.limit ?? 'Unknown'} /{' '}
                  {call.result_count ?? 'Unknown'} Results
                </small>
              </DataListItem>
            ))}
          </DataList>
        </section>
      ) : null}
      {sourceCount > 0 ? (
        <section
          aria-label="Sources Detail"
          className="grid gap-2 max-[680px]:gap-1.5"
        >
          <h3 className="text-sm font-semibold text-foreground max-[680px]:text-sm max-[680px]:leading-snug">
            Sources · {sourceCount}
          </h3>
          <DataList>
            {response.citations.map((result, index) => (
              <DataListItem
                className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] max-[680px]:gap-2"
                key={`${result.chunk_id ?? 'no-chunk'}-${result.citation.source_id}-${index}`}
              >
                <div className="grid min-w-0 gap-2 max-[680px]:gap-1.5">
                  <strong className="break-words text-sm text-foreground max-[680px]:text-sm max-[680px]:leading-snug">
                    <span className="mr-1.5 inline-flex size-5 items-center justify-center rounded-full bg-primary/15 text-[10px] font-semibold tabular-nums">
                      {index + 1}
                    </span>
                    {result.citation.source_external_id}
                  </strong>
                  <p className="text-sm leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-sm max-[680px]:leading-relaxed">
                    {result.citation.snippet}
                  </p>
                  <div className="flex flex-wrap gap-2 max-[680px]:gap-1.5">
                    <Badge>
                      {sourceTypeLabel(result.citation.source_type)} Source
                    </Badge>
                    <Badge>
                      Version {result.citation.document_version_number}
                    </Badge>
                    <Badge>
                      Chars {result.citation.char_start}-{result.citation.char_end}
                    </Badge>
                  </div>
                </div>
                <DataListItemActions className="justify-start md:justify-end">
                  <StatusBadge>Score {formatScore(result.score)}</StatusBadge>
                  <Button
                    aria-label={`View Source ${result.citation.source_external_id}`}
                    onClick={() =>
                      onOpenSource(
                        result.citation.source_id,
                        result.citation.snippet,
                      )
                    }
                    type="button"
                    variant="secondary"
                  >
                    View Source
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
    <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6 max-[680px]:gap-0.5">
      {usage.model !== null ? (
        <UsageItem label="Model" value={usage.model} />
      ) : null}
      {usage.provider !== null ? (
        <UsageItem label="Provider" value={usage.provider} />
      ) : null}
      <UsageItem label="Tokens" value={formatNullableTokens(usage.totalTokens)} />
      <UsageItem label="Input" value={formatNullableTokenCount(usage.inputTokens)} />
      <UsageItem label="Output" value={formatNullableTokenCount(usage.outputTokens)} />
      <UsageItem label="Cost" value={formatNullableUsageCost(usage.costUsd)} />
    </dl>
  )
}

function UsageItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3 max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-2 max-[680px]:shadow-none">
      <dt className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-xs max-[680px]:tracking-wide">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-semibold text-foreground max-[680px]:mt-0.5 max-[680px]:text-sm max-[680px]:leading-snug">
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
  // Primary commit only while still a draft with non-empty text.
  const canSubmitPrimary = canEdit && draft.text.trim().length > 0
  const primaryAction =
    draft.reviewAction === 'approve' ? 'Approve Knowledge' : 'Request Approval'

  return (
    <article
      aria-label={`Knowledge draft ${draft.draftId}`}
      className="grid gap-3 rounded-md border border-border bg-card p-4 text-card-foreground max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-3 max-[680px]:shadow-none"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2 max-[680px]:gap-1.5">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-1">
          <span className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-xs max-[680px]:tracking-wide">
            Knowledge draft
          </span>
          <strong className="break-words text-sm text-foreground max-[680px]:text-sm max-[680px]:leading-snug">
            {draft.scope}
          </strong>
        </div>
        <StatusBadge tone={knowledgeDraftStatusTone(draft.status)}>
          {knowledgeDraftStatusLabel(draft.status)}
        </StatusBadge>
      </div>
      <Field>
        <FieldLabel htmlFor={`knowledge-draft-${draft.draftId}`}>
          Knowledge draft text
        </FieldLabel>
        <FieldControl>
          <Textarea
            aria-label="Knowledge Draft Text"
            className="focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            disabled={!canEdit}
            id={`knowledge-draft-${draft.draftId}`}
            onChange={(event) => onTextChange(event.currentTarget.value)}
            rows={3}
            value={draft.text}
          />
        </FieldControl>
      </Field>
      {draft.proposalId === null ? null : (
        <p className="text-sm text-muted-foreground max-[680px]:text-sm max-[680px]:leading-snug">
          Proposal {draft.proposalId}
        </p>
      )}
      {draft.approvedSourceId !== null ? (
        <p
          className="text-sm text-muted-foreground max-[680px]:text-sm max-[680px]:leading-snug"
          data-slot="chat-knowledge-ingest-status"
        >
          Source {shortSessionId(draft.approvedSourceId)}
          {draft.ingestStatus !== null
            ? ` · ingest ${draft.ingestStatus}`
            : ' · saved (indexing may still be pending)'}
        </p>
      ) : null}
      {draft.error === null ? null : (
        <InlineFeedback tone="danger">{operatorSafeMessage(draft.error)}</InlineFeedback>
      )}
      <div className="flex flex-wrap gap-2 max-[680px]:gap-1.5">
        <Button disabled={!canSubmitPrimary} onClick={onSubmit} type="button">
          {primaryAction}
        </Button>
        <Button
          disabled={!canEdit}
          onClick={onRefine}
          type="button"
          variant="secondary"
        >
          Refine In Chat
        </Button>
        <Button
          disabled={!canCancel}
          onClick={onCancel}
          type="button"
          variant="secondary"
        >
          Cancel Draft
        </Button>
      </div>
    </article>
  )
}

function sourceTypeLabel(sourceType: string | null | undefined): string {
  if (sourceType === null || sourceType === undefined || sourceType === '') {
    return 'Unknown'
  }
  if (sourceType === 'url') {
    return 'URL'
  }
  if (sourceType === 'pdf') {
    return 'PDF'
  }
  if (sourceType === 'docx') {
    return 'DOCX'
  }
  if (sourceType === 'txt') {
    return 'TXT'
  }
  return sourceType.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function knowledgeDraftStatusLabel(status: ChatKnowledgeDraftStatus): string {
  if (status === 'approved') {
    return 'Approved'
  }
  if (status === 'pending') {
    return 'Pending'
  }
  if (status === 'cancelled') {
    return 'Canceled'
  }
  if (status === 'draft') {
    return 'Draft'
  }
  return status
}

function knowledgeDraftStatusTone(
  status: ChatKnowledgeDraftStatus,
): 'danger' | 'neutral' | 'primary' | 'success' | 'warning' {
  if (status === 'approved') {
    return 'success'
  }
  if (status === 'pending') {
    return 'warning'
  }
  if (status === 'cancelled') {
    return 'neutral'
  }
  if (status === 'draft') {
    return 'primary'
  }
  return 'neutral'
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
    approvedSourceId: getJsonString(call.result_summary, 'approved_source_id'),
    draftId,
    error: null,
    ingestStatus: null,
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

function CopyAnswerButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <Button
      aria-label={copied ? 'Copied answer' : 'Copy answer'}
      className="h-7 gap-1 px-2 text-[11px]"
      data-slot="chat-copy-answer"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          window.setTimeout(() => setCopied(false), 1500)
        })
      }}
      size="sm"
      type="button"
      variant="ghost"
    >
      {copied ? (
        <Check aria-hidden="true" className="size-3.5" />
      ) : (
        <Copy aria-hidden="true" className="size-3.5" />
      )}
      {copied ? 'Copied' : 'Copy'}
    </Button>
  )
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
  return error instanceof Error
    ? operatorSafeMessage(error.message)
    : 'Request failed.'
}

function formatScore(score: number): string {
  return score.toFixed(2)
}

function formatNullableUsageCost(value: number | null): string {
  return value === null ? 'Unknown Cost' : formatUsd(value)
}

function formatNullableTokens(value: number | null): string {
  return value === null ? 'Unknown Tokens' : `${formatNumber(value)} Tokens`
}

function formatNullableTokenCount(value: number | null): string {
  return value === null ? 'Unknown' : formatNumber(value)
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
