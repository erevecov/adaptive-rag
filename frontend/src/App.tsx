import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import './App.css'
import { IconButton } from '@/components/ui/button'
import { SidebarItem as UiSidebarItem } from '@/components/ui/nav'
import { AuthoringPanel } from '@/features/authoring/AuthoringView'
import { ChatWorkspacePanel } from '@/features/chat/ChatWorkspaceView'
import {
  SessionNavigationPanel,
  WorkspaceInspectorPanel,
} from '@/features/history/HistoryInspectorView'
import { ObservabilityPanel } from '@/features/observability/ObservabilityView'
import { RuntimeSettingsPanel } from '@/features/runtime/RuntimeSettingsView'
import {
  CHAT_RETRIEVAL_MAX_LIMIT,
  PROVIDER_CONNECTION_CAPABILITIES,
  type RuntimeSubmodule,
} from '@/features/runtime/runtimeUi'
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

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_RETRIEVAL_LIMIT = 5
const DEFAULT_RERANK_CANDIDATE_LIMIT = 10
const SESSION_PAGE_SIZE = 15
const PROJECT_STORAGE_KEY = 'adaptive-rag:last-project-id'
const RIGHT_DOCK_INLINE_WIDTH_PX = 1280
const PROJECT_NAME_COLLATOR = new Intl.Collator(undefined, {
  sensitivity: 'base',
})
const SETTINGS_NAVIGATION = [
  {
    id: 'authoring',
    label: 'Authoring',
    submodules: [
      { id: 'projects', label: 'Projects' },
      { id: 'users', label: 'Users' },
      { id: 'knowledge', label: 'Knowledge' },
      { id: 'sources', label: 'Sources' },
    ],
  },
  {
    id: 'observability',
    label: 'Observability',
    submodules: [
      { id: 'summary', label: 'Summary' },
      { id: 'costs', label: 'Costs' },
      { id: 'errors', label: 'Errors' },
      { id: 'latency', label: 'Latency' },
    ],
  },
  {
    id: 'runtime',
    label: 'Runtime',
    submodules: [
      { id: 'connections', label: 'Connections' },
      { id: 'model_catalog', label: 'Model catalog' },
      { id: 'global_defaults', label: 'Global defaults' },
      { id: 'project_overrides', label: 'Project overrides' },
    ],
  },
] as const

const AUTHORING_NAVIGATION = SETTINGS_NAVIGATION[0]
const OBSERVABILITY_NAVIGATION = SETTINGS_NAVIGATION[1]
const RUNTIME_NAVIGATION = SETTINGS_NAVIGATION[2]

const ACCOUNT_MODULES = [
  { id: 'appearance', label: 'Appearance' },
  { id: 'memory', label: 'Memory' },
] as const

type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
type PrimaryView = 'chat' | 'account' | 'settings'
type AccountModule = (typeof ACCOUNT_MODULES)[number]['id']
type SettingsModule = (typeof SETTINGS_NAVIGATION)[number]['id']
type AuthoringSubmodule = (typeof SETTINGS_NAVIGATION)[0]['submodules'][number]['id']
type ObservabilitySubmodule =
  (typeof SETTINGS_NAVIGATION)[1]['submodules'][number]['id']
type SettingsSubmodule =
  | AuthoringSubmodule
  | ObservabilitySubmodule
  | RuntimeSubmodule
type SettingsNavigationSelection =
  | { module: 'authoring'; submodule: AuthoringSubmodule }
  | { module: 'observability'; submodule: ObservabilitySubmodule }
  | { module: 'runtime'; submodule: RuntimeSubmodule }
