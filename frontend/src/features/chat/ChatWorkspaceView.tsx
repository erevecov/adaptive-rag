import {
  type Dispatch,
  type DragEvent,
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
  CornerDownLeft,
  FileText,
  ImageIcon,
  Map as MapIcon,
  Mic,
  MoreVertical,
  Paperclip,
  RefreshCw,
  Square,
} from 'lucide-react'

import {
  AttachmentLightbox,
  type AttachmentLightboxItem,
} from '@/features/chat/AttachmentLightbox'
import {
  AttachmentChips,
  AttachmentFileInput,
  type LocalAttachment,
} from '@/features/chat/ChatAttachments'
import { ChatPipelineSteps } from '@/components/ChatPipelineSteps'
import { MarkdownAnswer } from '@/components/MarkdownAnswer'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import * as DropdownMenu from '@/components/ui/dropdown-menu'
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
import type { ChatMessageAttachmentRef, ChatStep } from '@/lib/chatSteps'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import { cn } from '@/lib/utils'

/** Icon-only tool control — no chrome/border; label via aria-label. */
const COMPOSER_TOOL_BUTTON_CLASS =
  'inline-flex size-8 shrink-0 items-center justify-center rounded-none border-0 bg-transparent p-0 text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground active:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-40 max-[680px]:size-11'

const COMPOSER_PRIMARY_ACTION_CLASS =
  'inline-flex size-8 shrink-0 items-center justify-center rounded-none border-0 bg-transparent p-0 text-foreground shadow-none hover:bg-transparent hover:text-primary active:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-40 max-[680px]:size-11'

const COMPOSER_TOOL_ACTIVE_CLASS = 'text-primary'

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
  assistantMessageId?: string | null
  /** Attachment refs echoed from the user message metadata (read-only chips). */
  attachments?: ChatMessageAttachmentRef[]
  citations: ChatResponseBody['citations']
  id: string
  question: string
  steps: ChatResponseBody['steps']
  tool_calls: ChatResponseBody['tool_calls']
  userMessageId?: string | null
}

/** Payload for answer ⋯ → Ver detalles (turn-scoped Context). */
export type ViewTurnDetailsPayload = {
  detailsInstanceId: string
  question: string
  turnId: string
}

