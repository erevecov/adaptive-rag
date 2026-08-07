import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import './App.css'
import { StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Panel, PanelDescription } from '@/components/ui/panel'
import { AuthoringPanel } from '@/features/authoring/AuthoringView'
import {
  ChatWorkspacePanel,
  type ChatTranscriptTurn,
} from '@/features/chat/ChatWorkspaceView'
import { UserMemoryPanel } from '@/features/memory/UserMemoryPanel'
import { WorkspaceInspectorPanel } from '@/features/history/HistoryInspectorView'
import { ObservabilityPanel } from '@/features/observability/ObservabilityView'
import { RetrievalPlaygroundPanel } from '@/features/retrieval/RetrievalPlaygroundView'
import { RuntimeSettingsPanel } from '@/features/runtime/RuntimeSettingsView'
import {
  CHAT_RETRIEVAL_MAX_LIMIT,
  PROVIDER_CONNECTION_CAPABILITIES,
  type RuntimeSubmodule,
} from '@/features/runtime/runtimeUi'
import {
  AppShell,
  AppSidebar,
  ChatWorkspaceGrid,
  WorkspaceTopline,
  type AccountModule,
  type AuthoringSubmodule,
  type ObservabilitySubmodule,
  type PrimaryView,
  type RequestState,
  type SessionNavigationFilter,
  type SettingsModule,
  type SettingsNavigationSelection,
} from '@/features/shell/AppShell'
import {
  ApiClientError,
  createApiClient,
  type ApiClient,
  type ChatRetrievalSettings,
  type ChatObservabilitySummary,
  type ChatHistoryRetrievedChunk,
  type ChatHistoryRetrievalRun,
  type ChatHistoryToolCall,
  type ChatResponseBody,
  type ChatSessionDetailResponse,
  type ChatSessionStatus,
  type ChatSessionSummary,
  type UserMemory,
  type ChatToolCall,
  type IngestionJob,
  type IngestionRunResponse,
  type ChatModel,
  type KnowledgeProposal,
  type Project,
  type ProjectMembership,
  type ProjectRuntimeSettings,
  type ProviderConnection,
  type ProviderConnectionCheckResponse,
  type ProviderModel,
  type RuntimeSlotDefault,
  type RetrievalResult,
  type Source,
  type SourceCreateBody,
  type User,
} from './lib/apiClient'
import {
  THEMES,
  THEME_STORAGE_KEY,
  type Theme,
  applyTheme,
  readPersistedTheme,
} from './lib/theme'
import {
  applyChatStepEvent,
  parseChatStepsFromMetadata,
  type ChatStepEvent,
} from './lib/chatSteps'
import { cn } from '@/lib/utils'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_RETRIEVAL_LIMIT = 5
const DEFAULT_RERANK_CANDIDATE_LIMIT = 10
const SESSION_PAGE_SIZE = 15
const PROJECT_STORAGE_KEY = 'adaptive-rag:last-project-id'
const RIGHT_DOCK_INLINE_WIDTH_PX = 1280
type ActiveView = PrimaryView | SettingsModule
const ACTIVE_VIEW_ROUTES: Record<ActiveView, string> = {
  account: '/account',
  authoring: '/settings/authoring',
  chat: '/chat',
  observability: '/settings/observability',
  runtime: '/settings/runtime',
  settings: '/settings/authoring',
}
type InspectorTab = 'context' | 'minimap'
type ChatKnowledgeDraftAction = 'approve' | 'request_approval' | string
type ChatKnowledgeDraftStatus =
  | 'draft'
  | 'pending'
  | 'approved'
  | 'cancelled'
  | string
type ChatKnowledgeDraft = {
  draftId: string
  error: string | null
  proposalId: string | null
  reviewAction: ChatKnowledgeDraftAction
  scope: string
  status: ChatKnowledgeDraftStatus
  text: string
}
type ChatKnowledgeDraftMap = Record<string, ChatKnowledgeDraft>
type SourceViewerState = {
  citationSnippet: string | null
  error: string | null
  source: Source | null
  sourceId: string | null
  state: RequestState
}
type BrowserSpeechRecognition = {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null
  start(): void
  stop(): void
}
type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition
type SpeechRecognitionResultEventLike = {
  results: ArrayLike<ArrayLike<{ transcript?: string }>>
}

type AppProps = {
  apiClient?: ApiClient
  initialProjectId?: string
}