type ActiveView = PrimaryView | SettingsModule
const ACTIVE_VIEW_ROUTES: Record<ActiveView, string> = {
  account: '/account',
  authoring: '/settings/authoring',
  chat: '/chat',
  observability: '/settings/observability',
  runtime: '/settings/runtime',
  settings: '/settings/authoring',
}
type SessionNavigationFilter = 'active' | 'training' | 'archived'
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

    transcript.scrollTop = transcript.scrollHeight
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
    setActiveResponseQuestion(trimmedQuestion)
    setSessionDetail(null)
    setDetailState('idle')
    setDetailError(null)
    setSelectedSessionId(null)
    setHistoryStatusFilter('active')
    setVisibleSessionCount(SESSION_PAGE_SIZE)
    resetSourceViewer()
    chatAutoFollowRef.current = true

    const requestBody = {
      message: trimmedQuestion,
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
      }
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
          const nextSessionId = nextResponse.session_id
          if (nextSessionId !== null) {
            setSelectedSessionId(nextSessionId)
          }
          setRequestState('succeeded')
          setQuestion('')
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

  async function handleSubmitKnowledgeDraft(
    draft: ChatKnowledgeDraft,
    sessionId: string | null,
  ): Promise<KnowledgeProposal> {
    const trimmedProjectId = projectId.trim()
    const text = draft.text.trim()

    if (trimmedProjectId.length === 0 || text.length === 0) {
      throw new Error('Project ID and knowledge text are required.')
    }

    const proposal = await client.submitKnowledgeProposal(trimmedProjectId, {
      ...(sessionId === null ? {} : { origin_session_id: sessionId }),
      proposed_text: text,
    })
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
    setRequestState('idle')
    setRequestError(null)
    resetSourceViewer()
    setDetailState('loading')
    setDetailError(null)

    try {
      const detail = await client.getChatSession(trimmedProjectId, sessionId)
      setSessionDetail(detail)
      setActiveResponseQuestion(extractLatestUserQuestion(detail))
      setResponse(chatResponseFromSessionDetail(detail))
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

    const body = buildSourceCreateBody({
      content,
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
      setSourceTags('')
      setSourceAuthoringState('succeeded')
    } catch (error) {
      setSourceAuthoringState('failed')
      setSourceAuthoringError(getErrorMessage(error))
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
    <main
      className={[
        'app-shell',
        isLeftSidebarOpen
          ? 'app-shell-sidebar-open'
          : 'app-shell-sidebar-closed',
        isRightDockOpen ? 'app-shell-right-dock-open' : 'app-shell-right-dock-closed',
      ].join(' ')}
    >
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

      <section
        className={primaryView === 'chat' ? 'workspace workspace-chat' : 'workspace'}
        aria-labelledby="workspace-title"
      >
        <WorkspaceTopline
          projectId={projectId}
          projects={projects}
          selectedSessionId={selectedSessionId}
          sessionDetail={sessionDetail}
          sessions={sessions}
        />

        {primaryView === 'chat' ? (
          <div
            className={
              isRightDockInline
                ? 'workspace-grid chat-workspace-grid chat-workspace-grid-docked'
                : 'workspace-grid chat-workspace-grid'
            }
          >
            <ChatWorkspacePanel
              activeResponseQuestion={activeResponseQuestion}
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
              onStartSpeechRecognition={handleStartSpeechRecognition}
              onStopSpeechRecognition={handleStopSpeechRecognition}
              onSubmit={handleSubmit}
              onSubmitKnowledgeDraft={handleSubmitKnowledgeDraft}
              onTranscriptScroll={handleChatTranscriptScroll}
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

            {isRightDockOverlay ? (
              <div
                aria-hidden="true"
                className="workspace-inspector-backdrop"
                data-testid="workspace-inspector-backdrop"
                onClick={() => setIsRightDockOpen(false)}
              />
            ) : null}

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
          </div>
        ) : primaryView === 'account' ? (
          accountModule === 'appearance' ? (
            <AppearanceSettingsPanel onThemeChange={setTheme} theme={theme} />
          ) : (
            <DeferredAccountModulePanel moduleName="Memory" />
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
                onRunNextIngestion={() => void handleRunNextIngestion()}
                onSaveProjectMembership={(event) =>
                  void handleSaveProjectMembership(event)
                }
                onSelectProject={handleSelectProject}
                onSourceContentChange={setSourceContent}
                onSourceExternalIdChange={setSourceExternalId}
                onSourceTagsChange={setSourceTags}
                onSourceTypeChange={setSourceType}
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
      </section>
    </main>
  )
}

function WorkspaceTopline({
  projectId,
  projects,
  selectedSessionId,
  sessionDetail,
  sessions,
}: {
  projectId: string
  projects: Project[]
  selectedSessionId: string | null
  sessionDetail: ChatSessionDetailResponse | null
  sessions: ChatSessionSummary[]
}) {
  const projectName = getWorkspaceProjectName(projectId, projects)
  const sessionName = getWorkspaceSessionName({
    selectedSessionId,
    sessionDetail,
    sessions,
  })

  return (
    <header
      aria-label={`Current session ${sessionName}, project ${projectName}`}
      className="workspace-topline"
    >
      <h1 id="workspace-title" title={sessionName}>
        {sessionName}
      </h1>
      <span className="workspace-project-chip" title={projectName}>
        {projectName}
      </span>
    </header>
  )
}

function AppSidebar({
  accountModule,
  authoringSubmodule,
  canLoadMoreSessions,
  error,
  isOpen,
  observabilitySubmodule,
  onArchiveSession,
  onAccountModuleChange,
  onLoadMoreSessions,
  onPrimaryViewChange,
  onProjectIdChange,
  onRenameSession,
  onSelectSession,
  onSettingsModuleChange,
  onSettingsSubmoduleChange,
  onStartNewSession,
  onStatusFilterChange,
  onToggle,
  onUnarchiveSession,
  primaryView,
  projectId,
  projectState,
  projects,
  runtimeSubmodule,
  selectedSessionId,
  sessions,
  sessionState,
  settingsModule,
  statusFilter,
}: {
  accountModule: AccountModule
  authoringSubmodule: AuthoringSubmodule
  canLoadMoreSessions: boolean
  error: string | null
  isOpen: boolean
  observabilitySubmodule: ObservabilitySubmodule
  onArchiveSession(sessionId: string): void
  onAccountModuleChange(module: AccountModule): void
  onLoadMoreSessions(): void
  onPrimaryViewChange(view: PrimaryView): void
  onProjectIdChange(projectId: string): void
  onRenameSession(sessionId: string, title: string): void
  onSelectSession(sessionId: string): void
  onSettingsModuleChange(module: SettingsModule): void
  onSettingsSubmoduleChange(selection: SettingsNavigationSelection): void
  onStartNewSession(): void
  onStatusFilterChange(filter: SessionNavigationFilter): void
  onToggle(): void
  onUnarchiveSession(sessionId: string): void
  primaryView: PrimaryView
  projectId: string
  projectState: RequestState
  projects: Project[]
  runtimeSubmodule: RuntimeSubmodule
  selectedSessionId: string | null
  sessions: ChatSessionSummary[]
  sessionState: RequestState
  settingsModule: SettingsModule
  statusFilter: SessionNavigationFilter
}) {
  return (
    <aside
      aria-label="Primary sidebar"
      className={isOpen ? 'app-sidebar app-sidebar-open' : 'app-sidebar app-sidebar-closed'}
    >
      <div className="app-sidebar-chrome">
        <IconButton
          aria-expanded={isOpen}
          className="sidebar-burger"
          label={isOpen ? 'Collapse left sidebar' : 'Open left sidebar'}
          onClick={onToggle}
        >
          <MenuIcon />
        </IconButton>
        <div className="sidebar-brand" aria-hidden={!isOpen}>
          <strong>Adaptive RAG</strong>
          <span>Workspace</span>
        </div>
      </div>

      <div className="app-sidebar-content">
        <SidebarProjectSelector
          onProjectIdChange={onProjectIdChange}
          projectId={projectId}
          projects={projects}
          state={projectState}
        />

        <nav className="sidebar-navigation" aria-label="Primary navigation">
          <SidebarNavButton
            active={primaryView === 'chat'}
            label="Chat"
            onClick={() => onPrimaryViewChange('chat')}
          />
          <SidebarNavButton
            active={primaryView === 'account'}
            label="My account"
            onClick={() => onPrimaryViewChange('account')}
          />
          <SidebarNavButton
            active={primaryView === 'settings'}
            label="Settings"
            onClick={() => onPrimaryViewChange('settings')}
          />
        </nav>

        {primaryView === 'chat' ? (
          <SessionNavigationPanel
            canLoadMore={canLoadMoreSessions}
            error={error}
            onArchiveSession={onArchiveSession}
            onLoadMore={onLoadMoreSessions}
            onRenameSession={onRenameSession}
            onSelectSession={onSelectSession}
            onStartNewSession={onStartNewSession}
            onStatusFilterChange={onStatusFilterChange}
            onUnarchiveSession={onUnarchiveSession}
            selectedSessionId={selectedSessionId}
            sessions={sessions}
            statusFilter={statusFilter}
            state={sessionState}
          />
        ) : primaryView === 'account' ? (
          <AccountNavigationPanel
            activeModule={accountModule}
            onModuleChange={onAccountModuleChange}
          />
        ) : (
          <SettingsNavigationPanel
            activeAuthoringSubmodule={authoringSubmodule}
            activeModule={settingsModule}
            activeObservabilitySubmodule={observabilitySubmodule}
            activeRuntimeSubmodule={runtimeSubmodule}
            onModuleChange={onSettingsModuleChange}
            onSubmoduleChange={onSettingsSubmoduleChange}
          />
        )}
      </div>
    </aside>
  )
}

function SidebarNavButton({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick(): void
}) {
  return (
    <UiSidebarItem
      active={active}
      className={active ? 'sidebar-nav-button sidebar-nav-button-active' : 'sidebar-nav-button'}
      onClick={onClick}
    >
      {label}
    </UiSidebarItem>
  )
}

function AccountNavigationPanel({
  activeModule,
  onModuleChange,
}: {
  activeModule: AccountModule
  onModuleChange(module: AccountModule): void
}) {
  return (
    <nav className="contextual-navigation" aria-label="My account navigation">
      <h2 className="sidebar-section-title">My account</h2>
      <div className="contextual-nav-group">
        {ACCOUNT_MODULES.map((module) => {
          const active = module.id === activeModule
          return (
            <button
              aria-pressed={active}
              className={
                active
                  ? 'contextual-nav-button contextual-nav-button-active'
                  : 'contextual-nav-button'
              }
              key={module.id}
              onClick={() => onModuleChange(module.id)}
              type="button"
            >
              {module.label}
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function SettingsNavigationPanel({
  activeAuthoringSubmodule,
  activeModule,
  activeObservabilitySubmodule,
  activeRuntimeSubmodule,
  onModuleChange,
  onSubmoduleChange,
}: {
  activeAuthoringSubmodule: AuthoringSubmodule
  activeModule: SettingsModule
  activeObservabilitySubmodule: ObservabilitySubmodule
  activeRuntimeSubmodule: RuntimeSubmodule
  onModuleChange(module: SettingsModule): void
  onSubmoduleChange(selection: SettingsNavigationSelection): void
}) {
  const activeSubmodule = getActiveSettingsSubmodule(
    activeModule,
    activeAuthoringSubmodule,
    activeObservabilitySubmodule,
    activeRuntimeSubmodule,
  )
  const renderSubmoduleButton = (
    selection: SettingsNavigationSelection,
    label: string,
  ) => {
    const submoduleActive = selection.submodule === activeSubmodule
    return (
      <button
        aria-pressed={submoduleActive}
        className={
          submoduleActive
            ? 'contextual-nav-subbutton contextual-nav-subbutton-active'
            : 'contextual-nav-subbutton'
        }
        key={selection.submodule}
        onClick={() => onSubmoduleChange(selection)}
        type="button"
      >
        {label}
      </button>
    )
  }

  return (
    <nav className="contextual-navigation" aria-label="Settings navigation">
      <h2 className="sidebar-section-title">Settings</h2>
      <div className="contextual-nav-group">
        <button
          aria-pressed={activeModule === AUTHORING_NAVIGATION.id}
          className={
            activeModule === AUTHORING_NAVIGATION.id
              ? 'contextual-nav-button contextual-nav-button-active'
              : 'contextual-nav-button'
          }
          onClick={() => onModuleChange(AUTHORING_NAVIGATION.id)}
          type="button"
        >
          {AUTHORING_NAVIGATION.label}
        </button>

        {activeModule === AUTHORING_NAVIGATION.id
          ? AUTHORING_NAVIGATION.submodules.map((submodule) =>
              renderSubmoduleButton(
                { module: AUTHORING_NAVIGATION.id, submodule: submodule.id },
                submodule.label,
              ),
            )
          : null}
      </div>
      <div className="contextual-nav-group">
        <button
          aria-pressed={activeModule === OBSERVABILITY_NAVIGATION.id}
          className={
            activeModule === OBSERVABILITY_NAVIGATION.id
              ? 'contextual-nav-button contextual-nav-button-active'
              : 'contextual-nav-button'
          }
          onClick={() => onModuleChange(OBSERVABILITY_NAVIGATION.id)}
          type="button"
        >
          {OBSERVABILITY_NAVIGATION.label}
        </button>

        {activeModule === OBSERVABILITY_NAVIGATION.id
          ? OBSERVABILITY_NAVIGATION.submodules.map((submodule) =>
              renderSubmoduleButton(
                {
                  module: OBSERVABILITY_NAVIGATION.id,
                  submodule: submodule.id,
                },
                submodule.label,
              ),
            )
          : null}
      </div>
      <div className="contextual-nav-group">
        <button
          aria-pressed={activeModule === RUNTIME_NAVIGATION.id}
          className={
            activeModule === RUNTIME_NAVIGATION.id
              ? 'contextual-nav-button contextual-nav-button-active'
              : 'contextual-nav-button'
          }
          onClick={() => onModuleChange(RUNTIME_NAVIGATION.id)}
          type="button"
        >
          {RUNTIME_NAVIGATION.label}
        </button>

        {activeModule === RUNTIME_NAVIGATION.id
          ? RUNTIME_NAVIGATION.submodules.map((submodule) =>
              renderSubmoduleButton(
                { module: RUNTIME_NAVIGATION.id, submodule: submodule.id },
                submodule.label,
              ),
            )
          : null}
      </div>
    </nav>
  )
}

function getActiveSettingsSubmodule(
  activeModule: SettingsModule,
  activeAuthoringSubmodule: AuthoringSubmodule,
  activeObservabilitySubmodule: ObservabilitySubmodule,
  activeRuntimeSubmodule: RuntimeSubmodule,
): SettingsSubmodule {
  if (activeModule === 'authoring') {
    return activeAuthoringSubmodule
  }
  if (activeModule === 'observability') {
    return activeObservabilitySubmodule
  }
  return activeRuntimeSubmodule
}

function SidebarProjectSelector({
  onProjectIdChange,
  projectId,
  projects,
  state,
}: {
  onProjectIdChange(projectId: string): void
  projectId: string
  projects: Project[]
  state: RequestState
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [projectSearch, setProjectSearch] = useState('')
  const rootRef = useRef<HTMLDivElement | null>(null)
  const trimmedProjectId = projectId.trim()
  const selectedProject = projects.find((project) => project.id === trimmedProjectId)
  const selectedLabel =
    selectedProject?.name ??
    (trimmedProjectId.length > 0 ? 'Project selected' : 'Select project')
  const visibleProjects = useMemo(
    () => getVisibleProjectOptions(projects, projectSearch),
    [projectSearch, projects],
  )

  useEffect(() => {
    if (!isOpen) return

    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current?.contains(event.target as Node) === true) {
        return
      }
      setIsOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [isOpen])

  function handleSelectProject(nextProjectId: string) {
    onProjectIdChange(nextProjectId)
    setIsOpen(false)
    setProjectSearch('')
  }

  return (
    <div className="sidebar-project-selector" ref={rootRef}>
      <button
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={`Project selector: ${selectedLabel}`}
        className="project-selector-trigger"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <span>
          <small>Project</small>
          <strong>{selectedLabel}</strong>
        </span>
        <ChevronDownIcon />
      </button>

      {isOpen ? (
        <div className="project-selector-popover">
          <label className="project-selector-search">
            <span>Search projects</span>
            <input
              aria-label="Search projects"
              autoComplete="off"
              autoFocus
              name="project-search"
              onChange={(event) => setProjectSearch(event.currentTarget.value)}
              placeholder="Search projects"
              type="search"
              value={projectSearch}
            />
          </label>

          <div className="project-selector-popover-header">
            <span>{state === 'loading' ? 'Loading projects...' : 'All projects'}</span>
          </div>

          <div className="project-selector-list" role="listbox" aria-label="Projects">
            {visibleProjects.length > 0 ? (
              visibleProjects.map((project) => {
                const canAccess = project.can_access !== false
                const isSelected = project.id === trimmedProjectId

                return (
                  <button
                    aria-label={
                      canAccess
                        ? `Select project ${project.name}`
                        : `Project ${project.name}. No tienes acceso para ese proyecto`
                    }
                    aria-selected={isSelected}
                    className={[
                      'project-selector-option',
                      isSelected ? 'project-selector-option-active' : '',
                      canAccess ? '' : 'project-selector-option-disabled',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    disabled={!canAccess}
                    key={project.id}
                    onClick={() => handleSelectProject(project.id)}
                    role="option"
                    title={canAccess ? undefined : 'No tienes acceso para ese proyecto'}
                    type="button"
                  >
                    <span>
                      <strong>{project.name}</strong>
                    </span>
                    {!canAccess ? (
                      <span
                        aria-label="No tienes acceso para ese proyecto"
                        className="project-selector-lock"
                        title="No tienes acceso para ese proyecto"
                      >
                        <LockIcon />
                      </span>
                    ) : null}
                  </button>
                )
              })
            ) : (
              <p className="project-selector-empty">No projects match.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function SettingsPanel({ children }: { children: ReactNode }) {
  return (
    <section className="settings-shell" aria-labelledby="settings-title">
      <header className="settings-shell-header">
        <div>
          <h2 id="settings-title">Settings</h2>
        </div>
      </header>
      <div className="settings-section-body">{children}</div>
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
    <section
      className="panel settings-panel"
      aria-labelledby="appearance-settings-title"
    >
      <header className="settings-header">
        <div>
          <p className="panel-label">My account</p>
          <h2 id="appearance-settings-title">Appearance</h2>
        </div>
        <span className="status">{theme}</span>
      </header>

      <p className="settings-description">Choose the interface palette.</p>

      <div className="theme-option-grid">
        {THEMES.map((option) => {
          const active = option.id === theme
          return (
            <button
              aria-pressed={active}
              className={
                active ? 'theme-option theme-option-active' : 'theme-option'
              }
              data-slot="theme-option"
              key={option.id}
              onClick={() => onThemeChange(option.id)}
              type="button"
            >
              <span
                aria-hidden="true"
                className="theme-swatch"
                style={{ background: option.swatch.bg }}
              >
                <span
                  className="theme-swatch-line theme-swatch-line-strong"
                  style={{ background: option.swatch.fg }}
                />
                <span
                  className="theme-swatch-line theme-swatch-line-muted"
                  style={{ background: option.swatch.muted }}
                />
                <span
                  className="theme-swatch-accent"
                  style={{ background: option.swatch.accent }}
                />
              </span>
              <span className="theme-option-copy">
                <span className="theme-option-title">
                  {option.label}
                  {active ? (
                    <span className="theme-option-check" aria-hidden="true" />
                  ) : null}
                </span>
                <span className="theme-option-description">
                  {option.description}
                </span>
              </span>
            </button>
          )
        })}
      </div>
    </section>
  )
}

function DeferredAccountModulePanel({ moduleName }: { moduleName: string }) {
  return (
    <section className="panel settings-panel" aria-labelledby="deferred-account-title">
      <header className="settings-header">
        <div>
          <p className="panel-label">My account</p>
          <h2 id="deferred-account-title">{moduleName}</h2>
        </div>
        <span className="status">Deferred</span>
      </header>
      <p className="settings-description">
        This module is not available until a durable backend contract exists.
      </p>
    </section>
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

function sessionDisplayTitle(session: ChatSessionSummary): string {
  const title = session.title?.trim()
  if (title !== undefined && title.length > 0) {
    return title
  }
  return shortSessionId(session.session_id)
}

function getWorkspaceProjectName(projectId: string, projects: Project[]): string {
  const trimmedProjectId = projectId.trim()
  const project = projects.find((item) => item.id === trimmedProjectId)
  const name = project?.name.trim()
  if (name !== undefined && name.length > 0) {
    return name
  }
  return trimmedProjectId.length > 0 ? 'Proyecto seleccionado' : 'Sin proyecto'
}

function getWorkspaceSessionName({
  selectedSessionId,
  sessionDetail,
  sessions,
}: {
  selectedSessionId: string | null
  sessionDetail: ChatSessionDetailResponse | null
  sessions: ChatSessionSummary[]
}): string {
  if (selectedSessionId === null) {
    return 'Nuevo chat'
  }

  if (sessionDetail?.session.session_id === selectedSessionId) {
    const detailTitle = sessionDetail.session.title?.trim()
    if (detailTitle !== undefined && detailTitle.length > 0) {
      return detailTitle
    }
  }

  const session = sessions.find((item) => item.session_id === selectedSessionId)
  if (session !== undefined) {
    return sessionDisplayTitle(session)
  }

  return shortSessionId(selectedSessionId)
}

function shortSessionId(sessionId: string): string {
  if (sessionId.length <= 12) {
    return sessionId
  }
  return sessionId.slice(0, 8)
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

function getVisibleProjectOptions(projects: Project[], search: string): Project[] {
  const normalizedSearch = search.trim().toLowerCase()
  const filteredProjects =
    normalizedSearch.length === 0
      ? projects
      : projects.filter((project) =>
          project.name.toLowerCase().includes(normalizedSearch),
        )

  return [...filteredProjects].sort((left, right) => {
    const leftCanAccess = left.can_access !== false
    const rightCanAccess = right.can_access !== false
    if (leftCanAccess !== rightCanAccess) {
      return leftCanAccess ? -1 : 1
    }

    const nameComparison = PROJECT_NAME_COLLATOR.compare(left.name, right.name)
    return nameComparison === 0 ? left.id.localeCompare(right.id) : nameComparison
  })
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
  const assistantMessage =
    [...detail.messages].reverse().find((message) => message.role === 'assistant') ??
    detail.messages[detail.messages.length - 1]

  return {
    answer: assistantMessage?.content ?? '',
    citations: detail.retrieval_runs.flatMap((run) =>
      run.retrieved_chunks.map((chunk) => retrievalResultFromHistory(chunk)),
    ),
    session_id: detail.session.session_id,
    steps: parseChatStepsFromMetadata(assistantMessage?.metadata ?? null),
    tool_calls: detail.tool_calls.map((call) =>
      chatToolCallFromHistory(call, detail.retrieval_runs),
    ),
  }
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
  const sourceId =
    getCitationString(citation, 'source_id') ??
    getCitationString(citation, 'source_external_id') ??
    chunk.chunk_id
  const sourceExternalId =
    getCitationString(citation, 'source_external_id') ?? sourceId

  return {
    chunk_id: chunk.chunk_id,
    citation: {
      char_end: getJsonNumber(citation, 'char_end') ?? 0,
      char_start: getJsonNumber(citation, 'char_start') ?? 0,
      chunk_id: getCitationString(citation, 'chunk_id') ?? chunk.chunk_id,
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
  externalId,
  sourceType,
  tags,
}: {
  content: string
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
  if (trimmedContent.length > 0 || isTextSourceType(sourceType)) {
    body.extra_metadata = { content }
  }
  return body
}

function isTextSourceType(sourceType: string): boolean {
  return sourceType === 'markdown' || sourceType === 'text' || sourceType === 'txt'
}

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

function MenuIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

function LockIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <rect height="10" rx="2" width="14" x="5" y="10" />
      <path d="M8 10V8a4 4 0 0 1 8 0v2" />
    </svg>
  )
}

export default App