export type ChatWorkspacePanelProps = {
  activeResponseQuestion: string | null
  /** Attachment refs of the live/just-sent turn (chips under its bubble). */
  activeResponseAttachments?: ChatMessageAttachmentRef[]
  appliedMemories?: UserMemory[]
  /** Local composer attachments (upload chips). */
  attachments?: LocalAttachment[]
  attachmentAccept?: string
  attachmentsAtCap?: boolean
  attachmentsBlocked?: boolean
  /** When set, follow-ups continue this multi-turn session. */
  continuingSessionId?: string | null
  drafts: ChatKnowledgeDraftMap
  /** Elapsed ms from last SSE heartbeat while a request is in flight. */
  heartbeatElapsedMs?: number | null
  isAsking: boolean
  isContextInspectorActive: boolean
  isMinimapInspectorActive: boolean
  isSpeechSupported: boolean
  onAddAttachmentFiles?(files: FileList | File[]): void
  onCancelRequest(): void
  onOpenContextInspector(): void
  onOpenMinimapInspector(): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onQuestionChange(value: string): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  /** Re-run the last succeeded answer without archiving it into prior turns. */
  onRegenerateLastAnswer?(): void
  onRemoveAttachment?(localId: string): void
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
  /** Open Context dock scoped to one transcript turn. */
  onViewTurnDetails?(payload: ViewTurnDetailsPayload): void
  /** Load attachment bytes for lightbox (transcript / remote ids). */
  onLoadAttachmentContent?(attachmentId: string): Promise<Blob>
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
  activeResponseAttachments = [],
  appliedMemories = [],
  attachments = [],
  attachmentAccept,
  attachmentsAtCap = false,
  attachmentsBlocked = false,
  continuingSessionId = null,
  drafts,
  heartbeatElapsedMs = null,
  isAsking,
  isContextInspectorActive,
  isMinimapInspectorActive,
  isSpeechSupported,
  onAddAttachmentFiles,
  onCancelRequest,
  onOpenContextInspector,
  onOpenMinimapInspector,
  onOpenSource,
  onQuestionChange,
  onRefineKnowledgeDraft,
  onRegenerateLastAnswer,
  onRemoveAttachment,
  onRetryLastQuestion,
  onStartNewSession,
  onEditQuestion,
  onStartSpeechRecognition,
  onStopSpeechRecognition,
  onSubmit,
  onSubmitKnowledgeDraft,
  onTranscriptScroll,
  onViewTurnDetails,
  onLoadAttachmentContent,
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
  const attachmentInputRef = useRef<HTMLInputElement>(null)
  const [isComposerDragActive, setIsComposerDragActive] = useState(false)
  const composerDragDepthRef = useRef(0)
  const [lightboxItem, setLightboxItem] = useState<AttachmentLightboxItem | null>(
    null,
  )

  useEffect(() => {
    if (question.length > 0) {
      return
    }
    const el = questionInputRef.current
    if (el !== null) {
      el.style.height = ''
    }
  }, [question])

  const canSend =
    question.trim().length > 0 && !attachmentsBlocked && !isAsking
  const canAcceptDroppedFiles =
    onAddAttachmentFiles !== undefined && !attachmentsAtCap && !isAsking

  function resetComposerDrag() {
    composerDragDepthRef.current = 0
    setIsComposerDragActive(false)
  }

  function handleComposerDragEnter(event: DragEvent<HTMLDivElement>) {
    if (!canAcceptDroppedFiles) {
      return
    }
    if (![...event.dataTransfer.types].includes('Files')) {
      return
    }
    event.preventDefault()
    composerDragDepthRef.current += 1
    setIsComposerDragActive(true)
  }

  function handleComposerDragOver(event: DragEvent<HTMLDivElement>) {
    if (!canAcceptDroppedFiles) {
      return
    }
    if (![...event.dataTransfer.types].includes('Files')) {
      return
    }
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
  }

  function handleComposerDragLeave(event: DragEvent<HTMLDivElement>) {
    if (!canAcceptDroppedFiles) {
      return
    }
    event.preventDefault()
    composerDragDepthRef.current = Math.max(0, composerDragDepthRef.current - 1)
    if (composerDragDepthRef.current === 0) {
      setIsComposerDragActive(false)
    }
  }

  function handleComposerDrop(event: DragEvent<HTMLDivElement>) {
    if (!canAcceptDroppedFiles || onAddAttachmentFiles === undefined) {
      return
    }
    event.preventDefault()
    resetComposerDrag()
    const files = event.dataTransfer.files
    if (files.length === 0) {
      return
    }
    onAddAttachmentFiles(files)
  }

  return (
    <Panel
      aria-label="Chat Workspace"
      className="flex h-full max-h-full min-h-0 w-full flex-1 flex-col overflow-hidden border-0 bg-transparent shadow-none"
      data-chat-radius="square"
      role="region"
    >
      {/* flex-1 + min-h-0: only the transcript scrolls; composer stays pinned. */}
      <div
        aria-busy={isAsking || requestState === 'loading' || undefined}
        aria-label="Chat Transcript"
        className="scrollbar-chat min-h-0 flex-1 overflow-x-hidden overflow-y-auto"
        data-slot="chat-transcript"
        onScroll={onTranscriptScroll}
        ref={transcriptRef}
        role="region"
      >
        {/* pb clears the composer fade (h-8) so Details / last turn stay readable. */}
        <div className="mx-auto grid w-full max-w-3xl gap-3 px-0.5 pb-12 pr-[18px] max-[900px]:pr-3.5 max-[680px]:gap-2 max-[680px]:pb-10 max-[680px]:pr-1">
          {priorTurns.map((turn) => (
            <ResponseContent
              key={turn.id}
              appliedMemories={[]}
              attachments={turn.attachments}
              detailsInstanceId={`turn-${turn.id}`}
              drafts={{}}
              onEditQuestion={
                onEditQuestion === undefined
                  ? undefined
                  : (text) => onEditQuestion(text, turn.id)
              }
              onOpenAttachment={(attachment) =>
                setLightboxItem({
                  id: attachment.id,
                  filename: attachment.filename,
                  kind: attachment.kind,
                  mime: attachment.mime,
                })
              }
              onOpenSource={onOpenSource}
              onRefineKnowledgeDraft={onRefineKnowledgeDraft}
              onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
              onViewTurnDetails={onViewTurnDetails}
              providerUsage={[]}
              question={turn.question}
              questionSticky={false}
              response={{
                answer: turn.answer,
                citations: turn.citations,
                session_id: continuingSessionId,
                steps: turn.steps,
                tool_calls: turn.tool_calls,
              }}
              setDrafts={setDrafts}
              state="succeeded"
              turnId={turn.assistantMessageId ?? turn.id}
            />
          ))}
          <ResponsePanel
            appliedMemories={appliedMemories}
            attachments={activeResponseAttachments}
            drafts={drafts}
            errorDetail={requestError}
            heartbeatElapsedMs={heartbeatElapsedMs}
            onEditQuestion={onEditQuestion}
            onOpenAttachment={(attachment) =>
              setLightboxItem({
                id: attachment.id,
                filename: attachment.filename,
                kind: attachment.kind,
                mime: attachment.mime,
              })
            }
            onOpenSource={onOpenSource}
            onQuestionChange={onQuestionChange}
            onRefineKnowledgeDraft={onRefineKnowledgeDraft}
            onRegenerateLastAnswer={onRegenerateLastAnswer}
            onRetryLastQuestion={onRetryLastQuestion}
            onStartNewSession={onStartNewSession}
            onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
            onViewTurnDetails={onViewTurnDetails}
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
          'relative shrink-0 bg-background pr-[18px] max-[900px]:pr-3.5 max-[680px]:pr-1',
          // Keep Ask docked above the fold on narrow shells / soft keyboards.
          'max-[680px]:sticky max-[680px]:bottom-0 max-[680px]:z-20',
          'max-[680px]:border-t max-[680px]:border-primary/95',
          // Purple hairline above sticky Ask dock (mirrors question sticky).
          'max-[680px]:shadow-[0_-1px_0_0] max-[680px]:shadow-primary/95',
          'max-[680px]:pb-[max(0.25rem,env(safe-area-inset-bottom))]',
        )}
        data-slot="chat-composer-shell"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-8 h-8 bg-gradient-to-b from-background/0 via-background/80 to-background max-[680px]:-top-1 max-[680px]:h-1 max-[680px]:via-card/80 max-[680px]:to-card"
          data-slot="chat-composer-gradient"
        />
        <form
          className="relative mx-auto w-full max-w-3xl px-1 pb-0 pt-1 sm:px-2 max-[680px]:px-1 max-[680px]:pt-1"
          data-slot="chat-composer"
          id="chat-composer"
          onSubmit={onSubmit}
          tabIndex={-1}
        >
          <div
            className={cn(
              'rounded-2xl border border-border bg-muted/15 p-1.5 shadow-sm',
              isComposerDragActive &&
                'border-primary/60 bg-primary/5 ring-1 ring-primary/30',
            )}
            data-drag-active={isComposerDragActive ? 'true' : undefined}
            data-slot="chat-composer-input-shell"
            onDragEnter={handleComposerDragEnter}
            onDragLeave={handleComposerDragLeave}
            onDragOver={handleComposerDragOver}
            onDrop={handleComposerDrop}
          >
            {attachments.length > 0 ? (
              <div className="px-2 pb-1 pt-1">
                <AttachmentChips
                  attachments={attachments.map((item) => ({
                    localId: item.localId,
                    filename: item.file.name,
                    previewUrl: item.previewUrl,
                    kind: item.kind,
                    mime: item.mime ?? item.file.type,
                    attachmentId: item.attachmentId,
                    status: item.status,
                    error: item.error,
                  }))}
                  onOpen={(item) =>
                    setLightboxItem({
                      id: item.attachmentId ?? item.localId,
                      filename: item.filename,
                      kind: item.kind ?? 'document',
                      mime: item.mime ?? 'application/octet-stream',
                      previewUrl: item.previewUrl,
                    })
                  }
                  onRemove={onRemoveAttachment}
                />
              </div>
            ) : null}

            <Field className="gap-0">
              <FieldLabel className="sr-only" htmlFor="chat-question">
                Question
              </FieldLabel>
              <FieldControl className="gap-0">
                <Textarea
                  className={cn(
                    'scrollbar-chat max-h-48 min-h-[3.5rem] w-full resize-none overflow-y-auto rounded-xl border-0 bg-transparent px-4 py-2.5 text-sm leading-relaxed shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 max-[680px]:min-h-11 max-[680px]:text-base',
                    'placeholder:text-muted-foreground',
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
                      if (!canSend) {
                        return
                      }
                      event.currentTarget.form?.requestSubmit()
                    }
                  }}
                  onPaste={(event) => {
                    if (onAddAttachmentFiles === undefined) {
                      return
                    }
                    const files = event.clipboardData?.files
                    if (files === undefined || files.length === 0) {
                      return
                    }
                    event.preventDefault()
                    onAddAttachmentFiles(files)
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
              className="mt-1 flex flex-wrap items-center justify-between gap-2 max-[680px]:mt-1.5 max-[680px]:gap-1.5"
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
                  {onAddAttachmentFiles !== undefined &&
                  attachmentAccept !== undefined ? (
                    <>
                      <AttachmentFileInput
                        accept={attachmentAccept}
                        disabled={attachmentsAtCap || isAsking}
                        inputRef={attachmentInputRef}
                        onChange={(event) => {
                          const files = event.currentTarget.files
                          if (files !== null && files.length > 0) {
                            onAddAttachmentFiles(files)
                          }
                          event.currentTarget.value = ''
                        }}
                      />
                      <Button
                        aria-label="Attach files"
                        className={COMPOSER_TOOL_BUTTON_CLASS}
                        disabled={attachmentsAtCap || isAsking}
                        onClick={() => attachmentInputRef.current?.click()}
                        size="icon"
                        type="button"
                        variant="ghost"
                      >
                        <Paperclip aria-hidden="true" className="size-4" />
                      </Button>
                    </>
                  ) : null}
                  <Button
                    aria-label="Open Context Sidebar"
                    aria-pressed={isContextInspectorActive}
                    className={cn(
                      COMPOSER_TOOL_BUTTON_CLASS,
                      isContextInspectorActive && COMPOSER_TOOL_ACTIVE_CLASS,
                    )}
                    onClick={onOpenContextInspector}
                    size="icon"
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
                      isMinimapInspectorActive && COMPOSER_TOOL_ACTIVE_CLASS,
                    )}
                    onClick={onOpenMinimapInspector}
                    size="icon"
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
                    aria-label="Cancel Request"
                    className={cn(
                      COMPOSER_TOOL_BUTTON_CLASS,
                      'text-destructive hover:text-destructive',
                    )}
                    onClick={onCancelRequest}
                    size="icon"
                    title="Cancel Request"
                    type="button"
                    variant="ghost"
                  >
                    <Square aria-hidden="true" className="size-4" />
                  </Button>
                ) : (
                  <Button
                    aria-label="Ask"
                    className={COMPOSER_PRIMARY_ACTION_CLASS}
                    disabled={!canSend}
                    size="icon"
                    title="Enter to send"
                    type="submit"
                  >
                    <CornerDownLeft aria-hidden="true" className="size-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Error detail is co-located with the transcript failure/cancel state
              (see ResponsePanel). Avoid a second under-composer callout. */}
        </form>
      </div>
      {lightboxItem !== null ? (
        <AttachmentLightbox
          item={lightboxItem}
          loadContent={
            lightboxItem.previewUrl
              ? undefined
              : onLoadAttachmentContent
          }
          onClose={() => setLightboxItem(null)}
        />
      ) : null}
    </Panel>
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
        : 'Speech Recognition Is Not Supported In This Browser.')

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
          isListening && COMPOSER_TOOL_ACTIVE_CLASS,
        )}
        disabled={!isSupported}
        onClick={isListening ? onStop : onStart}
        size="icon"
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
  'What is the workspace codename?',
  'Which sources cover deployment?',
] as const