function App({ apiClient, initialProjectId = '' }: AppProps) {
  const client = useMemo(
    () =>
      apiClient ??
      createApiClient({
        authToken: getDefaultApiAuthToken(),
        baseUrl: getDefaultApiBaseUrl(),
      }),
    [apiClient],
  )
  const [projectId, setProjectId] = useState(() =>
    initialProjectId.trim() || readPersistedProjectId(),
  )
  const projectIdRef = useRef(projectId.trim())
  const [question, setQuestion] = useState('')
  const [speechState, setSpeechState] = useState<RequestState>('idle')
  const [speechFeedback, setSpeechFeedback] = useState<string | null>(null)
  const [activeSpeechRecognition, setActiveSpeechRecognition] =
    useState<BrowserSpeechRecognition | null>(null)
  const [response, setResponse] = useState<ChatResponseBody | null>(null)
  const [appliedMemories, setAppliedMemories] = useState<UserMemory[]>([])
  const [activeResponseQuestion, setActiveResponseQuestion] = useState<
    string | null
  >(null)
  const [knowledgeDrafts, setKnowledgeDrafts] =
    useState<ChatKnowledgeDraftMap>({})
  const [sourceViewer, setSourceViewer] = useState<SourceViewerState>({
    citationSnippet: null,
    error: null,
    source: null,
    sourceId: null,
    state: 'idle',
  })
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [sessionDetail, setSessionDetail] =
    useState<ChatSessionDetailResponse | null>(null)
  /** Earlier turns in the open multi-turn session (excludes the live/current turn). */
  const [priorTurns, setPriorTurns] = useState<ChatTranscriptTurn[]>([])
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [historyState, setHistoryState] = useState<RequestState>('idle')
  const [historyStatusFilter, setHistoryStatusFilter] =
    useState<SessionNavigationFilter>('active')
  const [visibleSessionCount, setVisibleSessionCount] =
    useState(SESSION_PAGE_SIZE)
  const [hasMoreSessions, setHasMoreSessions] = useState(false)
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('context')
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(() =>
    readInitialLeftSidebarOpen(),
  )
  const [isRightDockOpen, setIsRightDockOpen] = useState(false)
  const chatTranscriptRef = useRef<HTMLDivElement | null>(null)
  const chatAutoFollowRef = useRef(true)
  const pendingFocusMessageIdRef = useRef<string | null>(null)
  const [detailState, setDetailState] = useState<RequestState>('idle')
  const [requestError, setRequestError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [activeRequestController, setActiveRequestController] =
    useState<AbortController | null>(null)
  const [activeView, setActiveView] =
    useState<ActiveView>(readActiveViewFromRoute)
  const [accountModule, setAccountModule] =
    useState<AccountModule>('appearance')
  const [settingsModule, setSettingsModule] = useState<SettingsModule>(() => {
    const initialActiveView = readActiveViewFromRoute()
    return isSettingsModule(initialActiveView) ? initialActiveView : 'authoring'
  })
  const [authoringSubmodule, setAuthoringSubmodule] =
    useState<AuthoringSubmodule>('projects')
  const [observabilitySubmodule, setObservabilitySubmodule] =
    useState<ObservabilitySubmodule>('summary')
  const [runtimeSubmodule, setRuntimeSubmodule] =
    useState<RuntimeSubmodule>('connections')
  const [theme, setTheme] = useState<Theme>(() => readPersistedTheme())
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
  const [projects, setProjects] = useState<Project[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [projectMemberships, setProjectMemberships] = useState<
    ProjectMembership[]
  >([])
  const [knowledgeProposals, setKnowledgeProposals] = useState<
    KnowledgeProposal[]
  >([])
  const [projectName, setProjectName] = useState('')
  const [sourceType, setSourceType] = useState('markdown')
  const [sourceExternalId, setSourceExternalId] = useState('')
  const [sourceContent, setSourceContent] = useState('')
  const [sourceContentBase64, setSourceContentBase64] = useState('')
  const [sourceFileName, setSourceFileName] = useState('')
  const [sourceTags, setSourceTags] = useState('')
  const [userLogin, setUserLogin] = useState('')
  const [userDisplayName, setUserDisplayName] = useState('')
  const [userSystemRole, setUserSystemRole] = useState('user')
  const [userAccessToken, setUserAccessToken] = useState('')
  const [memberUserId, setMemberUserId] = useState('')
  const [memberRole, setMemberRole] = useState('viewer')
  const [proposalDrafts, setProposalDrafts] = useState<Record<string, string>>({})
  const [proposalRejectReasons, setProposalRejectReasons] = useState<
    Record<string, string>
  >({})
  const [projectAuthoringState, setProjectAuthoringState] =
    useState<RequestState>('loading')
  const [sourceAuthoringState, setSourceAuthoringState] =
    useState<RequestState>('idle')
  const [accessManagementState, setAccessManagementState] =
    useState<RequestState>('idle')
  const [knowledgeReviewState, setKnowledgeReviewState] =
    useState<RequestState>('idle')
  const [projectAuthoringError, setProjectAuthoringError] = useState<
    string | null
  >(null)
  const [sourceAuthoringError, setSourceAuthoringError] = useState<string | null>(
    null,
  )
  const [accessManagementError, setAccessManagementError] = useState<
    string | null
  >(null)
  const [knowledgeReviewError, setKnowledgeReviewError] = useState<
    string | null
  >(null)
  const [ingestionJobs, setIngestionJobs] = useState<IngestionJob[]>([])
  const [ingestionRun, setIngestionRun] = useState<IngestionRunResponse | null>(
    null,
  )
  const [ingestionState, setIngestionState] = useState<RequestState>('idle')
  const [ingestionError, setIngestionError] = useState<string | null>(null)
  const [runtimeConnections, setRuntimeConnections] = useState<
    ProviderConnection[]
  >([])
  const [runtimeSlots, setRuntimeSlots] = useState<RuntimeSlotDefault[]>([])
  const [runtimeChatModels, setRuntimeChatModels] = useState<ChatModel[]>([])
  const [runtimeChatRetrieval, setRuntimeChatRetrieval] =
    useState<ChatRetrievalSettings | null>(null)
  const [runtimeProviderModels, setRuntimeProviderModels] = useState<
    ProviderModel[]
  >([])
  const [projectRuntimeSettings, setProjectRuntimeSettings] =
    useState<ProjectRuntimeSettings | null>(null)
  const [runtimeState, setRuntimeState] = useState<RequestState>('idle')
  const [runtimeError, setRuntimeError] = useState<string | null>(null)
  const [connectionProvider, setConnectionProvider] = useState('qwen')
  const [connectionType, setConnectionType] = useState('hosted')
  const [connectionBaseUrl, setConnectionBaseUrl] = useState('')
  const [connectionCapabilities, setConnectionCapabilities] = useState<string[]>([
    'chat',
  ])
  const [connectionApiKey, setConnectionApiKey] = useState('')
  const [editingConnectionId, setEditingConnectionId] = useState<string | null>(
    null,
  )
  const [connectionCheckResults, setConnectionCheckResults] = useState<
    Record<string, ProviderConnectionCheckResponse>
  >({})
  const [checkingConnectionId, setCheckingConnectionId] = useState<string | null>(
    null,
  )
  const [deleteConnectionId, setDeleteConnectionId] = useState<string | null>(
    null,
  )
  const [deleteConnectionConfirmation, setDeleteConnectionConfirmation] =
    useState('')
  const [modelSyncConnectionId, setModelSyncConnectionId] = useState('')
  const [globalSlot, setGlobalSlot] = useState('chat')
  const [globalSlotConnectionId, setGlobalSlotConnectionId] = useState('')
  const [globalSlotModelId, setGlobalSlotModelId] = useState('')
  const [globalChatConnectionId, setGlobalChatConnectionId] = useState('')
  const [globalChatModelId, setGlobalChatModelId] = useState('')
  const [globalChatRetrievalLimit, setGlobalChatRetrievalLimit] = useState(
    DEFAULT_RETRIEVAL_LIMIT,
  )
  const [globalChatRerankEnabled, setGlobalChatRerankEnabled] = useState(true)
  const [globalChatRerankCandidateLimit, setGlobalChatRerankCandidateLimit] =
    useState(DEFAULT_RERANK_CANDIDATE_LIMIT)
  const [projectSlot, setProjectSlot] = useState('chat')
  const [projectSlotConnectionId, setProjectSlotConnectionId] = useState('')
  const [projectSlotModelId, setProjectSlotModelId] = useState('')
  const [projectChatRetrievalLimit, setProjectChatRetrievalLimit] = useState(
    DEFAULT_RETRIEVAL_LIMIT,
  )
  const [projectChatRerankEnabled, setProjectChatRerankEnabled] = useState(true)
  const [projectChatRerankCandidateLimit, setProjectChatRerankCandidateLimit] =
    useState(DEFAULT_RERANK_CANDIDATE_LIMIT)

  const isAsking = requestState === 'loading'
  const isRightDockInlineViewport = useIsRightDockInlineViewport()
  const isRightDockInline = isRightDockOpen && isRightDockInlineViewport
  const isRightDockOverlay = isRightDockOpen && !isRightDockInlineViewport
  const speechRecognitionConstructor = getSpeechRecognitionConstructor()
  const isSpeechSupported = speechRecognitionConstructor !== null
  const primaryView: PrimaryView =
    activeView === 'chat' || activeView === 'account' ? activeView : 'settings'

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  useEffect(() => {
    replaceRouteForActiveView(readActiveViewFromRoute())

    const handlePopState = () => {
      const nextView = readActiveViewFromRoute()
      setActiveView(nextView)
      if (isSettingsModule(nextView)) {
        setSettingsModule(nextView)
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  useEffect(() => {
    persistProjectId(projectId)
  }, [projectId])

  useEffect(() => {
    if (initialProjectId.trim().length > 0) return

    let ignore = false
    void client
      .getCurrentUser()
      .then((currentUser) => {
        if (ignore) return
        const lastProjectId = currentUser.last_project_id?.trim() ?? ''
        if (lastProjectId.length > 0) {
          setVisibleSessionCount(SESSION_PAGE_SIZE)
          setSessions([])
          setHasMoreSessions(false)
          setSelectedSessionId(null)
          setSessionDetail(null)
          setHistoryError(null)
          setHistoryState('loading')
          projectIdRef.current = lastProjectId
          setProjectId(lastProjectId)
        }
      })
      .catch(() => {
        // Local/bootstrap sessions may not have an authenticated account yet.
      })

    return () => {
      ignore = true
    }
  }, [client, initialProjectId])

  useEffect(() => {
    let ignore = false
    void client
      .listProjects()
      .then((response) => {
        if (ignore) return
        setProjects(response.items)
        setProjectAuthoringState('succeeded')
      })
      .catch((error: unknown) => {
        if (ignore) return
        setProjectAuthoringState('failed')
        setProjectAuthoringError(getErrorMessage(error))
      })

    return () => {
      ignore = true
    }
  }, [client])

  useEffect(() => {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      return
    }

    let ignore = false
    void refreshHistory(
      client,
      trimmedProjectId,
      historyStatusFilter,
      visibleSessionCount,
      {
        onError: (error) => {
          if (!ignore) setHistoryError(error)
        },
        onHasMore: (hasMore) => {
          if (!ignore) setHasMoreSessions(hasMore)
        },
        onItems: (items) => {
          if (!ignore) setSessions(items)
        },
        onState: (state) => {
          if (!ignore) setHistoryState(state)
        },
      },
    )

    return () => {
      ignore = true
    }
  }, [client, historyStatusFilter, projectId, visibleSessionCount])

  useEffect(() => {
    if (inspectorTab !== 'context' || pendingFocusMessageIdRef.current === null) {
      return
    }

    const messageId = pendingFocusMessageIdRef.current
    pendingFocusMessageIdRef.current = null
    focusMessage(messageId)
  }, [inspectorTab])

  useEffect(() => {
    if (primaryView !== 'chat' || !chatAutoFollowRef.current) {
      return
    }

    const transcript = chatTranscriptRef.current
    if (transcript === null) {
      return
    }

    scrollChatTranscriptToBottom(transcript)
  }, [primaryView, requestState, response])

  useEffect(() => {
    if (
      primaryView !== 'settings' ||
      settingsModule !== 'runtime' ||
      runtimeSubmodule !== 'connections'
    ) {
      return
    }

    let ignore = false

    void client
      .listProviderConnections()
      .then((connections) => {
        if (ignore) return
        setRuntimeConnections(connections.items)
        setRuntimeError(null)
        setRuntimeState('succeeded')
      })
      .catch((error: unknown) => {
        if (ignore) return
        setRuntimeState('failed')
        setRuntimeError(getErrorMessage(error))
      })

    return () => {
      ignore = true
    }
  }, [client, primaryView, runtimeSubmodule, settingsModule])

  useEffect(() => {
    if (
      primaryView !== 'settings' ||
      settingsModule !== 'runtime' ||
      runtimeSubmodule !== 'model_catalog'
    ) {
      return
    }

    let ignore = false

    void client
      .listProviderConnections()
      .then(async (connections) => {
        const currentConnectionId = modelSyncConnectionId.trim()
        const selectedConnectionId = connections.items.some(
          (connection) => connection.connection_id === currentConnectionId,
        )
          ? currentConnectionId
          : (connections.items[0]?.connection_id ?? '')

        if (ignore) return
        setRuntimeConnections(connections.items)
        if (selectedConnectionId !== currentConnectionId) {
          setModelSyncConnectionId(selectedConnectionId)
          if (selectedConnectionId.length > 0) {
            return
          }
        }

        if (selectedConnectionId.length === 0) {
          setRuntimeProviderModels([])
          setRuntimeError(null)
          setRuntimeState('succeeded')
          return
        }

        const providerModels = await client.listProviderModels({
          connection_id: selectedConnectionId,
        })
        if (ignore) return
        setRuntimeProviderModels(providerModels.items)
        setRuntimeError(null)
        setRuntimeState('succeeded')
      })
      .catch((error: unknown) => {
        if (ignore) return
        setRuntimeState('failed')
        setRuntimeError(getErrorMessage(error))
      })

    return () => {
      ignore = true
    }
  }, [
    client,
    modelSyncConnectionId,
    primaryView,
    runtimeSubmodule,
    settingsModule,
  ])

  function handleChatTranscriptScroll() {
    const transcript = chatTranscriptRef.current
    if (transcript === null) {
      return
    }

    const distanceFromBottom =
      transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight
    chatAutoFollowRef.current = distanceFromBottom <= 48
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (requestState === 'loading') {
      return
    }

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
    // Keep completed prior turns visible; archive the current succeeded turn.
    if (
      response !== null &&
      requestState === 'succeeded' &&
      activeResponseQuestion !== null &&
      activeResponseQuestion.trim().length > 0
    ) {
      setPriorTurns((current) => [
        ...current,
        {
          id: `local-${Date.now()}`,
          question: activeResponseQuestion,
          answer: response.answer,
          citations: response.citations,
          steps: response.steps,
          tool_calls: response.tool_calls,
        },
      ])
    }
    setResponse(null)
    setAppliedMemories([])
    setActiveResponseQuestion(trimmedQuestion)
    setDetailState('idle')
    setDetailError(null)
    // Keep selectedSessionId so follow-ups continue the same multi-turn session.
    setHistoryStatusFilter('active')
    setVisibleSessionCount(SESSION_PAGE_SIZE)
    resetSourceViewer()
    chatAutoFollowRef.current = true

    const continueSessionId = selectedSessionId
    if (continueSessionId === null) {
      setPriorTurns([])
    }
    const requestBody = {
      message: trimmedQuestion,
      ...(continueSessionId === null ? {} : { session_id: continueSessionId }),
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
            setSelectedSessionId(sessionId)
            setSessions((current) =>
              upsertSessionSummary(
                current,
                buildOptimisticSessionSummary(sessionId, 'running', trimmedQuestion),
              ),
            )
          },
          onToolCall: (toolCall) => {
            markStreamOpened()
            setResponse((current) => appendToolCall(current, toolCall))
          },
          onStep: (step) => {
            markStreamOpened()
            setResponse((current) => appendChatStep(current, step))
          },
        },
        { signal: controller.signal },
      )
      setResponse((current) =>
        withChatSteps(nextResponse, current?.steps ?? []),
      )
      const nextSessionId = nextResponse.session_id
      if (nextSessionId !== null) {
        setSelectedSessionId(nextSessionId)
      }
      setRequestState('succeeded')
      setQuestion('')
      try {
        const memories = await client.listUserMemories({
          project_id: trimmedProjectId,
          status: 'approved',
        })
        setAppliedMemories(memories.items)
      } catch {
        setAppliedMemories([])
      }
      await handleRefreshHistory(trimmedProjectId, 'active')
      if (nextSessionId !== null) {
        setSessions((current) =>
          ensureSessionSummary(
            current,
            buildOptimisticSessionSummary(
              nextSessionId,
              'succeeded',
              trimmedQuestion,
            ),
          ),
        )
        await refreshOpenSessionDetail(trimmedProjectId, nextSessionId)
      }
    } catch (error) {
      if (isAbortError(error)) {
        setRequestState('canceled')
        setRequestError(null)
        // Session was committed at session_started; refresh history so the
        // failed/canceled turn is visible and continuity stays valid.
        if (selectedSessionId !== null) {
          void handleRefreshHistory(trimmedProjectId, 'active')
          void refreshOpenSessionDetail(trimmedProjectId, selectedSessionId)
        }
        return
      }
      if (!streamOpened && shouldFallbackToJsonChat(error)) {
        try {
          const nextResponse = await client.askChat(trimmedProjectId, requestBody)
          setResponse(nextResponse)
          const nextSessionId = nextResponse.session_id
          if (nextSessionId !== null) {
            setSelectedSessionId(nextSessionId)
          }
          setRequestState('succeeded')
          setQuestion('')
          try {
            const memories = await client.listUserMemories({
              project_id: trimmedProjectId,
              status: 'approved',
            })
            setAppliedMemories(memories.items)
          } catch {
            setAppliedMemories([])
          }
          await handleRefreshHistory(trimmedProjectId, 'active')
          if (nextSessionId !== null) {
            setSessions((current) =>
              ensureSessionSummary(
                current,
                buildOptimisticSessionSummary(
                  nextSessionId,
                  'succeeded',
                  trimmedQuestion,
                ),
              ),
            )
            await refreshOpenSessionDetail(trimmedProjectId, nextSessionId)
          }
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

  async function refreshOpenSessionDetail(
    trimmedProjectId: string,
    sessionId: string,
  ): Promise<void> {
    if (!isRightDockOpen) {
      return
    }
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

  async function handleSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal> {
    const trimmedProjectId = projectId.trim()
    const text = draft.text.trim()

    if (trimmedProjectId.length === 0 || text.length === 0) {
      throw new Error('Project ID and knowledge text are required.')
    }

    // Durable path: commit_knowledge already created a pending proposal whose
    // id is the draft_id. Prefer approve to avoid duplicate proposals.
    const looksLikeUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        draft.draftId,
      )
    let proposal: KnowledgeProposal
    if (looksLikeUuid || draft.proposalId !== null) {
      const proposalId = draft.proposalId ?? draft.draftId
      try {
        proposal = await client.approveKnowledgeProposal(
          trimmedProjectId,
          proposalId,
          {},
        )
      } catch {
        // Fall back to create if approve fails (e.g. not yet durable).
        proposal = await client.submitKnowledgeProposal(trimmedProjectId, {
          ...(sessionId === null ? {} : { origin_session_id: sessionId }),
          proposed_text: text,
        })
      }
    } else {
      proposal = await client.submitKnowledgeProposal(trimmedProjectId, {
        ...(sessionId === null ? {} : { origin_session_id: sessionId }),
        proposed_text: text,
      })
    }
    setKnowledgeProposals((current) =>
      upsertKnowledgeProposal(current, proposal),
    )
    return proposal
  }

  function handleRefineKnowledgeDraft(draft: ChatKnowledgeDraft) {
    setQuestion(
      [
        `[refining knowledge draft ${draft.draftId}]`,
        'Current draft:',
        draft.text,
        'Requested change: ',
      ].join('\n'),
    )
  }

  function handleCancelRequest() {
    activeRequestController?.abort()
  }

  function handleRetryLastQuestion() {
    const lastQuestion = activeResponseQuestion?.trim()
    if (lastQuestion === undefined || lastQuestion.length === 0) {
      return
    }
    setQuestion(lastQuestion)
    // Defer submit so the controlled textarea commits lastQuestion first.
    window.setTimeout(() => {
      const form = document.querySelector<HTMLFormElement>('#chat-composer')
      form?.requestSubmit()
    }, 0)
  }

  async function handleRefreshHistory(
    projectIdOverride?: string,
    statusFilterOverride: SessionNavigationFilter = historyStatusFilter,
    limitOverride: number = visibleSessionCount,
  ) {
    const trimmedProjectId = (projectIdOverride ?? projectId).trim()

    if (trimmedProjectId.length === 0) {
      setHistoryState('failed')
      setHistoryError('Project ID is required to refresh history.')
      setHasMoreSessions(false)
      return
    }

    setHistoryError(null)
    await refreshHistory(
      client,
      trimmedProjectId,
      statusFilterOverride,
      limitOverride,
      {
        onError: setHistoryError,
        onHasMore: setHasMoreSessions,
        onItems: setSessions,
        onState: setHistoryState,
      },
    )
  }

  function handleChangeHistoryStatusFilter(filter: SessionNavigationFilter) {
    setHistoryStatusFilter(filter)
    setVisibleSessionCount(SESSION_PAGE_SIZE)
  }

  function handleLoadMoreSessions() {
    setVisibleSessionCount((current) => current + SESSION_PAGE_SIZE)
  }

  async function handleRenameSession(sessionId: string, title: string) {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setHistoryState('failed')
      setHistoryError('Project ID is required to rename a session.')
      return
    }

    setHistoryError(null)
    setHistoryState('loading')
    try {
      await client.updateChatSessionTitle(trimmedProjectId, sessionId, title)
      await handleRefreshHistory(trimmedProjectId)
    } catch (error) {
      setHistoryError(getErrorMessage(error))
      setHistoryState('failed')
    }
  }

  async function handleArchiveSession(sessionId: string) {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setHistoryState('failed')
      setHistoryError('Project ID is required to archive a session.')
      return
    }

    setHistoryError(null)
    setHistoryState('loading')
    try {
      await client.archiveChatSession(trimmedProjectId, sessionId)
      await handleRefreshHistory(trimmedProjectId)
    } catch (error) {
      setHistoryError(getErrorMessage(error))
      setHistoryState('failed')
    }
  }

  async function handleUnarchiveSession(sessionId: string) {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setHistoryState('failed')
      setHistoryError('Project ID is required to unarchive a session.')
      return
    }

    setHistoryError(null)
    setHistoryState('loading')
    try {
      await client.unarchiveChatSession(trimmedProjectId, sessionId)
      await handleRefreshHistory(trimmedProjectId)
    } catch (error) {
      setHistoryError(getErrorMessage(error))
      setHistoryState('failed')
    }
  }

  function handleChangeProjectId(nextProjectId: string) {
    const selectedProject = projects.find((project) => project.id === nextProjectId)
    if (selectedProject !== undefined) {
      if (selectedProject.can_access === false) {
        return
      }
      handleSelectProject(selectedProject)
      return
    }
    setSelectedProjectId(nextProjectId)
  }

  function handleOpenInspectorTab(tab: InspectorTab) {
    setInspectorTab(tab)
    setIsRightDockOpen(true)
  }

  function handlePrimaryViewChange(view: PrimaryView) {
    handleChangeActiveView(view === 'settings' ? settingsModule : view)
  }

  function handleSettingsModuleChange(module: SettingsModule) {
    handleChangeActiveView(module)
    setSettingsModule(module)
    if (module === 'authoring') {
      setAuthoringSubmodule('projects')
    } else if (module === 'observability') {
      setObservabilitySubmodule('summary')
    } else {
      setRuntimeSubmodule('connections')
    }
  }

  function handleSettingsSubmoduleChange(selection: SettingsNavigationSelection) {
    handleChangeActiveView(selection.module)
    setSettingsModule(selection.module)
    if (selection.module === 'authoring') {
      setAuthoringSubmodule(selection.submodule)
    } else if (selection.module === 'observability') {
      setObservabilitySubmodule(selection.submodule)
    } else {
      setRuntimeSubmodule(selection.submodule)
    }
  }

  function handleStartNewSession() {
    handleChangeActiveView('chat')
    setQuestion('')
    setResponse(null)
    setActiveResponseQuestion(null)
    setSelectedSessionId(null)
    setSessionDetail(null)
    setRequestState('idle')
    setRequestError(null)
    setDetailState('idle')
    setDetailError(null)
    resetSourceViewer()
    chatAutoFollowRef.current = true
  }

  function handleNavigateToMessage(messageId: string) {
    pendingFocusMessageIdRef.current = messageId
    handleOpenInspectorTab('context')
  }

  function resetSourceViewer() {
    setSourceViewer({
      citationSnippet: null,
      error: null,
      source: null,
      sourceId: null,
      state: 'idle',
    })
  }

  async function handleOpenSource(sourceId: string, citationSnippet: string | null) {
    const trimmedProjectId = projectId.trim()
    handleOpenInspectorTab('context')
    setSourceViewer({
      citationSnippet,
      error: null,
      source: null,
      sourceId,
      state: 'loading',
    })

    if (trimmedProjectId.length === 0) {
      setSourceViewer({
        citationSnippet,
        error: 'Project ID is required to load source details.',
        source: null,
        sourceId,
        state: 'failed',
      })
      return
    }

    try {
      const source = await client.getSource(trimmedProjectId, sourceId)
      setSourceViewer({
        citationSnippet,
        error: null,
        source,
        sourceId,
        state: 'succeeded',
      })
    } catch (error) {
      setSourceViewer({
        citationSnippet,
        error: getErrorMessage(error),
        source: null,
        sourceId,
        state: 'failed',
      })
    }
  }

  function handleStartSpeechRecognition() {
    const Recognition = getSpeechRecognitionConstructor()
    if (Recognition === null) {
      setSpeechState('failed')
      setSpeechFeedback('Speech recognition is not supported in this browser.')
      return
    }

    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = navigator.language || 'en-US'
    recognition.onresult = (event) => {
      const transcript = extractSpeechTranscript(event)
      if (transcript.length === 0) {
        setSpeechState('failed')
        setSpeechFeedback('Speech recognition returned an empty transcript.')
        return
      }
      setQuestion((current) => appendTranscript(current, transcript))
      setSpeechState('succeeded')
      setSpeechFeedback('Voice transcript added.')
    }
    recognition.onerror = (event) => {
      setSpeechState('failed')
      setSpeechFeedback(`Speech recognition error: ${event.error ?? 'unknown'}`)
    }
    recognition.onend = () => {
      setActiveSpeechRecognition(null)
      setSpeechState((current) => (current === 'loading' ? 'idle' : current))
    }

    try {
      recognition.start()
      setActiveSpeechRecognition(recognition)
      setSpeechState('loading')
      setSpeechFeedback('Listening...')
    } catch (error) {
      setSpeechState('failed')
      setSpeechFeedback(getErrorMessage(error))
    }
  }

  function handleStopSpeechRecognition() {
    activeSpeechRecognition?.stop()
    setActiveSpeechRecognition(null)
    setSpeechState('idle')
    setSpeechFeedback('Transcript stopped.')
  }

  async function handleSelectSession(sessionId: string) {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setDetailState('failed')
      setDetailError('Project ID is required to load session detail.')
      return
    }

    handleChangeActiveView('chat')
    setQuestion('')
    setActiveResponseQuestion(null)
    setSelectedSessionId(sessionId)
    setPriorTurns([])
    setRequestState('idle')
    setRequestError(null)
    resetSourceViewer()
    setDetailState('loading')
    setDetailError(null)

    try {
      const detail = await client.getChatSession(trimmedProjectId, sessionId)
      setSessionDetail(detail)
      const turns = transcriptTurnsFromSessionDetail(detail)
      if (turns.length === 0) {
        setPriorTurns([])
        setResponse(null)
        setActiveResponseQuestion(null)
        setRequestState('idle')
      } else {
        const earlier = turns.slice(0, -1)
        const latest = turns[turns.length - 1]
        setPriorTurns(earlier)
        setResponse({
          answer: latest.answer,
          citations: latest.citations,
          session_id: detail.session.session_id,
          steps: latest.steps,
          tool_calls: latest.tool_calls,
        })
        setActiveResponseQuestion(latest.question)
        setRequestState('succeeded')
      }
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

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedName = projectName.trim()
    if (trimmedName.length === 0) {
      setProjectAuthoringState('failed')
      setProjectAuthoringError('Project name is required.')
      return
    }

    setProjectAuthoringState('loading')
    setProjectAuthoringError(null)

    try {
      const project = await client.createProject({ name: trimmedName })
      setProjects((current) => upsertProject(current, project))
      setSelectedProjectId(project.id)
      setProjectName('')
      setSources([])
      setIngestionJobs([])
      setIngestionRun(null)
      setProjectAuthoringState('succeeded')
    } catch (error) {
      setProjectAuthoringState('failed')
      setProjectAuthoringError(getErrorMessage(error))
    }
  }

  function handleSelectProject(project: Project) {
    if (project.can_access === false) {
      return
    }
    setSelectedProjectId(project.id)
    setSources([])
    setIngestionJobs([])
    setIngestionRun(null)
    setIngestionError(null)
    setIngestionState('idle')
    setSourceAuthoringError(null)
    setSourceAuthoringState('idle')
    setProjectMemberships([])
    setKnowledgeProposals([])
    setKnowledgeReviewError(null)
    setKnowledgeReviewState('idle')
  }

  function setSelectedProjectId(nextProjectId: string) {
    const trimmedProjectId = nextProjectId.trim()
    projectIdRef.current = trimmedProjectId
    setVisibleSessionCount(SESSION_PAGE_SIZE)
    setSessions([])
    setHasMoreSessions(false)
    setSelectedSessionId(null)
    setSessionDetail(null)
    setHistoryError(null)
    setHistoryState(trimmedProjectId.length === 0 ? 'idle' : 'loading')
    syncProjectRuntimeSettings(null)
    setRuntimeState('idle')
    setRuntimeError(null)
    setProjectId(trimmedProjectId)
    if (trimmedProjectId.length === 0) {
      return
    }
    void client
      .updateCurrentUserPreferences({ last_project_id: trimmedProjectId })
      .catch(() => {
        // Local storage remains the fallback when there is no authenticated account.
      })
  }

  async function handleRefreshSources(projectIdOverride?: string) {
    const trimmedProjectId = (projectIdOverride ?? projectId).trim()

    if (trimmedProjectId.length === 0) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError('Project ID is required to refresh sources.')
      return
    }

    setSourceAuthoringState('loading')
    setSourceAuthoringError(null)

    try {
      const response = await client.listSources(trimmedProjectId)
      setSources(response.items)
      setSourceAuthoringState('succeeded')
    } catch (error) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(getErrorMessage(error))
    }
  }

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedProjectId = projectId.trim()
    const trimmedExternalId = sourceExternalId.trim()
    const content = sourceContent

    if (trimmedProjectId.length === 0) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError('Project ID is required to create a source.')
      return
    }
    if (trimmedExternalId.length === 0) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError('External ID is required.')
      return
    }
    if (isTextSourceType(sourceType) && content.trim().length === 0) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(`${sourceType} source requires content.`)
      return
    }
    if (isBinarySourceType(sourceType) && sourceContentBase64.trim().length === 0) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(`${sourceType} source requires a file.`)
      return
    }

    const body = buildSourceCreateBody({
      content,
      contentBase64: sourceContentBase64,
      externalId: trimmedExternalId,
      sourceType,
      tags: sourceTags,
    })

    setSourceAuthoringState('loading')
    setSourceAuthoringError(null)

    try {
      const source = await client.createSource(trimmedProjectId, body)
      setSources((current) => upsertSource(current, source))
      setSourceExternalId('')
      setSourceContent('')
      setSourceContentBase64('')
      setSourceFileName('')
      setSourceTags('')
      setSourceAuthoringState('succeeded')
    } catch (error) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(getErrorMessage(error))
    }
  }

  async function handleSourceFileChange(file: File | null) {
    if (file === null) {
      setSourceContentBase64('')
      setSourceFileName('')
      return
    }
    if (file.size > MAX_SOURCE_FILE_BYTES) {
      setSourceContentBase64('')
      setSourceFileName('')
      setSourceAuthoringState('failed')
      setSourceAuthoringError(
        `${sourceType} source file exceeds the 5 MiB limit.`,
      )
      return
    }
    const buffer = await file.arrayBuffer()
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let index = 0; index < bytes.length; index += 1) {
      binary += String.fromCharCode(bytes[index]!)
    }
    setSourceContentBase64(btoa(binary))
    setSourceFileName(file.name)
    if (sourceExternalId.trim().length === 0) {
      setSourceExternalId(file.name)
    }
  }

  async function handleRefreshAccess() {
    const trimmedProjectId = projectId.trim()

    setAccessManagementState('loading')
    setAccessManagementError(null)

    try {
      const usersResponse = await client.listUsers()
      setUsers(usersResponse.items)

      if (trimmedProjectId.length > 0) {
        const membershipsResponse =
          await client.listProjectMemberships(trimmedProjectId)
        setProjectMemberships(membershipsResponse.items)
      }

      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedLogin = userLogin.trim()
    const trimmedDisplayName = userDisplayName.trim()
    const trimmedAccessToken = userAccessToken.trim()

    if (trimmedLogin.length === 0) {
      setAccessManagementState('failed')
      setAccessManagementError('User login is required.')
      return
    }
    if (trimmedDisplayName.length === 0) {
      setAccessManagementState('failed')
      setAccessManagementError('Display name is required.')
      return
    }

    setAccessManagementState('loading')
    setAccessManagementError(null)

    try {
      const user = await client.createUser({
        access_token: trimmedAccessToken.length > 0 ? trimmedAccessToken : null,
        display_name: trimmedDisplayName,
        login: trimmedLogin,
        system_role: userSystemRole,
      })
      setUsers((current) => upsertUser(current, user))
      setUserLogin('')
      setUserDisplayName('')
      setUserAccessToken('')
      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleSaveProjectMembership(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedProjectId = projectId.trim()
    const trimmedUserId = memberUserId.trim()

    if (trimmedProjectId.length === 0) {
      setAccessManagementState('failed')
      setAccessManagementError('Project ID is required to save membership.')
      return
    }
    if (trimmedUserId.length === 0) {
      setAccessManagementState('failed')
      setAccessManagementError('Member user ID is required.')
      return
    }

    setAccessManagementState('loading')
    setAccessManagementError(null)

    try {
      const membership = await client.upsertProjectMembership(
        trimmedProjectId,
        trimmedUserId,
        { role: memberRole },
      )
      setProjectMemberships((current) => upsertMembership(current, membership))
      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleDeleteProject(project: Project) {
    const confirmed = window.confirm(
      `Soft-delete project "${project.name}"? This hides it from lists.`,
    )
    if (!confirmed) {
      return
    }
    setProjectAuthoringState('loading')
    setProjectAuthoringError(null)
    try {
      await client.deleteProject(project.id)
      setProjects((current) => current.filter((item) => item.id !== project.id))
      if (projectId === project.id) {
        setSelectedProjectId('')
        setSources([])
        setIngestionJobs([])
        setIngestionRun(null)
      }
      setProjectAuthoringState('succeeded')
    } catch (error) {
      setProjectAuthoringState('failed')
      setProjectAuthoringError(getErrorMessage(error))
    }
  }

  async function handleDeleteSource(source: Source) {
    const confirmed = window.confirm(
      `Soft-delete source "${source.external_id}" and cascade its index?`,
    )
    if (!confirmed) {
      return
    }
    setSourceAuthoringState('loading')
    setSourceAuthoringError(null)
    try {
      await client.deleteSource(source.project_id, source.id)
      setSources((current) => current.filter((item) => item.id !== source.id))
      setSourceAuthoringState('succeeded')
    } catch (error) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(getErrorMessage(error))
    }
  }

  async function handleDeleteMembership(membership: ProjectMembership) {
    const confirmed = window.confirm(
      `Remove membership for user ${membership.user_id}?`,
    )
    if (!confirmed) {
      return
    }
    setAccessManagementState('loading')
    setAccessManagementError(null)
    try {
      await client.deleteProjectMembership(
        membership.project_id,
        membership.user_id,
      )
      setProjectMemberships((current) =>
        current.filter((item) => item.id !== membership.id),
      )
      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleDeactivateUser(user: User) {
    const confirmed = window.confirm(
      `Deactivate user "${user.login}"? They will not authenticate while inactive.`,
    )
    if (!confirmed) {
      return
    }
    setAccessManagementState('loading')
    setAccessManagementError(null)
    try {
      const updated = await client.deactivateUser(user.id)
      setUsers((current) => upsertUser(current, updated))
      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleRevokeAccessToken() {
    const trimmedToken = userAccessToken.trim()
    if (trimmedToken.length === 0) {
      setAccessManagementState('failed')
      setAccessManagementError('Access token is required to revoke.')
      return
    }
    const confirmed = window.confirm(
      'Revoke this access token? It will stop authenticating immediately.',
    )
    if (!confirmed) {
      return
    }
    setAccessManagementState('loading')
    setAccessManagementError(null)
    try {
      await client.revokeAccessToken({ access_token: trimmedToken })
      setUserAccessToken('')
      setAccessManagementState('succeeded')
    } catch (error) {
      setAccessManagementState('failed')
      setAccessManagementError(getErrorMessage(error))
    }
  }

  async function handleRefreshKnowledgeProposals() {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError('Project ID is required to refresh proposals.')
      return
    }

    setKnowledgeReviewState('loading')
    setKnowledgeReviewError(null)

    try {
      const response = await client.listKnowledgeProposals(trimmedProjectId, {
        status: 'pending',
      })
      setKnowledgeProposals(response.items)
      setKnowledgeReviewState('succeeded')
    } catch (error) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError(getErrorMessage(error))
    }
  }

  async function handleRefineKnowledgeProposal(proposal: KnowledgeProposal) {
    const trimmedProjectId = projectId.trim()
    const refinedText = proposalDraftText(proposalDrafts, proposal).trim()

    if (trimmedProjectId.length === 0 || refinedText.length === 0) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError('Project ID and refined text are required.')
      return
    }

    setKnowledgeReviewState('loading')
    setKnowledgeReviewError(null)

    try {
      const updated = await client.refineKnowledgeProposal(
        trimmedProjectId,
        proposal.id,
        { refined_text: refinedText },
      )
      setKnowledgeProposals((current) =>
        upsertKnowledgeProposal(current, updated),
      )
      setKnowledgeReviewState('succeeded')
    } catch (error) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError(getErrorMessage(error))
    }
  }

  async function handleApproveKnowledgeProposal(proposal: KnowledgeProposal) {
    const trimmedProjectId = projectId.trim()
    const refinedText = proposalDraftText(proposalDrafts, proposal).trim()

    if (trimmedProjectId.length === 0) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError('Project ID is required to approve proposals.')
      return
    }

    setKnowledgeReviewState('loading')
    setKnowledgeReviewError(null)

    try {
      const updated = await client.approveKnowledgeProposal(
        trimmedProjectId,
        proposal.id,
        {
          refined_text: refinedText.length > 0 ? refinedText : null,
          review_note: null,
        },
      )
      setKnowledgeProposals((current) =>
        upsertKnowledgeProposal(current, updated),
      )
      setKnowledgeReviewState('succeeded')
    } catch (error) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError(getErrorMessage(error))
    }
  }

  async function handleRejectKnowledgeProposal(proposal: KnowledgeProposal) {
    const trimmedProjectId = projectId.trim()
    const reason = (proposalRejectReasons[proposal.id] ?? '').trim()

    if (trimmedProjectId.length === 0 || reason.length === 0) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError('Project ID and rejection reason are required.')
      return
    }

    setKnowledgeReviewState('loading')
    setKnowledgeReviewError(null)

    try {
      const updated = await client.rejectKnowledgeProposal(
        trimmedProjectId,
        proposal.id,
        { reason },
      )
      setKnowledgeProposals((current) =>
        upsertKnowledgeProposal(current, updated),
      )
      setKnowledgeReviewState('succeeded')
    } catch (error) {
      setKnowledgeReviewState('failed')
      setKnowledgeReviewError(getErrorMessage(error))
    }
  }

  async function handleRefreshIngestionJobs(projectIdOverride?: string) {
    const trimmedProjectId = (projectIdOverride ?? projectId).trim()

    if (trimmedProjectId.length === 0) {
      setIngestionState('failed')
      setIngestionError('Project ID is required to refresh ingestion jobs.')
      return
    }

    setIngestionState('loading')
    setIngestionError(null)

    try {
      const response = await client.listIngestionJobs(trimmedProjectId, {
        job_type: 'ingest_source',
      })
      setIngestionJobs(response.items)
      setIngestionState('succeeded')
    } catch (error) {
      setIngestionState('failed')
      setIngestionError(getErrorMessage(error))
    }
  }

  async function handleEnqueueIngestion(source: Source) {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setIngestionState('failed')
      setIngestionError('Project ID is required to enqueue ingestion.')
      return
    }

    setIngestionState('loading')
    setIngestionError(null)

    try {
      const job = await client.enqueueIngestionJob(trimmedProjectId, source.id)
      setIngestionJobs((current) => upsertIngestionJob(current, job))
      setIngestionState('succeeded')
    } catch (error) {
      setIngestionState('failed')
      setIngestionError(getErrorMessage(error))
    }
  }

  async function handleRunNextIngestion() {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setIngestionState('failed')
      setIngestionError('Project ID is required to run ingestion.')
      return
    }

    setIngestionState('loading')
    setIngestionError(null)

    try {
      const run = await client.runNextIngestionJob(trimmedProjectId)
      setIngestionRun(run)
      setIngestionState('succeeded')
      if (run.job_id !== null) {
        await handleRefreshIngestionJobs(trimmedProjectId)
      }
    } catch (error) {
      setIngestionState('failed')
      setIngestionError(getErrorMessage(error))
    }
  }

  async function handleRetryIngestionJob(job: IngestionJob) {
    const trimmedProjectId = projectId.trim()

    if (trimmedProjectId.length === 0) {
      setIngestionState('failed')
      setIngestionError('Project ID is required to retry ingestion.')
      return
    }

    setIngestionState('loading')
    setIngestionError(null)

    try {
      const nextJob = await client.retryIngestionJob(trimmedProjectId, job.id)
      setIngestionJobs((current) => upsertIngestionJob(current, nextJob))
      setIngestionState('succeeded')
    } catch (error) {
      setIngestionState('failed')
      setIngestionError(getErrorMessage(error))
    }
  }

  async function handleRefreshRuntimeModelCatalog() {
    setRuntimeState('loading')
    setRuntimeError(null)

    try {
      const trimmedConnectionId = modelSyncConnectionId.trim()
      const [connections, providerModels] = await Promise.all([
        client.listProviderConnections(),
        client.listProviderModels(
          trimmedConnectionId.length > 0
            ? { connection_id: trimmedConnectionId }
            : undefined,
        ),
      ])
      setRuntimeConnections(connections.items)
      setRuntimeProviderModels(providerModels.items)
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSelectModelCatalogConnection(value: string) {
    setModelSyncConnectionId(value)
    const trimmedConnectionId = value.trim()
    if (trimmedConnectionId.length === 0) {
      setRuntimeProviderModels([])
      setRuntimeError(null)
      setRuntimeState('idle')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const providerModels = await client.listProviderModels({
        connection_id: trimmedConnectionId,
      })
      setRuntimeProviderModels(providerModels.items)
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleRefreshRuntimeGlobalDefaults() {
    setRuntimeState('loading')
    setRuntimeError(null)

    try {
      const [connections, slots, chatModels, providerModels, chatRetrieval] =
        await Promise.all([
          client.listProviderConnections(),
          client.listRuntimeSlotDefaults(),
          client.listChatModels(),
          client.listProviderModels(),
          client.getChatRetrievalSettings(),
        ])
      setRuntimeConnections(connections.items)
      setRuntimeSlots(slots.items)
      setRuntimeChatModels(chatModels.items)
      setRuntimeProviderModels(providerModels.items)
      setRuntimeChatRetrieval(chatRetrieval)
      syncGlobalChatRetrievalFields(chatRetrieval)
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleRefreshRuntimeProjectOverrides() {
    const trimmedProjectId = projectId.trim()
    setRuntimeState('loading')
    setRuntimeError(null)

    try {
      const projectSettingsPromise =
        trimmedProjectId.length > 0
          ? client.getProjectRuntimeSettings(trimmedProjectId)
          : Promise.resolve(null)
      const [connections, providerModels, projectSettings] = await Promise.all([
        client.listProviderConnections(),
        client.listProviderModels(),
        projectSettingsPromise,
      ])
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeConnections(connections.items)
      setRuntimeProviderModels(providerModels.items)
      syncProjectRuntimeSettings(projectSettings)
      setRuntimeState('succeeded')
    } catch (error) {
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  function resetConnectionForm() {
    setEditingConnectionId(null)
    setConnectionProvider('qwen')
    setConnectionType('hosted')
    setConnectionBaseUrl('')
    setConnectionCapabilities(['chat'])
    setConnectionApiKey('')
  }

  function handleRequestEditConnection(connectionId: string) {
    const connection = runtimeConnections.find(
      (item) => item.connection_id === connectionId,
    )
    if (connection === undefined) {
      setRuntimeState('failed')
      setRuntimeError('Connection was not found.')
      return
    }

    setEditingConnectionId(connection.connection_id)
    setConnectionProvider(connection.provider)
    setConnectionType(connection.connection_type)
    setConnectionBaseUrl(connection.base_url ?? '')
    setConnectionCapabilities(
      connection.capabilities.filter((capability) =>
        PROVIDER_CONNECTION_CAPABILITIES.includes(capability),
      ),
    )
    setConnectionApiKey('')
    setDeleteConnectionId(null)
    setDeleteConnectionConfirmation('')
    setRuntimeError(null)
    setRuntimeSubmodule('connections')
  }

  function handleCancelEditConnection() {
    resetConnectionForm()
    setRuntimeError(null)
  }

  async function handleSaveConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const selectedCapabilities = connectionCapabilities.filter((capability) =>
      PROVIDER_CONNECTION_CAPABILITIES.includes(capability),
    )
    if (selectedCapabilities.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Select at least one connection capability.')
      return
    }
    const trimmedApiKey = connectionApiKey.trim()

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const editingConnection =
        editingConnectionId === null
          ? null
          : runtimeConnections.find(
              (connection) => connection.connection_id === editingConnectionId,
            )
      const body = {
        api_key: trimmedApiKey.length > 0 ? trimmedApiKey : null,
        base_url: optionalFilterValue(connectionBaseUrl),
        capabilities: selectedCapabilities,
        connection_type: connectionType,
        metadata: editingConnection?.metadata ?? null,
        provider: connectionProvider,
      }
      const connection =
        editingConnectionId === null
          ? await client.createProviderConnection(body)
          : await client.upsertProviderConnection(editingConnectionId, body)
      setRuntimeConnections((current) => upsertConnection(current, connection))
      setConnectionCheckResults((current) => {
        const next = { ...current }
        delete next[connection.connection_id]
        return next
      })
      setModelSyncConnectionId(connection.connection_id)
      setConnectionApiKey('')
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  function handleRequestDeleteConnection(connectionId: string) {
    setDeleteConnectionId(connectionId)
    setDeleteConnectionConfirmation('')
    setRuntimeError(null)
  }

  function handleCancelDeleteConnection() {
    setDeleteConnectionId(null)
    setDeleteConnectionConfirmation('')
    setRuntimeError(null)
  }

  async function handleCheckProviderConnection(connectionId: string) {
    setCheckingConnectionId(connectionId)
    setRuntimeError(null)
    try {
      const response = await client.checkProviderConnection(connectionId)
      setConnectionCheckResults((current) => ({
        ...current,
        [connectionId]: response,
      }))
      setRuntimeState(response.ok ? 'succeeded' : 'failed')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    } finally {
      setCheckingConnectionId((current) =>
        current === connectionId ? null : current,
      )
    }
  }

  async function handleDeleteConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const connectionId = deleteConnectionId
    if (connectionId === null) {
      return
    }
    if (deleteConnectionConfirmation.trim() !== connectionId) {
      setRuntimeState('failed')
      setRuntimeError('Type the connection ID to confirm deletion.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const response = await client.deleteProviderConnection(connectionId)
      if (!response.deleted) {
        throw new Error('Connection was not deleted.')
      }
      setRuntimeConnections((current) =>
        current.filter((connection) => connection.connection_id !== connectionId),
      )
      setRuntimeProviderModels((current) =>
        current.filter((model) => model.connection_id !== connectionId),
      )
      setRuntimeSlots((current) =>
        current.filter((slot) => slot.connection_id !== connectionId),
      )
      setRuntimeChatModels((current) =>
        current.filter((model) => model.connection_id !== connectionId),
      )
      setConnectionCheckResults((current) => {
        const next = { ...current }
        delete next[connectionId]
        return next
      })
      setProjectRuntimeSettings((current) =>
        current === null
          ? null
          : {
              ...current,
              chat_models: current.chat_models.filter(
                (model) => model.connection_id !== connectionId,
              ),
              slots: current.slots.filter(
                (slot) => slot.connection_id !== connectionId,
              ),
            },
      )
      setModelSyncConnectionId((current) =>
        current === connectionId ? '' : current,
      )
      if (editingConnectionId === connectionId) {
        resetConnectionForm()
      }
      if (globalSlotConnectionId === connectionId) {
        setGlobalSlotConnectionId('')
        setGlobalSlotModelId('')
      }
      if (globalChatConnectionId === connectionId) {
        setGlobalChatConnectionId('')
        setGlobalChatModelId('')
      }
      if (projectSlotConnectionId === connectionId) {
        setProjectSlotConnectionId('')
        setProjectSlotModelId('')
      }
      setDeleteConnectionId(null)
      setDeleteConnectionConfirmation('')
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSyncProviderModels(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedConnectionId = modelSyncConnectionId.trim()
    if (trimmedConnectionId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Model sync connection is required.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const response = await client.syncProviderModels(trimmedConnectionId)
      setRuntimeProviderModels((current) =>
        upsertProviderModels(current, response.items),
      )
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSaveGlobalSlot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedConnectionId = globalSlotConnectionId.trim()
    const trimmedModelId = globalSlotModelId.trim()
    if (trimmedConnectionId.length === 0 || trimmedModelId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Global slot connection and model are required.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const slot = await client.upsertRuntimeSlotDefault(globalSlot, {
        connection_id: trimmedConnectionId,
        model_id: trimmedModelId,
      })
      setRuntimeSlots((current) => upsertRuntimeSlot(current, slot))
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSaveGlobalChatModel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedConnectionId = globalChatConnectionId.trim()
    const trimmedModelId = globalChatModelId.trim()
    if (trimmedConnectionId.length === 0 || trimmedModelId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Chat connection and model are required.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const model = await client.upsertChatModel({
        connection_id: trimmedConnectionId,
        make_default: true,
        model_id: trimmedModelId,
      })
      setRuntimeChatModels((current) => upsertChatModel(current, model))
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedProjectId = projectId.trim()
    const validationError = validateChatRetrievalSettings({
      candidateLimit: globalChatRerankCandidateLimit,
      rerankEnabled: globalChatRerankEnabled,
      retrievalLimit: globalChatRetrievalLimit,
    })
    if (validationError !== null) {
      setRuntimeState('failed')
      setRuntimeError(validationError)
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const settings = await client.updateChatRetrievalSettings({
        retrieval_limit: globalChatRetrievalLimit,
        rerank_enabled: globalChatRerankEnabled,
        rerank_candidate_limit: globalChatRerankCandidateLimit,
      })
      setRuntimeChatRetrieval(settings)
      syncGlobalChatRetrievalFields(settings)
      if (trimmedProjectId.length > 0) {
        const projectSettings =
          await client.getProjectRuntimeSettings(trimmedProjectId)
        if (
          !syncProjectRuntimeSettingsForProject(
            trimmedProjectId,
            projectSettings,
          )
        ) {
          return
        }
      }
      setRuntimeState('succeeded')
    } catch (error) {
      if (
        trimmedProjectId.length > 0 &&
        !isCurrentProjectRuntimeRequest(trimmedProjectId)
      ) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSaveProjectOverride(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedProjectId = projectId.trim()
    const trimmedConnectionId = projectSlotConnectionId.trim()
    const trimmedModelId = projectSlotModelId.trim()
    if (
      trimmedProjectId.length === 0 ||
      trimmedConnectionId.length === 0 ||
      trimmedModelId.length === 0
    ) {
      setRuntimeState('failed')
      setRuntimeError('Project, connection and model are required.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      await client.upsertProjectRuntimeSlotOverride(trimmedProjectId, projectSlot, {
        connection_id: trimmedConnectionId,
        model_id: trimmedModelId,
      })
      const settings = await client.getProjectRuntimeSettings(trimmedProjectId)
      if (!syncProjectRuntimeSettingsForProject(trimmedProjectId, settings)) {
        return
      }
      setRuntimeState('succeeded')
    } catch (error) {
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleResetProjectSlot(slot: string) {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Project ID is required to reset runtime overrides.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      await client.deleteProjectRuntimeSlotOverride(trimmedProjectId, slot)
      const settings = await client.getProjectRuntimeSettings(trimmedProjectId)
      if (!syncProjectRuntimeSettingsForProject(trimmedProjectId, settings)) {
        return
      }
      setRuntimeState('succeeded')
    } catch (error) {
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleSaveProjectChatRetrieval(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Project ID is required for project retrieval settings.')
      return
    }
    const validationError = validateChatRetrievalSettings({
      candidateLimit: projectChatRerankCandidateLimit,
      rerankEnabled: projectChatRerankEnabled,
      retrievalLimit: projectChatRetrievalLimit,
    })
    if (validationError !== null) {
      setRuntimeState('failed')
      setRuntimeError(validationError)
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      await client.upsertProjectChatRetrievalSettings(trimmedProjectId, {
        retrieval_limit: projectChatRetrievalLimit,
        rerank_enabled: projectChatRerankEnabled,
        rerank_candidate_limit: projectChatRerankCandidateLimit,
      })
      const settings = await client.getProjectRuntimeSettings(trimmedProjectId)
      if (!syncProjectRuntimeSettingsForProject(trimmedProjectId, settings)) {
        return
      }
      setRuntimeState('succeeded')
    } catch (error) {
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleResetProjectChatRetrieval() {
    const trimmedProjectId = projectId.trim()
    if (trimmedProjectId.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Project ID is required to reset chat retrieval.')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      await client.deleteProjectChatRetrievalSettings(trimmedProjectId)
      const settings = await client.getProjectRuntimeSettings(trimmedProjectId)
      if (!syncProjectRuntimeSettingsForProject(trimmedProjectId, settings)) {
        return
      }
      setRuntimeState('succeeded')
    } catch (error) {
      if (!isCurrentProjectRuntimeRequest(trimmedProjectId)) {
        return
      }
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  function syncGlobalChatRetrievalFields(settings: ChatRetrievalSettings) {
    setGlobalChatRetrievalLimit(settings.retrieval_limit)
    setGlobalChatRerankEnabled(settings.rerank_enabled)
    setGlobalChatRerankCandidateLimit(settings.rerank_candidate_limit)
  }

  function syncProjectRuntimeSettings(settings: ProjectRuntimeSettings | null) {
    setProjectRuntimeSettings(settings)
    if (settings === null) {
      resetProjectRuntimeFormFields()
      return
    }
    setProjectChatRetrievalLimit(settings.chat_retrieval.retrieval_limit)
    setProjectChatRerankEnabled(settings.chat_retrieval.rerank_enabled)
    setProjectChatRerankCandidateLimit(
      settings.chat_retrieval.rerank_candidate_limit,
    )
  }

  function syncProjectRuntimeSettingsForProject(
    requestedProjectId: string,
    settings: ProjectRuntimeSettings | null,
  ): boolean {
    if (!isCurrentProjectRuntimeRequest(requestedProjectId)) {
      return false
    }
    syncProjectRuntimeSettings(settings)
    return true
  }

  function isCurrentProjectRuntimeRequest(requestedProjectId: string): boolean {
    return projectIdRef.current === requestedProjectId.trim()
  }

  function resetProjectRuntimeFormFields() {
    setProjectSlot('chat')
    setProjectSlotConnectionId('')
    setProjectSlotModelId('')
    setProjectChatRetrievalLimit(DEFAULT_RETRIEVAL_LIMIT)
    setProjectChatRerankEnabled(true)
    setProjectChatRerankCandidateLimit(DEFAULT_RERANK_CANDIDATE_LIMIT)
  }

  function handleChangeActiveView(view: ActiveView) {
    const nextView = normalizeActiveView(view)
    pushRouteForActiveView(nextView)
    setActiveView(nextView)
    if (isSettingsModule(nextView)) {
      setSettingsModule(nextView)
    }
  }

  const activeSettingsModule = settingsModule

  return (
    <AppShell
      isBackgroundInert={isRightDockOverlay}
      isLeftSidebarOpen={isLeftSidebarOpen}
      isRightDockOpen={isRightDockOpen}
      primaryView={primaryView}
      sidebar={
        <AppSidebar
          accountModule={accountModule}
          authoringSubmodule={authoringSubmodule}
          canLoadMoreSessions={hasMoreSessions}
          error={historyError}
          isOpen={isLeftSidebarOpen}
          observabilitySubmodule={observabilitySubmodule}
          onArchiveSession={(sessionId) => void handleArchiveSession(sessionId)}
          onAccountModuleChange={setAccountModule}
          onLoadMoreSessions={handleLoadMoreSessions}
          onPrimaryViewChange={handlePrimaryViewChange}
          onProjectIdChange={handleChangeProjectId}
          onRenameSession={(sessionId, title) =>
            void handleRenameSession(sessionId, title)
          }
          onSelectSession={(sessionId) => void handleSelectSession(sessionId)}
          onSettingsModuleChange={handleSettingsModuleChange}
          onSettingsSubmoduleChange={handleSettingsSubmoduleChange}
          onStartNewSession={handleStartNewSession}
          onStatusFilterChange={handleChangeHistoryStatusFilter}
          onToggle={() => setIsLeftSidebarOpen((current) => !current)}
          onUnarchiveSession={(sessionId) =>
            void handleUnarchiveSession(sessionId)
          }
          primaryView={primaryView}
          projectId={projectId}
          projectState={projectAuthoringState}
          projects={projects}
          runtimeSubmodule={runtimeSubmodule}
          selectedSessionId={selectedSessionId}
          sessions={sessions}
          sessionState={historyState}
          settingsModule={settingsModule}
          statusFilter={historyStatusFilter}
        />
      }
      topline={
        <WorkspaceTopline
          isChatWorkspace={primaryView === 'chat'}
          isLeftSidebarOpen={isLeftSidebarOpen}
          projectId={projectId}
          projects={projects}
          selectedSessionId={selectedSessionId}
          sessionDetail={sessionDetail}
          sessions={sessions}
        />
      }
    >
      {primaryView === 'chat' ? (
          <ChatWorkspaceGrid isRightDockInline={isRightDockInline}>
            {isRightDockOverlay ? (
              <Button
                aria-label="Close Workspace Inspector"
                // tabIndex=-1 keeps the full-screen scrim out of Tab order; Escape / X still close.
                className="fixed inset-0 z-[60] h-auto cursor-pointer rounded-none border-0 bg-[var(--overlay-backdrop)] p-0 text-transparent hover:bg-[var(--overlay-backdrop)]"
                data-testid="inspector-backdrop"
                onClick={() => setIsRightDockOpen(false)}
                slotName="inspector-backdrop"
                tabIndex={-1}
                type="button"
                variant="ghost"
              />
            ) : null}

            <div
              className="min-h-0 min-w-0"
              data-slot="chat-workspace-inert-host"
              {...(isRightDockOverlay ? { inert: true } : {})}
            >
              <ChatWorkspacePanel
                activeResponseQuestion={activeResponseQuestion}
                appliedMemories={appliedMemories}
                continuingSessionId={selectedSessionId}
                drafts={knowledgeDrafts}
                isAsking={isAsking}
                isContextInspectorActive={
                  isRightDockOpen && inspectorTab === 'context'
                }
                isMinimapInspectorActive={
                  isRightDockOpen && inspectorTab === 'minimap'
                }
                isSpeechSupported={isSpeechSupported}
                onCancelRequest={handleCancelRequest}
                onOpenContextInspector={() => handleOpenInspectorTab('context')}
                onOpenMinimapInspector={() => handleOpenInspectorTab('minimap')}
                onOpenSource={(sourceId, citationSnippet) =>
                  void handleOpenSource(sourceId, citationSnippet)
                }
                onQuestionChange={setQuestion}
                onRefineKnowledgeDraft={handleRefineKnowledgeDraft}
                onRetryLastQuestion={handleRetryLastQuestion}
                onStartSpeechRecognition={handleStartSpeechRecognition}
                onStopSpeechRecognition={handleStopSpeechRecognition}
                onSubmit={handleSubmit}
                onSubmitKnowledgeDraft={handleSubmitKnowledgeDraft}
                onTranscriptScroll={handleChatTranscriptScroll}
                priorTurns={priorTurns}
                providerUsage={
                  response !== null &&
                  sessionDetail?.session.session_id === response.session_id
                    ? sessionDetail.provider_usage
                    : []
                }
                question={question}
                requestError={requestError}
                requestState={requestState}
                response={response}
                setDrafts={setKnowledgeDrafts}
                speechFeedback={speechFeedback}
                speechState={speechState}
                transcriptRef={chatTranscriptRef}
              />
            </div>

            {isRightDockOpen ? (
              <WorkspaceInspectorPanel
                activeTab={inspectorTab}
                detail={sessionDetail}
                detailError={detailError}
                detailState={detailState}
                layout={isRightDockInline ? 'inline' : 'overlay'}
                onClose={() => setIsRightDockOpen(false)}
                onNavigateMessage={handleNavigateToMessage}
                onActiveTabChange={handleOpenInspectorTab}
                onOpenSource={(sourceId, citationSnippet) =>
                  void handleOpenSource(sourceId, citationSnippet)
                }
                sourceViewer={sourceViewer}
              />
            ) : null}
          </ChatWorkspaceGrid>
        ) : primaryView === 'account' ? (
          accountModule === 'appearance' ? (
            <AppearanceSettingsPanel onThemeChange={setTheme} theme={theme} />
          ) : (
            <UserMemoryPanel apiClient={client} projectId={projectId} />
          )
        ) : (
          <SettingsPanel>
            {activeSettingsModule === 'observability' ? (
              <ObservabilityPanel
                activeSubmodule={observabilitySubmodule}
                createdAtFrom={createdAtFrom}
                createdAtTo={createdAtTo}
                error={observabilityError}
                onCreatedAtFromChange={setCreatedAtFrom}
                onCreatedAtToChange={setCreatedAtTo}
                onProjectIdChange={handleChangeProjectId}
                onRefresh={() => void handleRefreshObservability()}
                onStatusChange={setObservabilityStatus}
                onSubmoduleChange={(submodule) =>
                  handleSettingsSubmoduleChange({
                    module: 'observability',
                    submodule,
                  })
                }
                projectId={projectId}
                state={observabilityState}
                status={observabilityStatus}
                summary={observabilitySummary}
              />
            ) : activeSettingsModule === 'runtime' ? (
              <RuntimeSettingsPanel
                activeSubmodule={runtimeSubmodule}
                connectionApiKey={connectionApiKey}
                chatConnectionId={globalChatConnectionId}
                chatModelId={globalChatModelId}
                chatModels={runtimeChatModels}
                chatRetrievalSettings={runtimeChatRetrieval}
                checkingConnectionId={checkingConnectionId}
                connectionBaseUrl={connectionBaseUrl}
                connectionCheckResults={connectionCheckResults}
                connectionCapabilities={connectionCapabilities}
                connectionProvider={connectionProvider}
                connectionType={connectionType}
                connections={runtimeConnections}
                deleteConnectionConfirmation={deleteConnectionConfirmation}
                deleteConnectionId={deleteConnectionId}
                editingConnectionId={editingConnectionId}
                error={runtimeError}
                globalChatRerankCandidateLimit={
                  globalChatRerankCandidateLimit
                }
                globalChatRerankEnabled={globalChatRerankEnabled}
                globalChatRetrievalLimit={globalChatRetrievalLimit}
                globalSlot={globalSlot}
                globalSlotConnectionId={globalSlotConnectionId}
                globalSlotModelId={globalSlotModelId}
                onChatConnectionIdChange={setGlobalChatConnectionId}
                onChatModelIdChange={setGlobalChatModelId}
                onConnectionBaseUrlChange={setConnectionBaseUrl}
                onConnectionCapabilitiesChange={setConnectionCapabilities}
                onConnectionApiKeyChange={setConnectionApiKey}
                onConnectionProviderChange={setConnectionProvider}
                onConnectionTypeChange={setConnectionType}
                onCancelDeleteConnection={handleCancelDeleteConnection}
                onCancelEditConnection={handleCancelEditConnection}
                onCheckConnection={(connectionId) =>
                  void handleCheckProviderConnection(connectionId)
                }
                onDeleteConnection={(event) => void handleDeleteConnection(event)}
                onDeleteConnectionConfirmationChange={
                  setDeleteConnectionConfirmation
                }
                onGlobalChatRerankCandidateLimitChange={
                  setGlobalChatRerankCandidateLimit
                }
                onGlobalChatRerankEnabledChange={setGlobalChatRerankEnabled}
                onGlobalChatRetrievalLimitChange={setGlobalChatRetrievalLimit}
                onGlobalSlotChange={setGlobalSlot}
                onGlobalSlotConnectionIdChange={setGlobalSlotConnectionId}
                onGlobalSlotModelIdChange={setGlobalSlotModelId}
                onProjectChatRerankCandidateLimitChange={
                  setProjectChatRerankCandidateLimit
                }
                onProjectChatRerankEnabledChange={setProjectChatRerankEnabled}
                onProjectChatRetrievalLimitChange={setProjectChatRetrievalLimit}
                onProjectSlotChange={setProjectSlot}
                onProjectSlotConnectionIdChange={setProjectSlotConnectionId}
                onProjectSlotModelIdChange={setProjectSlotModelId}
                onRefreshGlobalDefaults={() =>
                  void handleRefreshRuntimeGlobalDefaults()
                }
                onRefreshModelCatalog={() =>
                  void handleRefreshRuntimeModelCatalog()
                }
                onRefreshProjectOverrides={() =>
                  void handleRefreshRuntimeProjectOverrides()
                }
                onResetProjectChatRetrieval={() =>
                  void handleResetProjectChatRetrieval()
                }
                onResetProjectSlot={(slot) => void handleResetProjectSlot(slot)}
                onRequestDeleteConnection={handleRequestDeleteConnection}
                onRequestEditConnection={handleRequestEditConnection}
                onSaveConnection={(event) => void handleSaveConnection(event)}
                onSaveGlobalChatModel={(event) =>
                  void handleSaveGlobalChatModel(event)
                }
                onSaveGlobalChatRetrieval={(event) =>
                  void handleSaveGlobalChatRetrieval(event)
                }
                onSaveGlobalSlot={(event) => void handleSaveGlobalSlot(event)}
                onSaveProjectChatRetrieval={(event) =>
                  void handleSaveProjectChatRetrieval(event)
                }
                onSaveProjectOverride={(event) =>
                  void handleSaveProjectOverride(event)
                }
                onSyncProviderModels={(event) =>
                  void handleSyncProviderModels(event)
                }
                onModelSyncConnectionIdChange={(value) =>
                  void handleSelectModelCatalogConnection(value)
                }
                projectId={projectId}
                projectChatRerankCandidateLimit={
                  projectChatRerankCandidateLimit
                }
                projectChatRerankEnabled={projectChatRerankEnabled}
                projectChatRetrievalLimit={projectChatRetrievalLimit}
                projectRuntimeSettings={projectRuntimeSettings}
                projectSlot={projectSlot}
                projectSlotConnectionId={projectSlotConnectionId}
                projectSlotModelId={projectSlotModelId}
                modelSyncConnectionId={modelSyncConnectionId}
                providerModels={runtimeProviderModels}
                slots={runtimeSlots}
                state={runtimeState}
              />
            ) : authoringSubmodule === 'retrieval' ? (
              <RetrievalPlaygroundPanel client={client} projectId={projectId} />
            ) : (
              <AuthoringPanel
                activeSubmodule={authoringSubmodule}
                accessError={accessManagementError}
                accessState={accessManagementState}
                ingestionError={ingestionError}
                ingestionJobs={ingestionJobs}
                ingestionRun={ingestionRun}
                ingestionState={ingestionState}
                knowledgeProposals={knowledgeProposals}
                knowledgeReviewError={knowledgeReviewError}
                knowledgeReviewState={knowledgeReviewState}
                memberRole={memberRole}
                memberUserId={memberUserId}
                memberships={projectMemberships}
                onCreateProject={(event) => void handleCreateProject(event)}
                onCreateSource={(event) => void handleCreateSource(event)}
                onCreateUser={(event) => void handleCreateUser(event)}
                onDeactivateUser={(user) => void handleDeactivateUser(user)}
                onDeleteMembership={(membership) =>
                  void handleDeleteMembership(membership)
                }
                onDeleteProject={(project) => void handleDeleteProject(project)}
                onDeleteSource={(source) => void handleDeleteSource(source)}
                onEnqueueIngestion={(source) => void handleEnqueueIngestion(source)}
                onApproveKnowledgeProposal={(proposal) =>
                  void handleApproveKnowledgeProposal(proposal)
                }
                onMemberRoleChange={setMemberRole}
                onMemberUserIdChange={setMemberUserId}
                onProjectIdChange={handleChangeProjectId}
                onProjectNameChange={setProjectName}
                onProposalDraftChange={(proposalId, value) =>
                  setProposalDrafts((current) => ({
                    ...current,
                    [proposalId]: value,
                  }))
                }
                onProposalRejectReasonChange={(proposalId, value) =>
                  setProposalRejectReasons((current) => ({
                    ...current,
                    [proposalId]: value,
                  }))
                }
                onRefreshAccess={() => void handleRefreshAccess()}
                onRefreshIngestionJobs={() => void handleRefreshIngestionJobs()}
                onRefreshKnowledgeProposals={() =>
                  void handleRefreshKnowledgeProposals()
                }
                onRefreshSources={() => void handleRefreshSources()}
                onRefineKnowledgeProposal={(proposal) =>
                  void handleRefineKnowledgeProposal(proposal)
                }
                onRejectKnowledgeProposal={(proposal) =>
                  void handleRejectKnowledgeProposal(proposal)
                }
                onRetryIngestionJob={(job) => void handleRetryIngestionJob(job)}
                onRevokeAccessToken={() => void handleRevokeAccessToken()}
                onRunNextIngestion={() => void handleRunNextIngestion()}
                onSaveProjectMembership={(event) =>
                  void handleSaveProjectMembership(event)
                }
                onSelectProject={handleSelectProject}
                onSourceContentChange={setSourceContent}
                onSourceExternalIdChange={setSourceExternalId}
                onSourceFileChange={(file) => void handleSourceFileChange(file)}
                onSourceTagsChange={setSourceTags}
                onSourceTypeChange={(value) => {
                  setSourceType(value)
                  if (!isBinarySourceType(value)) {
                    setSourceContentBase64('')
                    setSourceFileName('')
                  }
                  if (!isTextSourceType(value)) {
                    setSourceContent('')
                  }
                }}
                onUserAccessTokenChange={setUserAccessToken}
                onUserDisplayNameChange={setUserDisplayName}
                onUserLoginChange={setUserLogin}
                onUserSystemRoleChange={setUserSystemRole}
                projectError={projectAuthoringError}
                projectId={projectId}
                projectName={projectName}
                projectState={projectAuthoringState}
                projects={projects}
                proposalDrafts={proposalDrafts}
                proposalRejectReasons={proposalRejectReasons}
                sourceContent={sourceContent}
                sourceError={sourceAuthoringError}
                sourceExternalId={sourceExternalId}
                sourceFileName={sourceFileName}
                sourceState={sourceAuthoringState}
                sourceTags={sourceTags}
                sourceType={sourceType}
                sources={sources}
                userAccessToken={userAccessToken}
                userDisplayName={userDisplayName}
                userLogin={userLogin}
                userSystemRole={userSystemRole}
                users={users}
              />
            )}
          </SettingsPanel>
        )}
    </AppShell>
  )
}

function SettingsPanel({ children }: { children: ReactNode }) {
  return (
    <section
      className="grid gap-4"
      data-slot="settings-shell"
      aria-labelledby="settings-title"
    >
      <header
        className="flex items-end justify-between"
        data-slot="settings-shell-header"
      >
        <div>
          <h2
            className="text-xl font-semibold leading-tight text-foreground"
            id="settings-title"
          >
            Settings
          </h2>
        </div>
      </header>
      <div className="grid min-w-0 gap-4" data-slot="settings-section-body">
        {children}
      </div>
    </section>
  )
}

function AppearanceSettingsPanel({
  onThemeChange,
  theme,
}: {
  onThemeChange(theme: Theme): void
  theme: Theme
}) {
  return (
    <Panel
      role="region"
      aria-labelledby="appearance-settings-title"
      className="grid gap-4 p-4 max-[680px]:gap-0.5 max-[680px]:p-0.5"
    >
      <header className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between max-[680px]:gap-0.5">
        <div className="grid gap-1 max-[680px]:gap-0.5">
          <p className="text-xs font-bold uppercase leading-none text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter">
            My Account
          </p>
          <h2
            className="text-lg font-semibold leading-tight text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug"
            id="appearance-settings-title"
          >
            Appearance
          </h2>
        </div>
        <StatusBadge className="w-fit">
          {THEMES.find((option) => option.id === theme)?.label ?? theme}
        </StatusBadge>
      </header>

      <PanelDescription>Choose the interface palette.</PanelDescription>

      <div className="grid gap-3 sm:grid-cols-3 max-[680px]:gap-0.5">
        {THEMES.map((option) => {
          const active = option.id === theme
          return (
            <Button
              aria-pressed={active}
              className={cn(
                'grid h-auto w-full min-w-0 justify-stretch gap-3 rounded-md border border-border bg-card p-3 text-left text-foreground max-[680px]:gap-0.5 max-[680px]:p-0.5',
                'hover:bg-primary/15',
                active &&
                  'border-primary bg-primary/25 focus-visible:ring-primary',
              )}
              data-state={active ? 'active' : 'inactive'}
              key={option.id}
              onClick={() => onThemeChange(option.id)}
              slotName="theme-option"
              type="button"
              variant="ghost"
            >
              <span
                aria-hidden="true"
                className="relative grid min-h-20 gap-2 rounded-md border border-border p-3 max-[680px]:min-h-12 max-[680px]:gap-0.5 max-[680px]:p-0.5"
                data-slot="theme-swatch"
                style={{ background: option.swatch.bg }}
              >
                <span
                  className="block h-2 rounded-full max-[680px]:h-1"
                  data-slot="theme-swatch-line-strong"
                  style={{ background: option.swatch.fg }}
                />
                <span
                  className="block h-2 w-3/4 rounded-full max-[680px]:h-1"
                  data-slot="theme-swatch-line-muted"
                  style={{ background: option.swatch.muted }}
                />
                <span
                  className="absolute bottom-3 right-3 block h-3 w-12 rounded-full max-[680px]:bottom-1 max-[680px]:right-1 max-[680px]:h-2 max-[680px]:w-8"
                  data-slot="theme-swatch-accent"
                  style={{ background: option.swatch.accent }}
                />
              </span>
              <span className="grid gap-1 max-[680px]:gap-0.5">
                <span className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 text-sm font-semibold leading-tight text-foreground max-[680px]:gap-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {option.label}
                  {active ? (
                    <span
                      className="inline-block size-2.5 rounded-full bg-primary max-[680px]:size-2"
                      aria-hidden="true"
                    />
                  ) : null}
                </span>
                <span className="text-xs leading-relaxed text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                  {option.description}
                </span>
              </span>
            </Button>
          )
        })}
      </div>
    </Panel>
  )
}

async function refreshHistory(
  client: ApiClient,
  projectId: string,
  statusFilter: SessionNavigationFilter,
  limit: number,
  callbacks: {
    onError(error: string | null): void
    onHasMore(hasMore: boolean): void
    onItems(items: ChatSessionSummary[]): void
    onState(state: RequestState): void
  },
) {
  callbacks.onState('loading')
  try {
    const history = await client.listChatSessions(projectId, {
      archived: statusFilter === 'archived',
      limit,
    })
    const items =
      statusFilter === 'training'
        ? history.items.filter(sessionHasTraining)
        : history.items
    callbacks.onError(null)
    callbacks.onItems(items)
    callbacks.onHasMore(history.next_cursor !== null)
    callbacks.onState('succeeded')
  } catch (error) {
    callbacks.onError(getErrorMessage(error))
    callbacks.onHasMore(false)
    callbacks.onState('failed')
  }
}

function sessionHasTraining(session: ChatSessionSummary): boolean {
  return session.has_pending_training || session.has_approved_training
}

function getDefaultApiBaseUrl(): string {
  const configured = (
    import.meta.env.VITE_ADAPTIVE_RAG_API_BASE_URL ?? ''
  ).trim()
  return configured.length > 0 ? configured : DEFAULT_API_BASE_URL
}

function getDefaultApiAuthToken(): string | null {
  const configured = (import.meta.env.VITE_ADAPTIVE_RAG_AUTH_TOKEN ?? '').trim()
  return configured.length > 0 ? configured : null
}

function readInitialLeftSidebarOpen(): boolean {
  if (typeof window === 'undefined') {
    return true
  }

  if (typeof window.matchMedia === 'function') {
    return window.matchMedia('(min-width: 681px)').matches
  }

  return window.innerWidth > 680
}

function readIsRightDockInlineViewport(): boolean {
  if (typeof window === 'undefined') {
    return true
  }
  return window.innerWidth >= RIGHT_DOCK_INLINE_WIDTH_PX
}

function useIsRightDockInlineViewport(): boolean {
  const [isInline, setIsInline] = useState(readIsRightDockInlineViewport)

  useEffect(() => {
    const onResize = () => setIsInline(readIsRightDockInlineViewport())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return isInline
}

function normalizeActiveView(view: ActiveView): ActiveView {
  return view === 'settings' ? 'authoring' : view
}

function isSettingsModule(view: ActiveView): view is SettingsModule {
  return view === 'authoring' || view === 'observability' || view === 'runtime'
}

function readActiveViewFromRoute(): ActiveView {
  if (typeof window === 'undefined') {
    return 'chat'
  }

  const pathname = window.location.pathname.replace(/\/+$/, '') || '/'
  if (pathname === '/' || pathname === '/chat') {
    return 'chat'
  }
  if (pathname === '/account') {
    return 'account'
  }
  if (pathname === '/settings' || pathname === '/settings/authoring') {
    return 'authoring'
  }
  if (pathname === '/settings/observability') {
    return 'observability'
  }
  if (pathname === '/settings/runtime') {
    return 'runtime'
  }
  return 'chat'
}

function replaceRouteForActiveView(view: ActiveView) {
  updateRouteForActiveView(view, 'replace')
}

function pushRouteForActiveView(view: ActiveView) {
  updateRouteForActiveView(view, 'push')
}

function updateRouteForActiveView(
  view: ActiveView,
  mode: 'push' | 'replace',
) {
  if (typeof window === 'undefined') {
    return
  }

  const nextView = normalizeActiveView(view)
  const nextPath = ACTIVE_VIEW_ROUTES[nextView]
  if (window.location.pathname === nextPath) {
    return
  }

  const state = { activeView: nextView }
  if (mode === 'replace') {
    window.history.replaceState(state, '', nextPath)
    return
  }
  window.history.pushState(state, '', nextPath)
}

function readPersistedProjectId(): string {
  try {
    return localStorage.getItem(PROJECT_STORAGE_KEY)?.trim() ?? ''
  } catch {
    return ''
  }
}

function persistProjectId(projectId: string): void {
  const trimmedProjectId = projectId.trim()
  try {
    if (trimmedProjectId.length === 0) {
      localStorage.removeItem(PROJECT_STORAGE_KEY)
      return
    }
    localStorage.setItem(PROJECT_STORAGE_KEY, trimmedProjectId)
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return operatorSafeMessage(error.message)
  }
  if (error instanceof Error) {
    return operatorSafeMessage(error.message)
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

function appendChatStep(
  response: ChatResponseBody | null,
  step: ChatStepEvent,
): ChatResponseBody {
  const current = response ?? emptyChatResponse()
  return {
    ...current,
    steps: applyChatStepEvent(current.steps ?? [], step),
  }
}

function withChatSteps(
  response: ChatResponseBody,
  steps: ChatStepEvent[],
): ChatResponseBody {
  return steps.length === 0
    ? response
    : {
        ...response,
        steps,
      }
}

function emptyChatResponse(): ChatResponseBody {
  return {
    answer: '',
    citations: [],
    session_id: null,
    steps: [],
    tool_calls: [],
  }
}

function chatResponseFromSessionDetail(
  detail: ChatSessionDetailResponse,
): ChatResponseBody {
  const turns = transcriptTurnsFromSessionDetail(detail)
  const latest = turns[turns.length - 1]
  if (latest === undefined) {
    return emptyChatResponse()
  }
  return {
    answer: latest.answer,
    citations: latest.citations,
    session_id: detail.session.session_id,
    steps: latest.steps,
    tool_calls: latest.tool_calls,
  }
}

function transcriptTurnsFromSessionDetail(
  detail: ChatSessionDetailResponse,
): ChatTranscriptTurn[] {
  const turns: ChatTranscriptTurn[] = []
  const messages = detail.messages
  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index]
    if (message?.role !== 'user') {
      continue
    }
    const question = message.content.trim()
    if (question.length === 0) {
      continue
    }
    let assistantIndex = -1
    for (let j = index + 1; j < messages.length; j += 1) {
      if (messages[j]?.role === 'user') {
        break
      }
      if (messages[j]?.role === 'assistant') {
        assistantIndex = j
        break
      }
    }
    if (assistantIndex < 0) {
      continue
    }
    const assistantMessage = messages[assistantIndex]
    const turnStartMs = Date.parse(message.created_at)
    let turnEndMs = Number.POSITIVE_INFINITY
    for (let j = assistantIndex + 1; j < messages.length; j += 1) {
      if (messages[j]?.role === 'user') {
        turnEndMs = Date.parse(messages[j].created_at)
        break
      }
    }
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
    turns.push({
      id: assistantMessage?.message_id ?? `turn-${index}`,
      question,
      answer: assistantMessage?.content ?? '',
      citations: turnRetrievalRuns.flatMap((run) =>
        run.retrieved_chunks.map((chunk) => retrievalResultFromHistory(chunk)),
      ),
      steps: parseChatStepsFromMetadata(assistantMessage?.metadata ?? null),
      tool_calls: turnToolCalls.map((call) =>
        chatToolCallFromHistory(call, turnRetrievalRuns),
      ),
    })
  }
  return turns
}

function extractLatestUserQuestion(detail: ChatSessionDetailResponse): string | null {
  const latestUserMessage = [...detail.messages]
    .reverse()
    .find((message) => message.role === 'user' && message.content.trim().length > 0)
  return latestUserMessage?.content.trim() ?? null
}

function retrievalResultFromHistory(
  chunk: ChatHistoryRetrievedChunk,
): RetrievalResult {
  const citation = chunk.citation
  // chunk_id may be null after source soft-delete cascade (ON DELETE SET NULL).
  const resolvedChunkId =
    chunk.chunk_id ??
    getCitationString(citation, 'chunk_id') ??
    chunk.retrieved_chunk_id
  const sourceId =
    getCitationString(citation, 'source_id') ??
    getCitationString(citation, 'source_external_id') ??
    resolvedChunkId
  const sourceExternalId =
    getCitationString(citation, 'source_external_id') ?? sourceId

  return {
    chunk_id: resolvedChunkId,
    citation: {
      char_end: getJsonNumber(citation, 'char_end') ?? 0,
      char_start: getJsonNumber(citation, 'char_start') ?? 0,
      chunk_id: getCitationString(citation, 'chunk_id') ?? resolvedChunkId,
      document_id: getCitationString(citation, 'document_id') ?? '',
      document_stable_id:
        getCitationString(citation, 'document_stable_id') ?? sourceExternalId,
      document_version_id: getCitationString(citation, 'document_version_id') ?? '',
      document_version_number:
        getJsonNumber(citation, 'document_version_number') ?? 0,
      section_metadata: null,
      snippet:
        getCitationString(citation, 'snippet') ?? 'No citation text stored.',
      source_external_id: sourceExternalId,
      source_extra_metadata: null,
      source_id: sourceId,
      source_tags: [],
      source_type: getCitationString(citation, 'source_type') ?? 'source',
    },
    distance: chunk.dense_score ?? chunk.rrf_score ?? chunk.rerank_score ?? 0,
    embedding_metadata: null,
    score: chunk.rerank_score ?? chunk.rrf_score ?? chunk.dense_score ?? 0,
  }
}

function chatToolCallFromHistory(
  call: ChatHistoryToolCall,
  retrievalRuns: ChatHistoryRetrievalRun[],
): ChatToolCall {
  const matchingRun =
    retrievalRuns.find((run) => run.tool_call_id === call.tool_call_id) ?? null
  const query = getCitationString(call.arguments, 'query') ?? matchingRun?.query
  const limit =
    getJsonNumber(call.arguments, 'limit') ??
    getJsonNumber(call.arguments, 'top_k') ??
    matchingRun?.top_k
  const resultCount =
    getJsonNumber(call.result_summary, 'result_count') ??
    matchingRun?.retrieved_chunks.length
  const toolCall: ChatToolCall = {
    name: call.tool_name,
    arguments: call.arguments ?? undefined,
    result_summary: call.result_summary ?? undefined,
  }
  if (query !== undefined) {
    toolCall.query = query
  }
  if (limit !== undefined) {
    toolCall.limit = limit
  }
  if (resultCount !== undefined) {
    toolCall.result_count = resultCount
  }
  return toolCall
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

function validateChatRetrievalSettings({
  candidateLimit,
  rerankEnabled,
  retrievalLimit,
}: {
  candidateLimit: number
  rerankEnabled: boolean
  retrievalLimit: number
}): string | null {
  if (
    retrievalLimit < 1 ||
    retrievalLimit > CHAT_RETRIEVAL_MAX_LIMIT ||
    candidateLimit < 1 ||
    candidateLimit > CHAT_RETRIEVAL_MAX_LIMIT
  ) {
    return `Chat retrieval limits must be between 1 and ${CHAT_RETRIEVAL_MAX_LIMIT}.`
  }
  if (rerankEnabled && candidateLimit < retrievalLimit) {
    return 'Candidate limit must be greater than or equal to retrieval limit.'
  }
  return null
}

function getSpeechRecognitionConstructor(): BrowserSpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') {
    return null
  }
  const host = window as unknown as {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
  }
  return host.SpeechRecognition ?? host.webkitSpeechRecognition ?? null
}

function extractSpeechTranscript(event: SpeechRecognitionResultEventLike): string {
  return Array.from(event.results)
    .map((result) => result[0]?.transcript?.trim() ?? '')
    .filter((transcript) => transcript.length > 0)
    .join(' ')
}

function appendTranscript(current: string, transcript: string): string {
  const trimmedCurrent = current.trim()
  return trimmedCurrent.length === 0 ? transcript : `${trimmedCurrent} ${transcript}`
}

function getCitationString(value: unknown, key: string): string | null {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return null
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return typeof nextValue === 'string' && nextValue.length > 0
    ? nextValue
    : null
}

function getJsonNumber(value: unknown, key: string): number | null {
  if (value === null || typeof value !== 'object' || !(key in value)) {
    return null
  }

  const nextValue = (value as Record<string, unknown>)[key]
  return typeof nextValue === 'number' && Number.isFinite(nextValue)
    ? nextValue
    : null
}

function buildSourceCreateBody({
  content,
  contentBase64,
  externalId,
  sourceType,
  tags,
}: {
  content: string
  contentBase64: string
  externalId: string
  sourceType: string
  tags: string
}): SourceCreateBody {
  const parsedTags = parseTags(tags)
  const trimmedContent = content.trim()
  const body: SourceCreateBody = {
    external_id: externalId,
    source_type: sourceType,
  }
  if (parsedTags.length > 0) {
    body.tags = parsedTags
  }
  if (isBinarySourceType(sourceType)) {
    body.extra_metadata = { content_base64: contentBase64 }
    return body
  }
  if (trimmedContent.length > 0 || isTextSourceType(sourceType)) {
    body.extra_metadata = { content }
  }
  return body
}

function isTextSourceType(sourceType: string): boolean {
  return sourceType === 'markdown' || sourceType === 'text' || sourceType === 'txt'
}

function isBinarySourceType(sourceType: string): boolean {
  return sourceType === 'pdf' || sourceType === 'docx'
}

// Matches the backend MAX_BINARY_SOURCE_BYTES (5 MiB decoded) so oversize
// files are rejected before base64-encoding them in the browser.
const MAX_SOURCE_FILE_BYTES = 5 * 1024 * 1024

function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0)
}

function upsertProject(projects: Project[], project: Project): Project[] {
  const nextProjects = projects.filter((item) => item.id !== project.id)
  return [...nextProjects, project]
}

function upsertUser(users: User[], user: User): User[] {
  const nextUsers = users.filter((item) => item.id !== user.id)
  return [...nextUsers, user]
}

function upsertMembership(
  memberships: ProjectMembership[],
  membership: ProjectMembership,
): ProjectMembership[] {
  const nextMemberships = memberships.filter(
    (item) => item.id !== membership.id && item.user_id !== membership.user_id,
  )
  return [...nextMemberships, membership]
}

function upsertKnowledgeProposal(
  proposals: KnowledgeProposal[],
  proposal: KnowledgeProposal,
): KnowledgeProposal[] {
  const nextProposals = proposals.filter((item) => item.id !== proposal.id)
  return [proposal, ...nextProposals]
}

function proposalDraftText(
  drafts: Record<string, string>,
  proposal: KnowledgeProposal,
): string {
  return drafts[proposal.id] ?? proposal.refined_text ?? ''
}

function buildOptimisticSessionSummary(
  sessionId: string,
  status: ChatSessionStatus,
  title?: string,
): ChatSessionSummary {
  const timestamp = new Date().toISOString()
  return {
    archived_at: null,
    created_at: timestamp,
    error_message: null,
    has_approved_training: false,
    has_pending_training: false,
    message_count: 0,
    model_config: null,
    prompt_version: null,
    provider_usage_count: 0,
    retrieval_run_count: 0,
    session_id: sessionId,
    status,
    title: title?.slice(0, 60) ?? null,
    title_is_custom: false,
    tool_call_count: 0,
    total_estimated_cost_usd: 0,
    updated_at: timestamp,
  }
}

function upsertSessionSummary(
  sessions: ChatSessionSummary[],
  session: ChatSessionSummary,
): ChatSessionSummary[] {
  const nextSessions = sessions.filter(
    (item) => item.session_id !== session.session_id,
  )
  return [session, ...nextSessions]
}

function ensureSessionSummary(
  sessions: ChatSessionSummary[],
  session: ChatSessionSummary,
): ChatSessionSummary[] {
  return sessions.some((item) => item.session_id === session.session_id)
    ? sessions
    : [session, ...sessions]
}

function upsertSource(sources: Source[], source: Source): Source[] {
  const nextSources = sources.filter((item) => item.id !== source.id)
  return [...nextSources, source]
}

function upsertConnection(
  connections: ProviderConnection[],
  connection: ProviderConnection,
): ProviderConnection[] {
  const nextConnections = connections.filter(
    (item) => item.connection_id !== connection.connection_id,
  )
  return [...nextConnections, connection]
}

function upsertRuntimeSlot(
  slots: RuntimeSlotDefault[],
  slot: RuntimeSlotDefault,
): RuntimeSlotDefault[] {
  const nextSlots = slots.filter((item) => item.slot !== slot.slot)
  return [...nextSlots, slot]
}

function upsertChatModel(models: ChatModel[], model: ChatModel): ChatModel[] {
  const nextModels = models
    .filter(
      (item) =>
        item.connection_id !== model.connection_id ||
        item.model_id !== model.model_id,
    )
    .map((item) =>
      model.is_default
        ? {
            ...item,
            is_default: false,
          }
        : item,
    )
  return [...nextModels, model]
}

function upsertProviderModels(
  models: ProviderModel[],
  nextModels: ProviderModel[],
): ProviderModel[] {
  const nextKeys = new Set(
    nextModels.map((model) => `${model.connection_id}\u0000${model.model_id}`),
  )
  return [
    ...models.filter(
      (model) => !nextKeys.has(`${model.connection_id}\u0000${model.model_id}`),
    ),
    ...nextModels,
  ]
}

function upsertIngestionJob(
  jobs: IngestionJob[],
  job: IngestionJob,
): IngestionJob[] {
  const nextJobs = jobs.filter((item) => item.id !== job.id)
  return [job, ...nextJobs]
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function scrollChatTranscriptToBottom(transcript: HTMLElement): void {
  const top = transcript.scrollHeight
  // Auto-follow: smooth when motion is OK; instant when user prefers reduced motion.
  // Prefer scrollTo when available; fall back to scrollTop (jsdom / older engines).
  if (typeof transcript.scrollTo === 'function') {
    const behavior: ScrollBehavior = prefersReducedMotion() ? 'auto' : 'smooth'
    transcript.scrollTo({ behavior, top })
    return
  }
  transcript.scrollTop = top
}

function focusMessage(messageId: string): void {
  document.getElementById(messageElementId(messageId))?.focus()
}

function messageElementId(messageId: string): string {
  return `chat-message-${messageId}`
}

function optionalFilterValue(value: string): string | null {
  const trimmedValue = value.trim()
  return trimmedValue.length > 0 ? trimmedValue : null
}

export default App