function ResponsePanel({
  appliedMemories,
  attachments = [],
  drafts,
  errorDetail = null,
  heartbeatElapsedMs = null,
  onEditQuestion,
  onOpenAttachment,
  onOpenSource,
  onQuestionChange,
  onRefineKnowledgeDraft,
  onRegenerateLastAnswer,
  onRetryLastQuestion,
  onStartNewSession,
  onSubmitKnowledgeDraft,
  onViewTurnDetails,
  providerUsage,
  question,
  response,
  setDrafts,
  state,
}: {
  appliedMemories: UserMemory[]
  attachments?: ChatMessageAttachmentRef[]
  drafts: ChatKnowledgeDraftMap
  errorDetail?: string | null
  heartbeatElapsedMs?: number | null
  onEditQuestion?(text: string, turnId?: string): void
  onOpenAttachment?(attachment: ChatMessageAttachmentRef): void
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
  onViewTurnDetails?(payload: ViewTurnDetailsPayload): void
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
          attachments={attachments}
          drafts={drafts}
          onOpenAttachment={onOpenAttachment}
          onOpenSource={onOpenSource}
          onRefineKnowledgeDraft={onRefineKnowledgeDraft}
          onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
          onViewTurnDetails={onViewTurnDetails}
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
        attachments={attachments}
        drafts={drafts}
        onEditQuestion={
          onEditQuestion === undefined
            ? undefined
            : (text) => onEditQuestion(text)
        }
        onOpenAttachment={onOpenAttachment}
        onOpenSource={onOpenSource}
        onRefineKnowledgeDraft={onRefineKnowledgeDraft}
        onRegenerateLastAnswer={
          state === 'succeeded' ? onRegenerateLastAnswer : undefined
        }
        onSubmitKnowledgeDraft={onSubmitKnowledgeDraft}
        onViewTurnDetails={onViewTurnDetails}
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
  attachments,
  detailsInstanceId,
  drafts,
  onEditQuestion,
  onOpenAttachment,
  onOpenSource,
  onRefineKnowledgeDraft,
  onRegenerateLastAnswer,
  onSubmitKnowledgeDraft,
  onViewTurnDetails,
  providerUsage,
  question,
  questionSticky = true,
  response,
  setDrafts,
  state,
  turnId,
}: {
  appliedMemories: UserMemory[]
  /** Attachment refs shown as read-only chips under the user bubble. */
  attachments?: ChatMessageAttachmentRef[]
  /** Exclusive Details accordion id (only one open across the transcript). */
  detailsInstanceId?: string
  drafts: ChatKnowledgeDraftMap
  onEditQuestion?(text: string): void
  onOpenAttachment?(attachment: ChatMessageAttachmentRef): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  onRefineKnowledgeDraft(draft: ChatKnowledgeDraft): void
  onRegenerateLastAnswer?(): void
  onSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal>
  onViewTurnDetails?(payload: ViewTurnDetailsPayload): void
  providerUsage: ChatHistoryProviderUsage[]
  question: string | null
  /** Prior turns render their question in normal flow (no sticky stacking). */
  questionSticky?: boolean
  response: ChatResponseBody
  setDrafts: ChatKnowledgeDraftSetter
  state: RequestState
  /** Stable id for Context turn focus (assistant message id when known). */
  turnId?: string
}) {
  const isStreaming = state === 'loading'
  const resolvedDetailsInstanceId =
    detailsInstanceId ??
    `live-${response.session_id ?? 'current'}-${question ?? 'q'}`
  const resolvedTurnId =
    turnId ??
    `live-${response.session_id ?? 'current'}`
  const canViewTurnDetails =
    onViewTurnDetails !== undefined &&
    !isStreaming &&
    (response.answer.trim().length > 0 || state === 'succeeded')
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
    /* Beflow chat rhythm: user bubble then open assistant column (no twin cards). */
    <div
      aria-label="Chat Response"
      className="grid gap-2 max-[680px]:gap-1.5"
      role="region"
    >
      <QuestionPrompt
        key={question ?? 'empty-question'}
        attachments={attachments}
        onEdit={
          onEditQuestion !== undefined &&
          !isStreaming &&
          question !== null &&
          question.trim().length > 0
            ? () => onEditQuestion(question)
            : undefined
        }
        onOpenAttachment={onOpenAttachment}
        question={question}
        sticky={questionSticky}
      />

      {response.answer.trim().length > 0 || !isStreaming ? (
        <article
          aria-label="Answer"
          className={cn(
            /* beflow AssistantTurn: no card chrome; soft hover wash only */
            'group/assistant-turn relative rounded-lg px-1 py-2 text-foreground tracking-tight',
            'transition-colors hover:bg-black/[0.025] dark:hover:bg-white/[0.025]',
            'sm:px-2 max-[680px]:px-0.5 max-[680px]:py-1.5',
          )}
          data-slot="chat-message"
        >
          <div className="min-w-0">
          <div className="mb-1.5 flex min-h-5 flex-wrap items-center gap-2 max-[680px]:mb-1">
            {isStreaming ? (
              <StatusBadge className="w-fit" tone="primary">
                Streaming
              </StatusBadge>
            ) : null}
            <div
              className={cn(
                'ml-auto flex items-center gap-1 opacity-0 transition-opacity',
                'group-hover/assistant-turn:opacity-100 group-focus-within/assistant-turn:opacity-100',
              )}
            >
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
              {canViewTurnDetails ? (
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <Button
                      aria-label="Más opciones de respuesta"
                      className="size-7 shrink-0 rounded-md p-0 text-muted-foreground hover:bg-primary/15 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                      data-slot="answer-actions-trigger"
                      size="sm"
                      type="button"
                      variant="ghost"
                    >
                      <MoreVertical aria-hidden="true" className="size-3.5" />
                    </Button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content
                      align="end"
                      className="z-50 grid min-w-[140px] gap-0.5 rounded-md border border-border bg-popover p-1 text-sm tracking-tight text-popover-foreground shadow-[var(--shadow-popover)]"
                      data-slot="answer-actions-menu"
                      onCloseAutoFocus={(event) => event.preventDefault()}
                      sideOffset={4}
                    >
                      <DropdownMenu.Item
                        className="px-3 py-1.5 text-left"
                        data-slot="answer-view-details"
                        onClick={() => {
                          onViewTurnDetails?.({
                            detailsInstanceId: resolvedDetailsInstanceId,
                            question: question ?? '',
                            turnId: resolvedTurnId,
                          })
                        }}
                      >
                        Ver detalles
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              ) : null}
            </div>
          </div>
          {response.answer.trim().length > 0 ? (
            <MarkdownAnswer
              citations={response.citations}
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
                Drafting Answer…
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
              returned nothing useful — verify before trusting workspace claims.
            </Callout>
          ) : null}
          {/* Citation chips live inline in MarkdownAnswer (doc-N). Full
              source list is under Details → Sources Detail only. */}
          </div>
        </article>
      ) : null}

      {hasStepDetails ? (
        <ChatPipelineSteps
          instanceId={resolvedDetailsInstanceId}
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

/** Compact role glyph (›) — same row as question text (neutral, not purple). */
function ChatRoleMarker() {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex h-[1.25rem] w-4 shrink-0 select-none items-center justify-center',
        'font-mono text-[13px] font-medium leading-none tracking-tight',
        'text-muted-foreground/70',
      )}
      data-slot="chat-role-marker"
      data-tone="user"
    >
      ›
    </span>
  )
}

function QuestionPrompt({
  attachments,
  onEdit,
  onOpenAttachment,
  question,
  sticky = true,
}: {
  /** Read-only attachment refs echoed from the user message metadata. */
  attachments?: ChatMessageAttachmentRef[]
  onEdit?(): void
  onOpenAttachment?(attachment: ChatMessageAttachmentRef): void
  question: string | null
  /** Current turn sticks to the transcript top; prior turns flow normally. */
  sticky?: boolean
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
    /* Grok Build–style: › + text on one row; Edit floats so it never pushes text down. */
    <div
      className={cn(
        'group/user-turn w-full pb-1.5',
        sticky && 'sticky top-0 z-10',
      )}
      aria-label="Your question"
      data-slot="chat-question-sticky"
    >
      <div
        className={cn(
          'relative flex w-full items-start gap-2 rounded-lg border-0 bg-chat-user-bubble px-3 py-2',
          'max-[680px]:gap-1.5 max-[680px]:px-2.5 max-[680px]:py-1.5',
          onEdit !== undefined && 'pr-12',
        )}
        data-slot="chat-question-surface"
      >
        <ChatRoleMarker />
        <div className="min-w-0 flex-1">
          {shouldCollapse ? (
            <button
              aria-expanded={expanded}
              aria-label={
                expanded ? 'Collapse full question' : 'Expand full question'
              }
              className={cn(
                'w-full text-left text-[13px] leading-snug text-foreground',
                expanded
                  ? 'whitespace-pre-wrap break-words'
                  : 'truncate whitespace-nowrap',
              )}
              onClick={() => setExpanded((current) => !current)}
              title={trimmedQuestion}
              type="button"
            >
              {displayQuestion}
            </button>
          ) : (
            <p className="whitespace-pre-wrap break-words text-[13px] leading-snug text-foreground">
              {displayQuestion}
            </p>
          )}
          {attachments !== undefined && attachments.length > 0 ? (
            <ul
              aria-label="Message attachments"
              className="mt-1.5 flex flex-wrap gap-1.5"
              data-slot="chat-turn-attachments"
            >
              {attachments.map((attachment) => (
                <li
                  className="max-w-[12rem]"
                  key={attachment.id}
                >
                  <button
                    aria-label={`Open attachment ${attachment.filename}`}
                    className={cn(
                      'flex w-full items-center gap-1.5 rounded-md border border-border/80 bg-background px-1.5 py-1 text-left text-[11px] tracking-tight',
                      'hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    )}
                    data-slot="attachment-chip-open"
                    onClick={() => onOpenAttachment?.(attachment)}
                    type="button"
                  >
                    {attachment.kind === 'image' ? (
                      <ImageIcon
                        aria-hidden="true"
                        className="size-3.5 shrink-0 text-muted-foreground"
                      />
                    ) : (
                      <FileText
                        aria-hidden="true"
                        className="size-3.5 shrink-0 text-muted-foreground"
                      />
                    )}
                    <span className="min-w-0 truncate text-foreground">
                      {attachment.filename}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        {onEdit !== undefined ? (
          <Button
            aria-label="Edit question"
            className={cn(
              'absolute right-1.5 top-1.5 h-6 px-1.5 text-[10px] opacity-0 transition-opacity',
              'group-hover/user-turn:opacity-100 group-focus-within/user-turn:opacity-100',
            )}
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
          <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground max-[680px]:size-3.5" />
        ) : (
          <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground max-[680px]:size-3.5" />
        )}
        <span className="min-w-0 truncate max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
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
      aria-label={`Knowledge Draft ${draft.draftId}`}
      className="grid gap-3 rounded-md border border-border bg-card p-4 text-card-foreground max-[680px]:gap-2 max-[680px]:rounded-md max-[680px]:border-border max-[680px]:p-3 max-[680px]:shadow-none"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2 max-[680px]:gap-1.5">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-1">
          <span className="text-xs font-semibold uppercase tracking-normal text-muted-foreground max-[680px]:text-xs max-[680px]:tracking-wide">
            Knowledge Draft
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
          Knowledge Draft Text
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
    : 'Request Failed.'
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
