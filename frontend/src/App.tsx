import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import './App.css'
import {
  ApiClientError,
  createApiClient,
  type ApiClient,
  type ChatRetrievalSettings,
  type ChatObservabilityProviderUsageGroup,
  type ChatObservabilitySummary,
  type ChatHistoryProviderUsage,
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
  type ProviderModel,
  type ProviderSecretStatus,
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

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_RETRIEVAL_LIMIT = 5
const DEFAULT_RERANK_CANDIDATE_LIMIT = 10
const CHAT_RETRIEVAL_MAX_LIMIT = 50
const SESSION_PAGE_SIZE = 15
const PROJECT_STORAGE_KEY = 'adaptive-rag:last-project-id'
const RIGHT_DOCK_INLINE_WIDTH_PX = 1280
const NUMBER_FORMATTER = new Intl.NumberFormat('en-US')
const PROJECT_NAME_COLLATOR = new Intl.Collator(undefined, {
  sensitivity: 'base',
})
const STATUS_ORDER = ['failed', 'running', 'succeeded']
const SESSION_FILTERS = [
  { label: 'ACTIVOS', value: 'active' },
  { label: 'TRAIN', value: 'training' },
  { label: 'ARCHIVADOS', value: 'archived' },
] as const
const RUNTIME_SLOTS = [
  'chat',
  'dense_embedding',
  'sparse_embedding',
  'rerank',
  'contextualization',
]
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
type RuntimeSubmodule = (typeof SETTINGS_NAVIGATION)[2]['submodules'][number]['id']
type SettingsSubmodule =
  | AuthoringSubmodule
  | ObservabilitySubmodule
  | RuntimeSubmodule
type SettingsNavigationSelection =
  | { module: 'authoring'; submodule: AuthoringSubmodule }
  | { module: 'observability'; submodule: ObservabilitySubmodule }
  | { module: 'runtime'; submodule: RuntimeSubmodule }
type SessionNavigationFilter = (typeof SESSION_FILTERS)[number]['value']
type InspectorTab = 'context' | 'minimap'
type ProviderModelOption = {
  connection_id: string
  model_id: string
}
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
  const [retrievalLimitOverride, setRetrievalLimitOverride] = useState('')
  const [speechState, setSpeechState] = useState<RequestState>('idle')
  const [speechFeedback, setSpeechFeedback] = useState<string | null>(null)
  const [activeSpeechRecognition, setActiveSpeechRecognition] =
    useState<BrowserSpeechRecognition | null>(null)
  const [response, setResponse] = useState<ChatResponseBody | null>(null)
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
  const [primaryView, setPrimaryView] = useState<PrimaryView>('chat')
  const [accountModule, setAccountModule] =
    useState<AccountModule>('appearance')
  const [settingsModule, setSettingsModule] =
    useState<SettingsModule>('authoring')
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
  const [knowledgeSubmitState, setKnowledgeSubmitState] =
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
  const [knowledgeSubmitError, setKnowledgeSubmitError] = useState<string | null>(
    null,
  )
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
  const [connectionCapabilities, setConnectionCapabilities] = useState('')
  const [modelSyncConnectionId, setModelSyncConnectionId] = useState('')
  const [secretConnectionId, setSecretConnectionId] = useState('')
  const [secretValue, setSecretValue] = useState('')
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
  const isProposingKnowledge = knowledgeSubmitState === 'loading'
  const isRightDockInlineViewport = useIsRightDockInlineViewport()
  const isRightDockInline = isRightDockOpen && isRightDockInlineViewport
  const isRightDockOverlay = isRightDockOpen && !isRightDockInlineViewport
  const speechRecognitionConstructor = getSpeechRecognitionConstructor()
  const isSpeechSupported = speechRecognitionConstructor !== null

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

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
    setSessionDetail(null)
    setDetailState('idle')
    setDetailError(null)
    setSelectedSessionId(null)
    setHistoryStatusFilter('active')
    setVisibleSessionCount(SESSION_PAGE_SIZE)
    resetSourceViewer()
    chatAutoFollowRef.current = true

    const requestBody: {
      message: string
      retrieval_limit?: number
    } = {
      message: trimmedQuestion,
    }
    const parsedRetrievalLimitOverride = parseOptionalChatRetrievalLimit(
      retrievalLimitOverride,
    )
    if (parsedRetrievalLimitOverride !== null) {
      requestBody.retrieval_limit = parsedRetrievalLimitOverride
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
        },
        { signal: controller.signal },
      )
      setResponse(nextResponse)
      const nextSessionId = nextResponse.session_id
      if (nextSessionId !== null) {
        setSelectedSessionId(nextSessionId)
      }
      setRequestState('succeeded')
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
    setPrimaryView(view)
  }

  function handleSettingsModuleChange(module: SettingsModule) {
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
    setPrimaryView('chat')
    setQuestion('')
    setResponse(null)
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

    setPrimaryView('chat')
    setQuestion('')
    setSelectedSessionId(sessionId)
    setRequestState('idle')
    setRequestError(null)
    resetSourceViewer()
    setDetailState('loading')
    setDetailError(null)

    try {
      const detail = await client.getChatSession(trimmedProjectId, sessionId)
      setSessionDetail(detail)
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

  async function handleSubmitKnowledgeProposal() {
    const trimmedProjectId = projectId.trim()
    const proposedText = question.trim()

    if (trimmedProjectId.length === 0) {
      setKnowledgeSubmitState('failed')
      setKnowledgeSubmitError('Project ID is required to propose knowledge.')
      return
    }
    if (proposedText.length === 0) {
      setKnowledgeSubmitState('failed')
      setKnowledgeSubmitError('Question text is required to propose knowledge.')
      return
    }

    setKnowledgeSubmitState('loading')
    setKnowledgeSubmitError(null)

    try {
      const proposal = await client.submitKnowledgeProposal(trimmedProjectId, {
        proposed_text: proposedText,
      })
      setKnowledgeProposals((current) => upsertKnowledgeProposal(current, proposal))
      setKnowledgeSubmitState('succeeded')
    } catch (error) {
      setKnowledgeSubmitState('failed')
      setKnowledgeSubmitError(getErrorMessage(error))
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

  async function handleRefreshRuntimeConnections() {
    setRuntimeState('loading')
    setRuntimeError(null)

    try {
      const connections = await client.listProviderConnections()
      setRuntimeConnections(connections.items)
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    }
  }

  async function handleRefreshRuntimeModelCatalog() {
    setRuntimeState('loading')
    setRuntimeError(null)

    try {
      const [connections, providerModels] = await Promise.all([
        client.listProviderConnections(),
        client.listProviderModels(),
      ])
      setRuntimeConnections(connections.items)
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

  async function handleSaveConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const connection = await client.createProviderConnection({
        base_url: optionalFilterValue(connectionBaseUrl),
        capabilities: parseTags(connectionCapabilities),
        connection_type: connectionType,
        metadata: null,
        provider: connectionProvider,
      })
      setRuntimeConnections((current) => upsertConnection(current, connection))
      setSecretConnectionId(connection.connection_id)
      setModelSyncConnectionId(connection.connection_id)
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

  async function handleSaveSecret(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedConnectionId = secretConnectionId.trim()
    const trimmedSecret = secretValue.trim()
    if (trimmedConnectionId.length === 0 || trimmedSecret.length === 0) {
      setRuntimeState('failed')
      setRuntimeError('Secret connection ID and API key are required.')
      setSecretValue('')
      return
    }

    setRuntimeState('loading')
    setRuntimeError(null)
    try {
      const status = await client.upsertProviderSecret(
        trimmedConnectionId,
        'api_key',
        { value: trimmedSecret },
      )
      setRuntimeConnections((current) =>
        updateConnectionSecret(current, trimmedConnectionId, status),
      )
      setRuntimeState('succeeded')
    } catch (error) {
      setRuntimeState('failed')
      setRuntimeError(getErrorMessage(error))
    } finally {
      setSecretValue('')
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
            <section className="panel panel-primary chat-panel" aria-label="Chat workspace">
              <div
                aria-label="Chat transcript"
                className="chat-transcript"
                onScroll={handleChatTranscriptScroll}
                ref={chatTranscriptRef}
                role="region"
              >
                <ResponsePanel
                  onOpenSource={(sourceId, citationSnippet) =>
                    void handleOpenSource(sourceId, citationSnippet)
                  }
                  response={response}
                  state={requestState}
                />
              </div>

              <form className="chat-form" onSubmit={handleSubmit}>
                <label className="field">
                  <span>Question</span>
                  <textarea
                    name="question"
                    onChange={(event) => setQuestion(event.currentTarget.value)}
                    placeholder="Ask a question about indexed sources"
                    rows={3}
                    value={question}
                  />
                </label>

                <div className="composer-toolbar">
                  <label className="field field-compact">
                    <span>Retrieval limit</span>
                    <input
                      max={CHAT_RETRIEVAL_MAX_LIMIT}
                      min={1}
                      name="retrieval-limit"
                      onChange={(event) =>
                        setRetrievalLimitOverride(
                          normalizeOptionalChatRetrievalLimit(
                            event.currentTarget.value,
                          ),
                        )
                      }
                      placeholder="Default"
                      type="number"
                      value={retrievalLimitOverride}
                    />
                  </label>

                  <div className="composer-icon-actions">
                    <button
                      aria-label="Open context sidebar"
                      aria-pressed={isRightDockOpen && inspectorTab === 'context'}
                      className="composer-icon-button context-toggle"
                      onClick={() => handleOpenInspectorTab('context')}
                      title="Context"
                      type="button"
                    >
                      <ContextRingIcon />
                    </button>
                    <button
                      aria-label="Open minimap sidebar"
                      aria-pressed={isRightDockOpen && inspectorTab === 'minimap'}
                      className="composer-icon-button"
                      onClick={() => handleOpenInspectorTab('minimap')}
                      title="Minimap"
                      type="button"
                    >
                      <MinimapIcon />
                    </button>
                    <SpeechInputControl
                      feedback={speechFeedback}
                      isSupported={isSpeechSupported}
                      onStart={handleStartSpeechRecognition}
                      onStop={handleStopSpeechRecognition}
                      state={speechState}
                    />
                    <button
                      className="secondary-button composer-propose-button"
                      disabled={isAsking || isProposingKnowledge}
                      onClick={() => void handleSubmitKnowledgeProposal()}
                      type="button"
                    >
                      {isProposingKnowledge ? 'Proposing...' : 'Propose knowledge'}
                    </button>
                    <button className="composer-send-button" disabled={isAsking} type="submit">
                      <SendIcon />
                      <span>{isAsking ? 'Asking...' : 'Ask'}</span>
                    </button>
                  </div>

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
                {knowledgeSubmitError ? (
                  <p className="form-feedback form-feedback-error" role="alert">
                    {knowledgeSubmitError}
                  </p>
                ) : null}
              </form>
            </section>

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
                projectId={projectId}
                state={observabilityState}
                status={observabilityStatus}
                summary={observabilitySummary}
              />
            ) : activeSettingsModule === 'runtime' ? (
              <RuntimeSettingsPanel
                activeSubmodule={runtimeSubmodule}
                chatConnectionId={globalChatConnectionId}
                chatModelId={globalChatModelId}
                chatModels={runtimeChatModels}
                chatRetrievalSettings={runtimeChatRetrieval}
                connectionBaseUrl={connectionBaseUrl}
                connectionCapabilities={connectionCapabilities}
                connectionProvider={connectionProvider}
                connectionType={connectionType}
                connections={runtimeConnections}
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
                onConnectionProviderChange={setConnectionProvider}
                onConnectionTypeChange={setConnectionType}
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
                onRefreshConnections={() =>
                  void handleRefreshRuntimeConnections()
                }
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
                onSaveSecret={(event) => void handleSaveSecret(event)}
                onSyncProviderModels={(event) =>
                  void handleSyncProviderModels(event)
                }
                onModelSyncConnectionIdChange={setModelSyncConnectionId}
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
                secretConnectionId={secretConnectionId}
                secretValue={secretValue}
                modelSyncConnectionId={modelSyncConnectionId}
                providerModels={runtimeProviderModels}
                slots={runtimeSlots}
                state={runtimeState}
                onSecretConnectionIdChange={setSecretConnectionId}
                onSecretValueChange={setSecretValue}
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
        <button
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Collapse left sidebar' : 'Open left sidebar'}
          className="sidebar-burger"
          onClick={onToggle}
          title={isOpen ? 'Collapse menu' : 'Open menu'}
          type="button"
        >
          <MenuIcon />
        </button>
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
    <button
      aria-pressed={active}
      className={active ? 'sidebar-nav-button sidebar-nav-button-active' : 'sidebar-nav-button'}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
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

function ProjectList({
  activeProjectId,
  onSelectProject,
  projects,
}: {
  activeProjectId: string
  onSelectProject(project: Project): void
  projects: Project[]
}) {
  if (projects.length === 0) {
    return <p className="empty-copy">No projects loaded.</p>
  }

  return (
    <ul className="authoring-list" aria-label="Projects">
      {projects.map((project) => {
        const canAccess = project.can_access !== false
        const roleLabel = canAccess ? (project.access_role ?? project.embedding_mode) : 'no access'
        return (
          <li key={project.id}>
            <button
              aria-label={`Select ${project.name}`}
              className={[
                'authoring-row',
                project.id === activeProjectId ? 'authoring-row-active' : '',
                canAccess ? '' : 'authoring-row-disabled',
              ]
                .filter(Boolean)
                .join(' ')}
              disabled={!canAccess}
              onClick={() => onSelectProject(project)}
              type="button"
            >
              <span>
                <strong>{project.name}</strong>
                <small>{project.id}</small>
              </span>
              <em>{roleLabel}</em>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function SettingsPanel({ children }: { children: ReactNode }) {
  return (
    <section className="settings-shell" aria-labelledby="settings-title">
      <header className="settings-shell-header">
        <div>
          <p className="panel-label">Settings</p>
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

function RuntimeSettingsPanel({
  activeSubmodule,
  chatConnectionId,
  chatModelId,
  chatModels,
  chatRetrievalSettings,
  connectionBaseUrl,
  connectionCapabilities,
  connectionProvider,
  connectionType,
  connections,
  error,
  globalChatRerankCandidateLimit,
  globalChatRerankEnabled,
  globalChatRetrievalLimit,
  globalSlot,
  globalSlotConnectionId,
  globalSlotModelId,
  onChatConnectionIdChange,
  onChatModelIdChange,
  onConnectionBaseUrlChange,
  onConnectionCapabilitiesChange,
  onConnectionProviderChange,
  onConnectionTypeChange,
  onGlobalChatRerankCandidateLimitChange,
  onGlobalChatRerankEnabledChange,
  onGlobalChatRetrievalLimitChange,
  onGlobalSlotChange,
  onGlobalSlotConnectionIdChange,
  onGlobalSlotModelIdChange,
  onProjectChatRerankCandidateLimitChange,
  onProjectChatRerankEnabledChange,
  onProjectChatRetrievalLimitChange,
  onProjectSlotChange,
  onProjectSlotConnectionIdChange,
  onProjectSlotModelIdChange,
  onRefreshConnections,
  onRefreshGlobalDefaults,
  onRefreshModelCatalog,
  onRefreshProjectOverrides,
  onResetProjectChatRetrieval,
  onResetProjectSlot,
  onSaveConnection,
  onSaveGlobalChatModel,
  onSaveGlobalChatRetrieval,
  onSaveGlobalSlot,
  onSaveProjectChatRetrieval,
  onSaveProjectOverride,
  onSaveSecret,
  onSyncProviderModels,
  onModelSyncConnectionIdChange,
  onSecretConnectionIdChange,
  onSecretValueChange,
  modelSyncConnectionId,
  providerModels,
  projectId,
  projectChatRerankCandidateLimit,
  projectChatRerankEnabled,
  projectChatRetrievalLimit,
  projectRuntimeSettings,
  projectSlot,
  projectSlotConnectionId,
  projectSlotModelId,
  secretConnectionId,
  secretValue,
  slots,
  state,
}: {
  activeSubmodule: RuntimeSubmodule
  chatConnectionId: string
  chatModelId: string
  chatModels: ChatModel[]
  chatRetrievalSettings: ChatRetrievalSettings | null
  connectionBaseUrl: string
  connectionCapabilities: string
  connectionProvider: string
  connectionType: string
  connections: ProviderConnection[]
  error: string | null
  globalChatRerankCandidateLimit: number
  globalChatRerankEnabled: boolean
  globalChatRetrievalLimit: number
  globalSlot: string
  globalSlotConnectionId: string
  globalSlotModelId: string
  onChatConnectionIdChange(value: string): void
  onChatModelIdChange(value: string): void
  onConnectionBaseUrlChange(value: string): void
  onConnectionCapabilitiesChange(value: string): void
  onConnectionProviderChange(value: string): void
  onConnectionTypeChange(value: string): void
  onGlobalChatRerankCandidateLimitChange(value: number): void
  onGlobalChatRerankEnabledChange(value: boolean): void
  onGlobalChatRetrievalLimitChange(value: number): void
  onGlobalSlotChange(value: string): void
  onGlobalSlotConnectionIdChange(value: string): void
  onGlobalSlotModelIdChange(value: string): void
  onProjectChatRerankCandidateLimitChange(value: number): void
  onProjectChatRerankEnabledChange(value: boolean): void
  onProjectChatRetrievalLimitChange(value: number): void
  onProjectSlotChange(value: string): void
  onProjectSlotConnectionIdChange(value: string): void
  onProjectSlotModelIdChange(value: string): void
  onRefreshConnections(): void
  onRefreshGlobalDefaults(): void
  onRefreshModelCatalog(): void
  onRefreshProjectOverrides(): void
  onResetProjectChatRetrieval(): void
  onResetProjectSlot(slot: string): void
  onSaveConnection(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatModel(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalSlot(event: FormEvent<HTMLFormElement>): void
  onSaveProjectChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveProjectOverride(event: FormEvent<HTMLFormElement>): void
  onSaveSecret(event: FormEvent<HTMLFormElement>): void
  onSyncProviderModels(event: FormEvent<HTMLFormElement>): void
  onModelSyncConnectionIdChange(value: string): void
  onSecretConnectionIdChange(value: string): void
  onSecretValueChange(value: string): void
  modelSyncConnectionId: string
  providerModels: ProviderModel[]
  projectId: string
  projectChatRerankCandidateLimit: number
  projectChatRerankEnabled: boolean
  projectChatRetrievalLimit: number
  projectRuntimeSettings: ProjectRuntimeSettings | null
  projectSlot: string
  projectSlotConnectionId: string
  projectSlotModelId: string
  secretConnectionId: string
  secretValue: string
  slots: RuntimeSlotDefault[]
  state: RequestState
}) {
  const globalSlotConnections = connectionsForCapability(connections, globalSlot)
  const globalSlotModelOptions = providerModelOptions({
    capability: globalSlot,
    connectionId: globalSlotConnectionId,
    providerModels,
    selectedModelId: globalSlotModelId,
  })
  const chatConnections = connectionsForCapability(connections, 'chat')
  const chatModelOptions = providerModelOptions({
    capability: 'chat',
    connectionId: chatConnectionId,
    configuredModels: chatModels,
    providerModels,
    selectedModelId: chatModelId,
  })
  const projectSlotConnections = connectionsForCapability(connections, projectSlot)
  const projectSlotModelOptions = providerModelOptions({
    capability: projectSlot,
    connectionId: projectSlotConnectionId,
    providerModels,
    selectedModelId: projectSlotModelId,
  })
  const globalSlotSyncMessage = missingSyncedModelMessage({
    connectionId: globalSlotConnectionId,
    modelOptions: globalSlotModelOptions,
    target: globalSlot,
  })
  const chatSyncMessage = missingSyncedModelMessage({
    connectionId: chatConnectionId,
    modelOptions: chatModelOptions,
    target: 'chat default',
  })
  const projectSlotSyncMessage = missingSyncedModelMessage({
    connectionId: projectSlotConnectionId,
    modelOptions: projectSlotModelOptions,
    target: projectSlot,
  })

  const activePanel =
    activeSubmodule === 'connections' ? (
      <RuntimeConnectionsPanel
        connectionBaseUrl={connectionBaseUrl}
        connectionCapabilities={connectionCapabilities}
        connectionProvider={connectionProvider}
        connectionType={connectionType}
        connections={connections}
        onConnectionBaseUrlChange={onConnectionBaseUrlChange}
        onConnectionCapabilitiesChange={onConnectionCapabilitiesChange}
        onConnectionProviderChange={onConnectionProviderChange}
        onConnectionTypeChange={onConnectionTypeChange}
        onRefresh={onRefreshConnections}
        onSaveConnection={onSaveConnection}
        onSaveSecret={onSaveSecret}
        onSecretConnectionIdChange={onSecretConnectionIdChange}
        onSecretValueChange={onSecretValueChange}
        secretConnectionId={secretConnectionId}
        secretValue={secretValue}
        state={state}
      />
    ) : activeSubmodule === 'model_catalog' ? (
      <RuntimeModelCatalogPanel
        connections={connections}
        modelSyncConnectionId={modelSyncConnectionId}
        onModelSyncConnectionIdChange={onModelSyncConnectionIdChange}
        onRefresh={onRefreshModelCatalog}
        onSyncProviderModels={onSyncProviderModels}
        providerModels={providerModels}
        state={state}
      />
    ) : activeSubmodule === 'global_defaults' ? (
      <RuntimeGlobalDefaultsPanel
        chatConnectionId={chatConnectionId}
        chatConnections={chatConnections}
        chatModelId={chatModelId}
        chatModelOptions={chatModelOptions}
        chatModels={chatModels}
        chatRetrievalSettings={chatRetrievalSettings}
        chatSyncMessage={chatSyncMessage}
        globalChatRerankCandidateLimit={globalChatRerankCandidateLimit}
        globalChatRerankEnabled={globalChatRerankEnabled}
        globalChatRetrievalLimit={globalChatRetrievalLimit}
        globalSlot={globalSlot}
        globalSlotConnectionId={globalSlotConnectionId}
        globalSlotConnections={globalSlotConnections}
        globalSlotModelId={globalSlotModelId}
        globalSlotModelOptions={globalSlotModelOptions}
        globalSlotSyncMessage={globalSlotSyncMessage}
        onChatConnectionIdChange={onChatConnectionIdChange}
        onChatModelIdChange={onChatModelIdChange}
        onGlobalChatRerankCandidateLimitChange={
          onGlobalChatRerankCandidateLimitChange
        }
        onGlobalChatRerankEnabledChange={onGlobalChatRerankEnabledChange}
        onGlobalChatRetrievalLimitChange={onGlobalChatRetrievalLimitChange}
        onGlobalSlotChange={onGlobalSlotChange}
        onGlobalSlotConnectionIdChange={onGlobalSlotConnectionIdChange}
        onGlobalSlotModelIdChange={onGlobalSlotModelIdChange}
        onRefresh={onRefreshGlobalDefaults}
        onSaveGlobalChatModel={onSaveGlobalChatModel}
        onSaveGlobalChatRetrieval={onSaveGlobalChatRetrieval}
        onSaveGlobalSlot={onSaveGlobalSlot}
        slots={slots}
        state={state}
      />
    ) : (
      <RuntimeProjectOverridesPanel
        onProjectChatRerankCandidateLimitChange={
          onProjectChatRerankCandidateLimitChange
        }
        onProjectChatRerankEnabledChange={onProjectChatRerankEnabledChange}
        onProjectChatRetrievalLimitChange={onProjectChatRetrievalLimitChange}
        onProjectSlotChange={onProjectSlotChange}
        onProjectSlotConnectionIdChange={onProjectSlotConnectionIdChange}
        onProjectSlotModelIdChange={onProjectSlotModelIdChange}
        onRefresh={onRefreshProjectOverrides}
        onResetProjectChatRetrieval={onResetProjectChatRetrieval}
        onResetProjectSlot={onResetProjectSlot}
        onSaveProjectChatRetrieval={onSaveProjectChatRetrieval}
        onSaveProjectOverride={onSaveProjectOverride}
        projectChatRerankCandidateLimit={projectChatRerankCandidateLimit}
        projectChatRerankEnabled={projectChatRerankEnabled}
        projectChatRetrievalLimit={projectChatRetrievalLimit}
        projectId={projectId}
        projectRuntimeSettings={projectRuntimeSettings}
        projectSlot={projectSlot}
        projectSlotConnectionId={projectSlotConnectionId}
        projectSlotConnections={projectSlotConnections}
        projectSlotModelId={projectSlotModelId}
        projectSlotModelOptions={projectSlotModelOptions}
        projectSlotSyncMessage={projectSlotSyncMessage}
        state={state}
      />
    )

  return (
    <div className="runtime-grid runtime-grid-focused">
      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}
      {activePanel}
    </div>
  )
}

function RuntimeConnectionsPanel({
  connectionBaseUrl,
  connectionCapabilities,
  connectionProvider,
  connectionType,
  connections,
  onConnectionBaseUrlChange,
  onConnectionCapabilitiesChange,
  onConnectionProviderChange,
  onConnectionTypeChange,
  onRefresh,
  onSaveConnection,
  onSaveSecret,
  onSecretConnectionIdChange,
  onSecretValueChange,
  secretConnectionId,
  secretValue,
  state,
}: {
  connectionBaseUrl: string
  connectionCapabilities: string
  connectionProvider: string
  connectionType: string
  connections: ProviderConnection[]
  onConnectionBaseUrlChange(value: string): void
  onConnectionCapabilitiesChange(value: string): void
  onConnectionProviderChange(value: string): void
  onConnectionTypeChange(value: string): void
  onRefresh(): void
  onSaveConnection(event: FormEvent<HTMLFormElement>): void
  onSaveSecret(event: FormEvent<HTMLFormElement>): void
  onSecretConnectionIdChange(value: string): void
  onSecretValueChange(value: string): void
  secretConnectionId: string
  secretValue: string
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel" aria-labelledby="runtime-connections-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-connections-title">Connections</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh connections'}
      </button>

      <section className="runtime-section" aria-label="Provider connections">
        <h3>Connections</h3>
        <ul className="authoring-list">
          {connections.length === 0 ? (
            <li className="authoring-row authoring-row-static">
              <span>No runtime connections loaded.</span>
            </li>
          ) : (
            connections.map((connection) => (
              <li className="authoring-row authoring-row-static" key={connection.connection_id}>
                <span>
                  <strong>{connection.connection_id}</strong>
                  <small>
                    {connection.provider} / {connection.connection_type}
                  </small>
                  <small>{connection.capabilities.join(', ')}</small>
                  {connection.base_url ? <small>{connection.base_url}</small> : null}
                  <ConnectionSecretSummary connection={connection} />
                </span>
                <em>{connection.connection_type}</em>
              </li>
            ))
          )}
        </ul>
      </section>

      <form className="authoring-form" onSubmit={onSaveConnection}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Provider</span>
            <select
              onChange={(event) =>
                onConnectionProviderChange(event.currentTarget.value)
              }
              value={connectionProvider}
            >
              <option value="qwen">qwen</option>
              <option value="local_openai_compatible">
                local_openai_compatible
              </option>
              <option value="fake">fake</option>
            </select>
          </label>
          <label className="field">
            <span>Connection type</span>
            <select
              onChange={(event) => onConnectionTypeChange(event.currentTarget.value)}
              value={connectionType}
            >
              <option value="hosted">hosted</option>
              <option value="local">local</option>
              <option value="fake">fake</option>
            </select>
          </label>
          <label className="field">
            <span>Base URL</span>
            <input
              onChange={(event) =>
                onConnectionBaseUrlChange(event.currentTarget.value)
              }
              value={connectionBaseUrl}
            />
          </label>
          <label className="field runtime-field-wide">
            <span>Capabilities</span>
            <input
              onChange={(event) =>
                onConnectionCapabilitiesChange(event.currentTarget.value)
              }
              value={connectionCapabilities}
            />
          </label>
        </div>
        <button type="submit">Save connection</button>
      </form>

      <form className="authoring-form" onSubmit={onSaveSecret}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Secret connection</span>
            <ConnectionSelect
              connections={connections}
              onChange={onSecretConnectionIdChange}
              testId="secret-connection-select"
              value={secretConnectionId}
            />
          </label>
          <label className="field">
            <span>API key</span>
            <input
              autoComplete="off"
              onChange={(event) => onSecretValueChange(event.currentTarget.value)}
              type="password"
              value={secretValue}
            />
          </label>
        </div>
        <button type="submit">Save secret</button>
      </form>
    </section>
  )
}

function RuntimeModelCatalogPanel({
  connections,
  modelSyncConnectionId,
  onModelSyncConnectionIdChange,
  onRefresh,
  onSyncProviderModels,
  providerModels,
  state,
}: {
  connections: ProviderConnection[]
  modelSyncConnectionId: string
  onModelSyncConnectionIdChange(value: string): void
  onRefresh(): void
  onSyncProviderModels(event: FormEvent<HTMLFormElement>): void
  providerModels: ProviderModel[]
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel" aria-labelledby="runtime-model-catalog-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-model-catalog-title">Model catalog</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh catalog'}
      </button>

      <form className="authoring-form" onSubmit={onSyncProviderModels}>
        <div className="runtime-form-grid">
          <label className="field runtime-field-wide">
            <span>Model sync connection</span>
            <ConnectionSelect
              connections={connections}
              onChange={onModelSyncConnectionIdChange}
              testId="model-sync-connection-select"
              value={modelSyncConnectionId}
            />
          </label>
        </div>
        <button type="submit">Sync models</button>
      </form>

      <ProviderModelCatalogView providerModels={providerModels} />
    </section>
  )
}

function RuntimeGlobalDefaultsPanel({
  chatConnectionId,
  chatConnections,
  chatModelId,
  chatModelOptions,
  chatModels,
  chatRetrievalSettings,
  chatSyncMessage,
  globalChatRerankCandidateLimit,
  globalChatRerankEnabled,
  globalChatRetrievalLimit,
  globalSlot,
  globalSlotConnectionId,
  globalSlotConnections,
  globalSlotModelId,
  globalSlotModelOptions,
  globalSlotSyncMessage,
  onChatConnectionIdChange,
  onChatModelIdChange,
  onGlobalChatRerankCandidateLimitChange,
  onGlobalChatRerankEnabledChange,
  onGlobalChatRetrievalLimitChange,
  onGlobalSlotChange,
  onGlobalSlotConnectionIdChange,
  onGlobalSlotModelIdChange,
  onRefresh,
  onSaveGlobalChatModel,
  onSaveGlobalChatRetrieval,
  onSaveGlobalSlot,
  slots,
  state,
}: {
  chatConnectionId: string
  chatConnections: ProviderConnection[]
  chatModelId: string
  chatModelOptions: ProviderModelOption[]
  chatModels: ChatModel[]
  chatRetrievalSettings: ChatRetrievalSettings | null
  chatSyncMessage: string | null
  globalChatRerankCandidateLimit: number
  globalChatRerankEnabled: boolean
  globalChatRetrievalLimit: number
  globalSlot: string
  globalSlotConnectionId: string
  globalSlotConnections: ProviderConnection[]
  globalSlotModelId: string
  globalSlotModelOptions: ProviderModelOption[]
  globalSlotSyncMessage: string | null
  onChatConnectionIdChange(value: string): void
  onChatModelIdChange(value: string): void
  onGlobalChatRerankCandidateLimitChange(value: number): void
  onGlobalChatRerankEnabledChange(value: boolean): void
  onGlobalChatRetrievalLimitChange(value: number): void
  onGlobalSlotChange(value: string): void
  onGlobalSlotConnectionIdChange(value: string): void
  onGlobalSlotModelIdChange(value: string): void
  onRefresh(): void
  onSaveGlobalChatModel(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalSlot(event: FormEvent<HTMLFormElement>): void
  slots: RuntimeSlotDefault[]
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel" aria-labelledby="runtime-global-defaults-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-global-defaults-title">Global defaults</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload global defaults'}
      </button>

      <RuntimeSlotList slots={slots} />

      <form className="authoring-form" onSubmit={onSaveGlobalSlot}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Global slot</span>
            <select
              data-testid="global-slot-select"
              onChange={(event) => onGlobalSlotChange(event.currentTarget.value)}
              value={globalSlot}
            >
              {RUNTIME_SLOTS.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Global slot connection</span>
            <ConnectionSelect
              connections={globalSlotConnections}
              onChange={onGlobalSlotConnectionIdChange}
              testId="global-slot-connection-select"
              value={globalSlotConnectionId}
            />
          </label>
          <label className="field">
            <span>Global slot model</span>
            <ProviderModelSelect
              models={globalSlotModelOptions}
              onChange={onGlobalSlotModelIdChange}
              testId="global-slot-model-select"
              value={globalSlotModelId}
            />
          </label>
        </div>
        {globalSlotSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">
            {globalSlotSyncMessage}
          </p>
        ) : null}
        <button disabled={globalSlotSyncMessage !== null} type="submit">
          Save global slot
        </button>
      </form>

      <section className="runtime-section" aria-label="Global chat models">
        <h3>Chat models</h3>
        <ul className="authoring-list">
          {chatModels.length === 0 ? (
            <li className="authoring-row authoring-row-static">
              <span>No chat models loaded.</span>
            </li>
          ) : (
            chatModels.map((model) => (
              <li
                className="authoring-row authoring-row-static"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <span>
                  <strong>{model.model_id}</strong>
                  <small>{model.connection_id}</small>
                </span>
                <em>{model.is_default ? 'default' : 'enabled'}</em>
              </li>
            ))
          )}
        </ul>
      </section>

      <form className="authoring-form" onSubmit={onSaveGlobalChatModel}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Chat connection</span>
            <ConnectionSelect
              connections={chatConnections}
              onChange={onChatConnectionIdChange}
              testId="chat-connection-select"
              value={chatConnectionId}
            />
          </label>
          <label className="field">
            <span>Chat model</span>
            <ProviderModelSelect
              models={chatModelOptions}
              onChange={onChatModelIdChange}
              testId="chat-model-select"
              value={chatModelId}
            />
          </label>
        </div>
        {chatSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">{chatSyncMessage}</p>
        ) : null}
        <button disabled={chatSyncMessage !== null} type="submit">
          Save chat default
        </button>
      </form>

      <section className="runtime-section" aria-label="Global chat retrieval">
        <h3>Chat retrieval</h3>
        {chatRetrievalSettings ? (
          <ul className="authoring-list">
            <li className="authoring-row authoring-row-static">
              <span>
                <strong>global defaults</strong>
                <small>
                  limit {chatRetrievalSettings.retrieval_limit} / candidate{' '}
                  {chatRetrievalSettings.rerank_candidate_limit}
                </small>
              </span>
              <em>{chatRetrievalSettings.rerank_enabled ? 'rerank on' : 'rerank off'}</em>
            </li>
          </ul>
        ) : (
          <p className="empty-copy">No chat retrieval defaults loaded.</p>
        )}
        <form className="authoring-form" onSubmit={onSaveGlobalChatRetrieval}>
          <div className="runtime-form-grid">
            <label className="field">
              <span>Retrieval limit</span>
              <input
                max={CHAT_RETRIEVAL_MAX_LIMIT}
                min={1}
                onChange={(event) =>
                  onGlobalChatRetrievalLimitChange(
                    normalizeChatRetrievalLimit(event.currentTarget.value),
                  )
                }
                type="number"
                value={globalChatRetrievalLimit}
              />
            </label>
            <label className="field">
              <span>Rerank</span>
              <select
                onChange={(event) =>
                  onGlobalChatRerankEnabledChange(
                    event.currentTarget.value === 'true',
                  )
                }
                value={String(globalChatRerankEnabled)}
              >
                <option value="true">on</option>
                <option value="false">off</option>
              </select>
            </label>
            <label className="field">
              <span>Candidate limit</span>
              <input
                max={CHAT_RETRIEVAL_MAX_LIMIT}
                min={1}
                onChange={(event) =>
                  onGlobalChatRerankCandidateLimitChange(
                    normalizeChatRetrievalLimit(event.currentTarget.value),
                  )
                }
                type="number"
                value={globalChatRerankCandidateLimit}
              />
            </label>
          </div>
          <button type="submit">Save chat retrieval</button>
        </form>
      </section>
    </section>
  )
}

function RuntimeProjectOverridesPanel({
  onProjectChatRerankCandidateLimitChange,
  onProjectChatRerankEnabledChange,
  onProjectChatRetrievalLimitChange,
  onProjectSlotChange,
  onProjectSlotConnectionIdChange,
  onProjectSlotModelIdChange,
  onRefresh,
  onResetProjectChatRetrieval,
  onResetProjectSlot,
  onSaveProjectChatRetrieval,
  onSaveProjectOverride,
  projectChatRerankCandidateLimit,
  projectChatRerankEnabled,
  projectChatRetrievalLimit,
  projectId,
  projectRuntimeSettings,
  projectSlot,
  projectSlotConnectionId,
  projectSlotConnections,
  projectSlotModelId,
  projectSlotModelOptions,
  projectSlotSyncMessage,
  state,
}: {
  onProjectChatRerankCandidateLimitChange(value: number): void
  onProjectChatRerankEnabledChange(value: boolean): void
  onProjectChatRetrievalLimitChange(value: number): void
  onProjectSlotChange(value: string): void
  onProjectSlotConnectionIdChange(value: string): void
  onProjectSlotModelIdChange(value: string): void
  onRefresh(): void
  onResetProjectChatRetrieval(): void
  onResetProjectSlot(slot: string): void
  onSaveProjectChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveProjectOverride(event: FormEvent<HTMLFormElement>): void
  projectChatRerankCandidateLimit: number
  projectChatRerankEnabled: boolean
  projectChatRetrievalLimit: number
  projectId: string
  projectRuntimeSettings: ProjectRuntimeSettings | null
  projectSlot: string
  projectSlotConnectionId: string
  projectSlotConnections: ProviderConnection[]
  projectSlotModelId: string
  projectSlotModelOptions: ProviderModelOption[]
  projectSlotSyncMessage: string | null
  state: RequestState
}) {
  return (
    <section
      className="panel runtime-panel runtime-panel-wide"
      aria-label="Project runtime settings"
    >
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-project-overrides-title">Project overrides</h2>
        </div>
        <span className="status">{projectId.trim() || 'No project'}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload project settings'}
      </button>

      <ProjectRuntimeSettingsView
        onResetProjectSlot={onResetProjectSlot}
        settings={projectRuntimeSettings}
      />

      <form className="authoring-form" onSubmit={onSaveProjectChatRetrieval}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Retrieval limit</span>
            <input
              max={CHAT_RETRIEVAL_MAX_LIMIT}
              min={1}
              onChange={(event) =>
                onProjectChatRetrievalLimitChange(
                  normalizeChatRetrievalLimit(event.currentTarget.value),
                )
              }
              type="number"
              value={projectChatRetrievalLimit}
            />
          </label>
          <label className="field">
            <span>Rerank</span>
            <select
              onChange={(event) =>
                onProjectChatRerankEnabledChange(
                  event.currentTarget.value === 'true',
                )
              }
              value={String(projectChatRerankEnabled)}
            >
              <option value="true">on</option>
              <option value="false">off</option>
            </select>
          </label>
          <label className="field">
            <span>Candidate limit</span>
            <input
              max={CHAT_RETRIEVAL_MAX_LIMIT}
              min={1}
              onChange={(event) =>
                onProjectChatRerankCandidateLimitChange(
                  normalizeChatRetrievalLimit(event.currentTarget.value),
                )
              }
              type="number"
              value={projectChatRerankCandidateLimit}
            />
          </label>
        </div>
        <div className="authoring-row-actions">
          <button type="submit">Save project retrieval override</button>
          {projectRuntimeSettings?.chat_retrieval.source === 'project' ? (
            <button
              className="secondary-button"
              onClick={onResetProjectChatRetrieval}
              type="button"
            >
              Reset chat retrieval to global
            </button>
          ) : null}
        </div>
      </form>

      <form className="authoring-form" onSubmit={onSaveProjectOverride}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Project slot</span>
            <select
              onChange={(event) => onProjectSlotChange(event.currentTarget.value)}
              value={projectSlot}
            >
              {RUNTIME_SLOTS.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Project slot connection</span>
            <ConnectionSelect
              connections={projectSlotConnections}
              onChange={onProjectSlotConnectionIdChange}
              testId="project-slot-connection-select"
              value={projectSlotConnectionId}
            />
          </label>
          <label className="field">
            <span>Project slot model</span>
            <ProviderModelSelect
              models={projectSlotModelOptions}
              onChange={onProjectSlotModelIdChange}
              testId="project-slot-model-select"
              value={projectSlotModelId}
            />
          </label>
        </div>
        {projectSlotSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">
            {projectSlotSyncMessage}
          </p>
        ) : null}
        <button disabled={projectSlotSyncMessage !== null} type="submit">
          Save project override
        </button>
      </form>
    </section>
  )
}

function ConnectionSecretSummary({
  connection,
}: {
  connection: ProviderConnection
}) {
  if (connection.secrets.length === 0) {
    return <small>No secret status</small>
  }
  return (
    <>
      {connection.secrets.map((secret) => (
        <small key={secret.secret_name}>
          {secret.secret_name}{' '}
          {secret.configured ? 'configured' : 'not configured'}
          {secret.last_four ? ` / last four ${secret.last_four}` : ''}
        </small>
      ))}
    </>
  )
}

function ConnectionSelect({
  connections,
  onChange,
  testId,
  value,
}: {
  connections: ProviderConnection[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <select
      data-testid={testId}
      onChange={(event) => onChange(event.currentTarget.value)}
      value={value}
    >
      <option value="">
        {connections.length === 0 ? 'No connections loaded' : 'Select connection'}
      </option>
      {connections.map((connection) => (
        <option key={connection.connection_id} value={connection.connection_id}>
          {connectionOptionLabel(connection)}
        </option>
      ))}
    </select>
  )
}

function ProviderModelSelect({
  models,
  onChange,
  testId,
  value,
}: {
  models: ProviderModelOption[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <select
      data-testid={testId}
      disabled={models.length === 0}
      onChange={(event) => onChange(event.currentTarget.value)}
      value={value}
    >
      <option value="">
        {models.length === 0 ? 'No models loaded' : 'Select model'}
      </option>
      {models.map((model) => (
        <option key={`${model.connection_id}-${model.model_id}`} value={model.model_id}>
          {model.model_id}
        </option>
      ))}
    </select>
  )
}

function ProviderModelCatalogView({
  providerModels,
}: {
  providerModels: ProviderModel[]
}) {
  return (
    <section className="runtime-section" aria-label="Provider model catalog">
      <h3>Model catalog</h3>
      <ul className="authoring-list">
        {providerModels.length === 0 ? (
          <li className="authoring-row authoring-row-static">
            <span>No provider models loaded.</span>
          </li>
        ) : (
          providerModels.map((model) => (
            <li
              className="authoring-row authoring-row-static"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <span>
                <strong>{model.model_id}</strong>
                <small>
                  {model.connection_id} / {model.capabilities.join(', ')}
                </small>
                {model.pricing ? <small>pricing metadata saved</small> : null}
              </span>
              <em>{model.pricing ? 'pricing' : 'metadata'}</em>
            </li>
          ))
        )}
      </ul>
    </section>
  )
}

function RuntimeSlotList({ slots }: { slots: RuntimeSlotDefault[] }) {
  return (
    <ul className="authoring-list" aria-label="Global runtime slots">
      {slots.length === 0 ? (
        <li className="authoring-row authoring-row-static">
          <span>No global slot defaults loaded.</span>
        </li>
      ) : (
        slots.map((slot) => (
          <li className="authoring-row authoring-row-static" key={slot.slot}>
            <span>
              <strong>{slot.slot}</strong>
              <small>
                {slot.connection_id} / {slot.model_id}
              </small>
            </span>
            <em>global</em>
          </li>
        ))
      )}
    </ul>
  )
}

function ProjectRuntimeSettingsView({
  onResetProjectSlot,
  settings,
}: {
  onResetProjectSlot(slot: string): void
  settings: ProjectRuntimeSettings | null
}) {
  if (settings === null) {
    return <p className="empty-copy">No project runtime settings loaded.</p>
  }
  return (
    <div className="project-runtime-grid">
      <section className="runtime-section">
        <h3>Effective slots</h3>
        <ul className="authoring-list">
          {settings.slots.map((slot) => (
            <li className="authoring-row authoring-row-static" key={slot.slot}>
              <span>
                <strong>{slot.slot}</strong>
                <small>
                  {slot.connection_id} / {slot.model_id}
                </small>
              </span>
              <div className="authoring-row-actions">
                <em>{slot.source}</em>
                {slot.source === 'overridden' ? (
                  <button
                    className="compact-button"
                    onClick={() => onResetProjectSlot(slot.slot)}
                    type="button"
                  >
                    Reset {slot.slot} to global
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="runtime-section">
        <h3>Chat pool</h3>
        <ul className="authoring-list">
          {settings.chat_models.map((model) => (
            <li
              className="authoring-row authoring-row-static"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <span>
                <strong>{model.model_id}</strong>
                <small>{model.connection_id}</small>
              </span>
              <div className="authoring-row-actions">
                <em>{model.source}</em>
                <em>{model.is_default ? 'default' : 'enabled'}</em>
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="runtime-section">
        <h3>Chat retrieval</h3>
        <ul className="authoring-list">
          <li className="authoring-row authoring-row-static">
            <span>
              <strong>
                limit {settings.chat_retrieval.retrieval_limit}
              </strong>
              <small>
                candidate {settings.chat_retrieval.rerank_candidate_limit} /{' '}
                {settings.chat_retrieval.rerank_enabled ? 'rerank on' : 'rerank off'}
              </small>
            </span>
            <em>{settings.chat_retrieval.source}</em>
          </li>
        </ul>
      </section>
    </div>
  )
}

function AuthoringPanel({
  activeSubmodule,
  accessError,
  accessState,
  ingestionError,
  ingestionJobs,
  ingestionRun,
  ingestionState,
  knowledgeProposals,
  knowledgeReviewError,
  knowledgeReviewState,
  memberRole,
  memberUserId,
  memberships,
  onCreateProject,
  onCreateSource,
  onCreateUser,
  onEnqueueIngestion,
  onApproveKnowledgeProposal,
  onMemberRoleChange,
  onMemberUserIdChange,
  onProjectIdChange,
  onProjectNameChange,
  onProposalDraftChange,
  onProposalRejectReasonChange,
  onRefreshAccess,
  onRefreshIngestionJobs,
  onRefreshKnowledgeProposals,
  onRefreshSources,
  onRefineKnowledgeProposal,
  onRejectKnowledgeProposal,
  onRetryIngestionJob,
  onRunNextIngestion,
  onSaveProjectMembership,
  onSelectProject,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceTagsChange,
  onSourceTypeChange,
  onUserAccessTokenChange,
  onUserDisplayNameChange,
  onUserLoginChange,
  onUserSystemRoleChange,
  projectError,
  projectId,
  projectName,
  projectState,
  projects,
  proposalDrafts,
  proposalRejectReasons,
  sourceContent,
  sourceError,
  sourceExternalId,
  sourceState,
  sourceTags,
  sourceType,
  sources,
  userAccessToken,
  userDisplayName,
  userLogin,
  userSystemRole,
  users,
}: {
  activeSubmodule: AuthoringSubmodule
  accessError: string | null
  accessState: RequestState
  ingestionError: string | null
  ingestionJobs: IngestionJob[]
  ingestionRun: IngestionRunResponse | null
  ingestionState: RequestState
  knowledgeProposals: KnowledgeProposal[]
  knowledgeReviewError: string | null
  knowledgeReviewState: RequestState
  memberRole: string
  memberUserId: string
  memberships: ProjectMembership[]
  onCreateProject(event: FormEvent<HTMLFormElement>): void
  onCreateSource(event: FormEvent<HTMLFormElement>): void
  onCreateUser(event: FormEvent<HTMLFormElement>): void
  onEnqueueIngestion(source: Source): void
  onApproveKnowledgeProposal(proposal: KnowledgeProposal): void
  onMemberRoleChange(value: string): void
  onMemberUserIdChange(value: string): void
  onProjectIdChange(value: string): void
  onProjectNameChange(value: string): void
  onProposalDraftChange(proposalId: string, value: string): void
  onProposalRejectReasonChange(proposalId: string, value: string): void
  onRefreshAccess(): void
  onRefreshIngestionJobs(): void
  onRefreshKnowledgeProposals(): void
  onRefreshSources(): void
  onRefineKnowledgeProposal(proposal: KnowledgeProposal): void
  onRejectKnowledgeProposal(proposal: KnowledgeProposal): void
  onRetryIngestionJob(job: IngestionJob): void
  onRunNextIngestion(): void
  onSaveProjectMembership(event: FormEvent<HTMLFormElement>): void
  onSelectProject(project: Project): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceTagsChange(value: string): void
  onSourceTypeChange(value: string): void
  onUserAccessTokenChange(value: string): void
  onUserDisplayNameChange(value: string): void
  onUserLoginChange(value: string): void
  onUserSystemRoleChange(value: string): void
  projectError: string | null
  projectId: string
  projectName: string
  projectState: RequestState
  projects: Project[]
  proposalDrafts: Record<string, string>
  proposalRejectReasons: Record<string, string>
  sourceContent: string
  sourceError: string | null
  sourceExternalId: string
  sourceState: RequestState
  sourceTags: string
  sourceType: string
  sources: Source[]
  userAccessToken: string
  userDisplayName: string
  userLogin: string
  userSystemRole: string
  users: User[]
}) {
  const isProjectBusy = projectState === 'loading'
  const isSourceBusy = sourceState === 'loading'
  const isIngestionBusy = ingestionState === 'loading'
  const isAccessBusy = accessState === 'loading'
  const isKnowledgeReviewBusy = knowledgeReviewState === 'loading'

  return (
    <div className="authoring-grid authoring-grid-focused">
      {activeSubmodule === 'projects' ? (
        <section className="panel authoring-panel" aria-labelledby="projects-title">
        <div className="panel-heading">
          <div>
            <p className="panel-label">Projects</p>
            <h2 id="projects-title">Authoring</h2>
          </div>
          <span className={statusClassName(projectState)}>
            {authoringStatusLabel(projectState)}
          </span>
        </div>

        <form className="authoring-form" onSubmit={onCreateProject}>
          <label className="field">
            <span>Project name</span>
            <input
              autoComplete="off"
              name="project-name"
              onChange={(event) => onProjectNameChange(event.currentTarget.value)}
              placeholder="Demo"
              value={projectName}
            />
          </label>
          <div className="form-actions">
            <button disabled={isProjectBusy} type="submit">
              {isProjectBusy ? 'Creating...' : 'Create project'}
            </button>
          </div>
        </form>

        {projectError ? (
          <p className="form-feedback form-feedback-error" role="alert">
            {projectError}
          </p>
        ) : null}

        <ProjectList
          activeProjectId={projectId}
          onSelectProject={onSelectProject}
          projects={projects}
        />
        </section>
      ) : null}

      {activeSubmodule === 'users' ? (
        <ProjectAccessPanel
          error={accessError}
          isBusy={isAccessBusy}
          memberRole={memberRole}
          memberUserId={memberUserId}
          memberships={memberships}
          onCreateUser={onCreateUser}
          onMemberRoleChange={onMemberRoleChange}
          onMemberUserIdChange={onMemberUserIdChange}
          onRefresh={onRefreshAccess}
          onSaveMembership={onSaveProjectMembership}
          onUserAccessTokenChange={onUserAccessTokenChange}
          onUserDisplayNameChange={onUserDisplayNameChange}
          onUserLoginChange={onUserLoginChange}
          onUserSystemRoleChange={onUserSystemRoleChange}
          state={accessState}
          userAccessToken={userAccessToken}
          userDisplayName={userDisplayName}
          userLogin={userLogin}
          userSystemRole={userSystemRole}
          users={users}
        />
      ) : null}

      {activeSubmodule === 'sources' ? (
        <section className="panel authoring-panel" aria-labelledby="sources-title">
        <div className="panel-heading">
          <div>
            <p className="panel-label">Sources</p>
            <h2 id="sources-title">Content registry</h2>
          </div>
          <span className={statusClassName(sourceState)}>
            {authoringStatusLabel(sourceState)}
          </span>
        </div>

        <form className="authoring-form" onSubmit={onCreateSource}>
          <label className="field">
            <span>Project ID</span>
            <input
              autoComplete="off"
              name="authoring-project-id"
              onChange={(event) => onProjectIdChange(event.currentTarget.value)}
              placeholder="Project UUID"
              value={projectId}
            />
          </label>
          <div className="source-form-grid">
            <label className="field">
              <span>Source type</span>
              <select
                name="source-type"
                onChange={(event) => onSourceTypeChange(event.currentTarget.value)}
                value={sourceType}
              >
                <option value="markdown">markdown</option>
                <option value="text">text</option>
                <option value="txt">txt</option>
                <option value="url">url</option>
              </select>
            </label>
            <label className="field">
              <span>External ID</span>
              <input
                autoComplete="off"
                name="source-external-id"
                onChange={(event) =>
                  onSourceExternalIdChange(event.currentTarget.value)
                }
                placeholder="notes.md"
                value={sourceExternalId}
              />
            </label>
          </div>
          <label className="field">
            <span>Content</span>
            <textarea
              name="source-content"
              onChange={(event) => onSourceContentChange(event.currentTarget.value)}
              placeholder="# Notes"
              rows={5}
              value={sourceContent}
            />
          </label>
          <label className="field">
            <span>Tags</span>
            <input
              autoComplete="off"
              name="source-tags"
              onChange={(event) => onSourceTagsChange(event.currentTarget.value)}
              placeholder="docs, local"
              value={sourceTags}
            />
          </label>
          <div className="form-actions">
            <button disabled={isSourceBusy} type="submit">
              {isSourceBusy ? 'Creating...' : 'Create source'}
            </button>
            <button
              className="secondary-button"
              disabled={isSourceBusy}
              onClick={onRefreshSources}
              type="button"
            >
              {isSourceBusy ? 'Refreshing...' : 'Refresh sources'}
            </button>
          </div>
        </form>

        {sourceError ? (
          <p className="form-feedback form-feedback-error" role="alert">
            {sourceError}
          </p>
        ) : null}

        <SourceList onEnqueueIngestion={onEnqueueIngestion} sources={sources} />
        <IngestionJobsPanel
          error={ingestionError}
          jobs={ingestionJobs}
          onRefresh={onRefreshIngestionJobs}
          onRetry={onRetryIngestionJob}
          onRunNext={onRunNextIngestion}
          run={ingestionRun}
          state={ingestionState}
          isBusy={isIngestionBusy}
        />
        </section>
      ) : null}

      {activeSubmodule === 'knowledge' ? (
        <KnowledgeReviewPanel
          drafts={proposalDrafts}
          error={knowledgeReviewError}
          isBusy={isKnowledgeReviewBusy}
          onApprove={onApproveKnowledgeProposal}
          onDraftChange={onProposalDraftChange}
          onRefresh={onRefreshKnowledgeProposals}
          onRefine={onRefineKnowledgeProposal}
          onReject={onRejectKnowledgeProposal}
          onRejectReasonChange={onProposalRejectReasonChange}
          proposals={knowledgeProposals}
          rejectReasons={proposalRejectReasons}
          state={knowledgeReviewState}
        />
      ) : null}
    </div>
  )
}

function ProjectAccessPanel({
  error,
  isBusy,
  memberRole,
  memberUserId,
  memberships,
  onCreateUser,
  onMemberRoleChange,
  onMemberUserIdChange,
  onRefresh,
  onSaveMembership,
  onUserAccessTokenChange,
  onUserDisplayNameChange,
  onUserLoginChange,
  onUserSystemRoleChange,
  state,
  userAccessToken,
  userDisplayName,
  userLogin,
  userSystemRole,
  users,
}: {
  error: string | null
  isBusy: boolean
  memberRole: string
  memberUserId: string
  memberships: ProjectMembership[]
  onCreateUser(event: FormEvent<HTMLFormElement>): void
  onMemberRoleChange(value: string): void
  onMemberUserIdChange(value: string): void
  onRefresh(): void
  onSaveMembership(event: FormEvent<HTMLFormElement>): void
  onUserAccessTokenChange(value: string): void
  onUserDisplayNameChange(value: string): void
  onUserLoginChange(value: string): void
  onUserSystemRoleChange(value: string): void
  state: RequestState
  userAccessToken: string
  userDisplayName: string
  userLogin: string
  userSystemRole: string
  users: User[]
}) {
  return (
    <section className="panel authoring-panel" aria-labelledby="project-access-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Users</p>
          <h2 id="project-access-title">Users</h2>
        </div>
        <span className={statusClassName(state)}>
          {authoringStatusLabel(state)}
        </span>
      </div>

      <form className="authoring-form" onSubmit={onCreateUser}>
        <div className="source-form-grid">
          <label className="field">
            <span>User login</span>
            <input
              autoComplete="off"
              name="user-login"
              onChange={(event) => onUserLoginChange(event.currentTarget.value)}
              placeholder="viewer@example.com"
              value={userLogin}
            />
          </label>
          <label className="field">
            <span>Display name</span>
            <input
              autoComplete="off"
              name="user-display-name"
              onChange={(event) =>
                onUserDisplayNameChange(event.currentTarget.value)
              }
              placeholder="Viewer User"
              value={userDisplayName}
            />
          </label>
        </div>
        <div className="source-form-grid">
          <label className="field">
            <span>System role</span>
            <select
              aria-label="System role"
              name="user-system-role"
              onChange={(event) =>
                onUserSystemRoleChange(event.currentTarget.value)
              }
              value={userSystemRole}
            >
              <option value="user">user</option>
              <option value="superadmin">superadmin</option>
            </select>
          </label>
          <label className="field">
            <span>Access token</span>
            <input
              autoComplete="off"
              name="user-access-token"
              onChange={(event) =>
                onUserAccessTokenChange(event.currentTarget.value)
              }
              placeholder="token"
              value={userAccessToken}
            />
          </label>
        </div>
        <div className="form-actions">
          <button disabled={isBusy} type="submit">
            {isBusy ? 'Creating...' : 'Create user'}
          </button>
          <button
            className="secondary-button"
            disabled={isBusy}
            onClick={onRefresh}
            type="button"
          >
            {isBusy ? 'Refreshing...' : 'Refresh access'}
          </button>
        </div>
      </form>

      <form className="authoring-form" onSubmit={onSaveMembership}>
        <div className="source-form-grid">
          <label className="field">
            <span>Member user ID</span>
            <input
              autoComplete="off"
              name="member-user-id"
              onChange={(event) => onMemberUserIdChange(event.currentTarget.value)}
              placeholder="User UUID"
              value={memberUserId}
            />
          </label>
          <label className="field">
            <span>Project role</span>
            <select
              aria-label="Project role"
              name="member-role"
              onChange={(event) => onMemberRoleChange(event.currentTarget.value)}
              value={memberRole}
            >
              <option value="viewer">viewer</option>
              <option value="contributor">contributor</option>
              <option value="admin">admin</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button disabled={isBusy} type="submit">
            {isBusy ? 'Saving...' : 'Save membership'}
          </button>
        </div>
      </form>

      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}

      <UserAccessLists memberships={memberships} users={users} />
    </section>
  )
}

function UserAccessLists({
  memberships,
  users,
}: {
  memberships: ProjectMembership[]
  users: User[]
}) {
  if (users.length === 0 && memberships.length === 0) {
    return <p className="empty-copy">No users or memberships loaded.</p>
  }

  return (
    <div className="access-list-grid">
      <ul className="authoring-list" aria-label="Users">
        {users.map((user) => (
          <li key={user.id}>
            <div className="authoring-row authoring-row-static">
              <span>
                <strong>{user.login}</strong>
                <small>{user.display_name}</small>
                <small>{user.id}</small>
              </span>
              <em>{user.system_role}</em>
            </div>
          </li>
        ))}
      </ul>
      <ul className="authoring-list" aria-label="Project memberships">
        {memberships.map((membership) => (
          <li key={membership.id}>
            <div className="authoring-row authoring-row-static">
              <span>
                <strong>{membership.user_id}</strong>
                <small>{membership.project_id}</small>
              </span>
              <em>{membership.role}</em>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function KnowledgeReviewPanel({
  drafts,
  error,
  isBusy,
  onApprove,
  onDraftChange,
  onRefresh,
  onRefine,
  onReject,
  onRejectReasonChange,
  proposals,
  rejectReasons,
  state,
}: {
  drafts: Record<string, string>
  error: string | null
  isBusy: boolean
  onApprove(proposal: KnowledgeProposal): void
  onDraftChange(proposalId: string, value: string): void
  onRefresh(): void
  onRefine(proposal: KnowledgeProposal): void
  onReject(proposal: KnowledgeProposal): void
  onRejectReasonChange(proposalId: string, value: string): void
  proposals: KnowledgeProposal[]
  rejectReasons: Record<string, string>
  state: RequestState
}) {
  return (
    <section className="panel authoring-panel" aria-labelledby="knowledge-review-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Knowledge</p>
          <h2 id="knowledge-review-title">Pending proposals</h2>
        </div>
        <span className={statusClassName(state)}>
          {authoringStatusLabel(state)}
        </span>
      </div>

      <div className="form-actions">
        <button
          className="secondary-button"
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
        >
          {isBusy ? 'Refreshing...' : 'Refresh proposals'}
        </button>
      </div>

      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}

      {proposals.length === 0 ? (
        <p className="empty-copy">No pending knowledge proposals loaded.</p>
      ) : (
        <ul className="authoring-list" aria-label="Knowledge proposals">
          {proposals.map((proposal) => {
            const draft = proposalDraftText(drafts, proposal)
            return (
              <li key={proposal.id}>
                <div className="authoring-row authoring-row-static knowledge-proposal-row">
                  <span>
                    <strong>{proposal.proposed_text}</strong>
                    <small>{proposal.id}</small>
                    <small>{proposal.status}</small>
                  </span>
                  <div className="knowledge-proposal-actions">
                    <label className="field">
                      <span>Refined text</span>
                      <textarea
                        name={`proposal-refined-${proposal.id}`}
                        onChange={(event) =>
                          onDraftChange(proposal.id, event.currentTarget.value)
                        }
                        rows={3}
                        value={draft}
                      />
                    </label>
                    <label className="field">
                      <span>Reject reason</span>
                      <input
                        autoComplete="off"
                        name={`proposal-reject-${proposal.id}`}
                        onChange={(event) =>
                          onRejectReasonChange(
                            proposal.id,
                            event.currentTarget.value,
                          )
                        }
                        placeholder="Reason"
                        value={rejectReasons[proposal.id] ?? ''}
                      />
                    </label>
                    <div className="form-actions">
                      <button
                        className="secondary-button"
                        disabled={isBusy}
                        onClick={() => onRefine(proposal)}
                        type="button"
                      >
                        Refine proposal
                      </button>
                      <button
                        disabled={isBusy}
                        onClick={() => onApprove(proposal)}
                        type="button"
                      >
                        Approve proposal
                      </button>
                      <button
                        className="secondary-button"
                        disabled={isBusy}
                        onClick={() => onReject(proposal)}
                        type="button"
                      >
                        Reject proposal
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function SourceList({
  onEnqueueIngestion,
  sources,
}: {
  onEnqueueIngestion(source: Source): void
  sources: Source[]
}) {
  if (sources.length === 0) {
    return <p className="empty-copy">No sources loaded.</p>
  }

  return (
    <ul className="authoring-list" aria-label="Sources">
      {sources.map((source) => (
        <li key={source.id}>
          <div className="authoring-row authoring-row-static">
            <span>
              <strong>{source.external_id}</strong>
              <small>{source.id}</small>
              <small>Ready to queue ingestion</small>
              <small>Queue ingestion when this source should be indexed.</small>
            </span>
            <div className="authoring-row-actions">
              <em>{source.source_type}</em>
              <button
                aria-label={`Enqueue ingestion for ${source.external_id}`}
                className="secondary-button compact-button"
                onClick={() => onEnqueueIngestion(source)}
                type="button"
              >
                Queue
              </button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function IngestionJobsPanel({
  error,
  isBusy,
  jobs,
  onRefresh,
  onRetry,
  onRunNext,
  run,
  state,
}: {
  error: string | null
  isBusy: boolean
  jobs: IngestionJob[]
  onRefresh(): void
  onRetry(job: IngestionJob): void
  onRunNext(): void
  run: IngestionRunResponse | null
  state: RequestState
}) {
  return (
    <section className="ingestion-panel" aria-labelledby="ingestion-jobs-title">
      <div className="ingestion-heading">
        <div>
          <p className="panel-label">Ingestion</p>
          <h3 id="ingestion-jobs-title">Jobs</h3>
        </div>
        <span className={statusClassName(state)}>
          {ingestionStatusLabel(state)}
        </span>
      </div>

      <div className="form-actions">
        <button
          className="secondary-button"
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
        >
          Refresh jobs
        </button>
        <button disabled={isBusy} onClick={onRunNext} type="button">
          Run next job
        </button>
      </div>

      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}

      {run ? (
        <p className="ingestion-run">
          <span>{`Last run ${run.status}`}</span>
          <strong>{run.status}</strong>
          <span>{ingestionRunMessage(run)}</span>
          {run.error_message ? <span>{run.error_message}</span> : null}
        </p>
      ) : null}

      <IngestionJobList jobs={jobs} onRetry={onRetry} />
    </section>
  )
}

function IngestionJobList({
  jobs,
  onRetry,
}: {
  jobs: IngestionJob[]
  onRetry(job: IngestionJob): void
}) {
  if (jobs.length === 0) {
    return <p className="empty-copy">No ingestion jobs loaded.</p>
  }

  return (
    <ul className="authoring-list" aria-label="Ingestion jobs">
      {jobs.map((job) => (
        <li key={job.id}>
          <div className="authoring-row authoring-row-static">
            <span>
              <strong className={jobStatusClassName(job.status)}>
                {job.status}
              </strong>
              <small>{job.id}</small>
              <small>{formatAttempts(job)}</small>
              <small>{formatRunAfter(job)}</small>
              <small>{formatLockState(job)}</small>
              {job.last_error ? (
                <small className="job-error">{job.last_error}</small>
              ) : null}
            </span>
            <div className="authoring-row-actions">
              <em>{job.job_type}</em>
              {isRetryableIngestionJob(job) ? (
                <button
                  aria-label={`Retry ingestion job ${job.id}`}
                  className="secondary-button compact-button"
                  onClick={() => onRetry(job)}
                  type="button"
                >
                  Retry
                </button>
              ) : null}
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ObservabilityPanel({
  activeSubmodule,
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
  activeSubmodule: ObservabilitySubmodule
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
          <h2 id="observability-title">
            {observabilitySubmoduleLabel(activeSubmodule)}
          </h2>
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

      <ObservabilityContent activeSubmodule={activeSubmodule} summary={summary} />
    </section>
  )
}

function ObservabilityContent({
  activeSubmodule,
  summary,
}: {
  activeSubmodule: ObservabilitySubmodule
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

  if (activeSubmodule === 'costs') {
    return <ObservabilityCostsContent summary={summary} />
  }
  if (activeSubmodule === 'errors') {
    return <ObservabilityErrorsContent summary={summary} />
  }
  if (activeSubmodule === 'latency') {
    return <ObservabilityLatencyContent summary={summary} />
  }

  return <ObservabilitySummaryContent summary={summary} />
}

function ObservabilitySummaryContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <>
      <ObservabilitySummaryMetrics summary={summary} />
      <ObservabilityBreakdowns summary={summary} />
    </>
  )
}

function ObservabilitySummaryMetrics({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
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
    </>
  )
}

function ObservabilityCostsContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <>
      <div className="metric-grid" aria-label="Cost observability metrics">
        <MetricCard
          label="Provider calls"
          value={String(summary.provider_usage.total_records)}
          detail={`${summary.provider_usage.groups.length} provider groups`}
        />
        <MetricCard
          label="Estimated cost"
          value={formatUsd(summary.provider_usage.total_estimated_cost_usd)}
          detail="Known usage only"
        />
        <MetricCard
          label="Missing costs"
          value={String(summary.provider_usage.missing_cost_count)}
          detail="Usage records without cost"
        />
      </div>
      <div className="observability-breakdowns">
        <ProviderUsageTable summary={summary} />
      </div>
    </>
  )
}

function ObservabilityErrorsContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  const errorCount =
    summary.errors.session_error_count + summary.errors.provider_error_count

  return (
    <>
      <div className="metric-grid" aria-label="Error observability metrics">
        <MetricCard
          label="Errors"
          value={String(errorCount)}
          detail={`${summary.errors.session_error_count} sessions / ${summary.errors.provider_error_count} providers`}
        />
        <MetricCard
          label="Failed sessions"
          value={String(summary.sessions.by_status.failed ?? 0)}
          detail={`${summary.sessions.total} sessions in filter`}
        />
        <MetricCard
          label="Top messages"
          value={String(summary.errors.top_messages.length)}
          detail="Grouped error messages"
        />
      </div>
      <div className="observability-breakdowns">
        <StatusBreakdown summary={summary} />
        <ErrorMessages summary={summary} />
        <SessionHealth summary={summary} />
      </div>
    </>
  )
}

function ObservabilityLatencyContent({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  const slowestP95 = getSlowestP95Group(summary.provider_usage.groups)

  return (
    <>
      <div className="metric-grid" aria-label="Latency observability metrics">
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
        <MetricCard
          label="Provider groups"
          value={String(summary.provider_usage.groups.length)}
          detail="Latency rollups"
        />
        <MetricCard
          label="Provider calls"
          value={String(summary.provider_usage.total_records)}
          detail="Usage records with timing"
        />
      </div>
      <div className="observability-breakdowns">
        <ProviderLatencyTable summary={summary} />
      </div>
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

function ProviderLatencyTable({
  summary,
}: {
  summary: ChatObservabilitySummary
}) {
  return (
    <section
      className="breakdown-card breakdown-card-wide"
      aria-labelledby="provider-latency-title"
    >
      <BreakdownHeader
        id="provider-latency-title"
        label={`${summary.provider_usage.groups.length} groups`}
        title="Provider latency"
      />
      {summary.provider_usage.groups.length === 0 ? (
        <p className="empty-copy">No provider latency groups yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="observability-table">
            <thead>
              <tr>
                <th scope="col">Operation</th>
                <th scope="col">Provider</th>
                <th scope="col">Model</th>
                <th scope="col">Calls</th>
                <th scope="col">Avg</th>
                <th scope="col">P50</th>
                <th scope="col">P95</th>
                <th scope="col">Max</th>
              </tr>
            </thead>
            <tbody>
              {summary.provider_usage.groups.map((group) => (
                <tr key={`${group.operation}-${group.provider}-${group.model}`}>
                  <td>{group.operation}</td>
                  <td>{group.provider}</td>
                  <td>{group.model}</td>
                  <td>{formatNumber(group.record_count)}</td>
                  <td>{formatNullableMs(group.latency_ms.avg)}</td>
                  <td>{formatNullableMs(group.latency_ms.p50)}</td>
                  <td>{formatNullableMs(group.latency_ms.p95)}</td>
                  <td>{formatNullableMs(group.latency_ms.max)}</td>
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
    <section className="speech-input" aria-label="Transcript input">
      <button
        aria-label={buttonLabel}
        className={
          isListening
            ? 'composer-icon-button speech-button speech-button-active'
            : 'composer-icon-button speech-button'
        }
        disabled={!isSupported}
        onClick={isListening ? onStop : onStart}
        title="Transcript"
        type="button"
      >
        <TranscriptIcon active={isListening} />
      </button>
      <p
        className={
          state === 'failed'
            ? 'form-feedback form-feedback-error'
            : 'speech-feedback'
        }
        role={state === 'failed' ? 'alert' : 'status'}
      >
        {message}
      </p>
    </section>
  )
}

function ResponsePanel({
  onOpenSource,
  response,
  state,
}: {
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  response: ChatResponseBody | null
  state: RequestState
}) {
  if (state === 'loading') {
    if (response !== null) {
      return (
        <ResponseContent
          onOpenSource={onOpenSource}
          response={response}
          state={state}
        />
      )
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
    <ResponseContent
      onOpenSource={onOpenSource}
      response={response}
      state={state}
    />
  )
}

function ResponseContent({
  onOpenSource,
  response,
  state,
}: {
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  response: ChatResponseBody
  state: RequestState
}) {
  const isStreaming = state === 'loading'

  return (
    <div className="response-stack" aria-label="Chat response">
      {isStreaming ? (
        <div className="streaming-status" aria-live="polite">
          <span>Streaming answer</span>
          <strong>Retrieval in progress</strong>
        </div>
      ) : null}

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
        {isStreaming && response.citations.length === 0 ? (
          <p className="empty-copy">Citations appear after the final response.</p>
        ) : response.citations.length === 0 ? (
          <p className="empty-copy">No citations returned.</p>
        ) : (
          <ol className="citation-list">
            {response.citations.map((result) => (
              <li key={result.chunk_id}>
                <div>
                  <strong>{result.citation.source_external_id}</strong>
                  <p>{result.citation.snippet}</p>
                  <div className="citation-meta">
                    <span>{result.citation.source_type} source</span>
                    <span>version {result.citation.document_version_number}</span>
                    <span>
                      chars {result.citation.char_start}-{result.citation.char_end}
                    </span>
                  </div>
                </div>
                <div className="citation-actions">
                  <span className="citation-score">
                    score {formatScore(result.score)}
                  </span>
                  <button
                    aria-label={`View source ${result.citation.source_external_id}`}
                    className="source-viewer-button"
                    onClick={() =>
                      onOpenSource(result.citation.source_id, result.citation.snippet)
                    }
                    type="button"
                  >
                    View source
                  </button>
                </div>
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

function SourceViewerPanel({ viewer }: { viewer: SourceViewerState }) {
  if (viewer.state === 'idle' && viewer.sourceId === null) {
    return null
  }

  return (
    <section className="source-viewer" aria-label="Source viewer">
      <div className="detail-heading">
        <h3>Source viewer</h3>
        <span>{sourceViewerStatusLabel(viewer.state)}</span>
      </div>

      {viewer.state === 'loading' ? (
        <p className="empty-copy">Loading source {viewer.sourceId}...</p>
      ) : null}

      {viewer.error ? (
        <p className="history-error" role="alert">
          {viewer.error}
        </p>
      ) : null}

      {viewer.citationSnippet === null ? null : (
        <div className="source-viewer-block">
          <h4>Citation snippet</h4>
          <p>{viewer.citationSnippet}</p>
        </div>
      )}

      {viewer.source ? (
        <div className="source-viewer-content">
          <p className="detail-session-id">{viewer.source.external_id}</p>
          <dl className="source-viewer-grid">
            <div>
              <dt>ID</dt>
              <dd>{viewer.source.id}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{viewer.source.source_type}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{viewer.source.created_at}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{viewer.source.updated_at}</dd>
            </div>
          </dl>

          <div className="source-viewer-block">
            <h4>Tags</h4>
            {viewer.source.tags === null || viewer.source.tags.length === 0 ? (
              <p className="empty-copy">No tags stored.</p>
            ) : (
              <ul className="source-tag-list">
                {viewer.source.tags.map((tag) => (
                  <li key={tag}>{tag}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="source-viewer-block">
            <h4>Metadata</h4>
            {viewer.source.extra_metadata === null ||
            Object.keys(viewer.source.extra_metadata).length === 0 ? (
              <p className="empty-copy">No metadata stored.</p>
            ) : (
              <dl className="source-viewer-grid">
                {Object.entries(viewer.source.extra_metadata).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{formatJsonValue(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function SessionNavigationPanel({
  canLoadMore,
  statusFilter,
  error,
  onArchiveSession,
  onLoadMore,
  onRenameSession,
  onSelectSession,
  onStartNewSession,
  onStatusFilterChange,
  onUnarchiveSession,
  selectedSessionId,
  sessions,
  state,
}: {
  canLoadMore: boolean
  statusFilter: SessionNavigationFilter
  error: string | null
  onArchiveSession(sessionId: string): void
  onLoadMore(): void
  onRenameSession(sessionId: string, title: string): void
  onSelectSession(sessionId: string): void
  onStartNewSession(): void
  onStatusFilterChange(filter: SessionNavigationFilter): void
  onUnarchiveSession(sessionId: string): void
  selectedSessionId: string | null
  sessions: ChatSessionSummary[]
  state: RequestState
}) {
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null)
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState('')
  const renameInputRef = useRef<HTMLInputElement | null>(null)
  const isLoading = state === 'loading'

  useEffect(() => {
    if (renamingSessionId !== null) {
      renameInputRef.current?.focus()
      renameInputRef.current?.select()
    }
  }, [renamingSessionId])

  useEffect(() => {
    if (openMenuSessionId === null) {
      return
    }

    const closeMenu = (event: MouseEvent) => {
      if ((event.target as HTMLElement).closest('[data-session-menu-root]')) {
        return
      }
      setOpenMenuSessionId(null)
    }
    document.addEventListener('mousedown', closeMenu)
    return () => document.removeEventListener('mousedown', closeMenu)
  }, [openMenuSessionId])

  return (
    <aside className="panel session-rail" aria-labelledby="history-title">
      <div className="session-rail-heading">
        <h2 id="history-title">Sesiones</h2>
      </div>

      <button
        className="new-session-button"
        onClick={onStartNewSession}
        type="button"
      >
        <PlusIcon />
        nuevo chat
      </button>

      <div className="session-filter-list" aria-label="Session filters">
        {SESSION_FILTERS.map((filter) => (
          <button
            aria-pressed={statusFilter === filter.value}
            className={
              statusFilter === filter.value
                ? 'session-filter session-filter-active'
                : 'session-filter'
            }
            key={filter.value}
            onClick={() => onStatusFilterChange(filter.value)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="history-error" role="status">
          {error}
        </p>
      ) : null}

      <ul className="session-list" aria-label="Project sessions">
        {isLoading && sessions.length === 0 ? (
          <li className="session-empty">
            <span>Cargando...</span>
          </li>
        ) : sessions.length === 0 ? (
          <li>
            <span>{sessionEmptyCopy(statusFilter)}</span>
          </li>
        ) : (
          sessions.map((session) => {
            const title = sessionDisplayTitle(session)
            const isSelected = session.session_id === selectedSessionId
            const isArchived = session.archived_at !== null
            const hasTraining = sessionHasTraining(session)
            const isRenaming = renamingSessionId === session.session_id
            const menuOpen = openMenuSessionId === session.session_id
            return (
              <li key={session.session_id}>
                <div
                  className={
                    isSelected
                      ? 'session-row session-row-selected'
                      : 'session-row'
                  }
                  data-session-menu-root
                >
                  <span
                    aria-hidden={!hasTraining}
                    className={
                      hasTraining
                        ? 'session-training-icon session-training-icon-visible'
                        : 'session-training-icon'
                    }
                    title={hasTraining ? 'Training' : undefined}
                  >
                    {hasTraining ? (
                      <BrainIcon approved={session.has_approved_training} />
                    ) : null}
                  </span>
                  {isRenaming ? (
                    <form
                      className="session-rename-form"
                      onSubmit={(event) => {
                        event.preventDefault()
                        const trimmedTitle = renameDraft.trim()
                        if (trimmedTitle.length === 0) {
                          return
                        }
                        onRenameSession(session.session_id, trimmedTitle)
                        setRenamingSessionId(null)
                        setRenameDraft('')
                      }}
                    >
                      <input
                        aria-label="Nuevo nombre de sesión"
                        className="session-rename-input"
                        maxLength={60}
                        onBlur={() => {
                          setRenamingSessionId(null)
                          setRenameDraft('')
                        }}
                        onChange={(event) => setRenameDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Escape') {
                            setRenamingSessionId(null)
                            setRenameDraft('')
                          }
                        }}
                        ref={renameInputRef}
                        value={renameDraft}
                      />
                    </form>
                  ) : (
                    <button
                      aria-label={`Abrir sesión ${title}`}
                      className="session-button"
                      onClick={() => onSelectSession(session.session_id)}
                      title={title}
                      type="button"
                    >
                      <span className="session-title">{title}</span>
                    </button>
                  )}
                  <span className={menuOpen ? 'session-age session-age-hidden' : 'session-age'}>
                    {formatRelativeSessionAge(session.created_at)}
                  </span>
                  <div className="session-menu" data-session-menu-root>
                    <button
                      aria-label={`Opciones de ${title}`}
                      className="session-menu-button"
                      onClick={() =>
                        setOpenMenuSessionId((current) =>
                          current === session.session_id ? null : session.session_id,
                        )
                      }
                      type="button"
                    >
                      <MoreVerticalIcon />
                    </button>
                    {menuOpen ? (
                      <div className="session-menu-popover">
                        <button
                          onClick={() => {
                            setRenamingSessionId(session.session_id)
                            setRenameDraft(title)
                            setOpenMenuSessionId(null)
                          }}
                          type="button"
                        >
                          renombrar
                        </button>
                        <button
                          onClick={() => {
                            if (isArchived) {
                              onUnarchiveSession(session.session_id)
                            } else {
                              onArchiveSession(session.session_id)
                            }
                            setOpenMenuSessionId(null)
                          }}
                          type="button"
                        >
                          {isArchived ? 'Desarchivar' : 'Archivar'}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </li>
            )
          })
        )}
      </ul>
      {canLoadMore ? (
        <button
          className="session-load-more"
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
        >
          {isLoading ? 'cargando...' : 'ver más'}
        </button>
      ) : null}
    </aside>
  )
}

function WorkspaceInspectorPanel({
  activeTab,
  detail,
  detailError,
  detailState,
  layout,
  onActiveTabChange,
  onClose,
  onNavigateMessage,
  onOpenSource,
  sourceViewer,
}: {
  activeTab: InspectorTab
  detail: ChatSessionDetailResponse | null
  detailError: string | null
  detailState: RequestState
  layout: 'inline' | 'overlay'
  onActiveTabChange(tab: InspectorTab): void
  onClose(): void
  onNavigateMessage(messageId: string): void
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  sourceViewer: SourceViewerState
}) {
  return (
    <aside
      className={`panel workspace-inspector workspace-inspector-${layout}`}
      aria-label="Workspace inspector"
    >
      <div className="inspector-header">
        <div className="inspector-tabs" role="tablist" aria-label="Inspector panels">
          <button
            aria-controls="context-panel"
            aria-selected={activeTab === 'context'}
            className={
              activeTab === 'context'
                ? 'inspector-tab inspector-tab-active'
                : 'inspector-tab'
            }
            id="context-tab"
            onClick={() => onActiveTabChange('context')}
            role="tab"
            type="button"
          >
            Context
          </button>
          <button
            aria-controls="minimap-panel"
            aria-selected={activeTab === 'minimap'}
            className={
              activeTab === 'minimap'
                ? 'inspector-tab inspector-tab-active'
                : 'inspector-tab'
            }
            id="minimap-tab"
            onClick={() => onActiveTabChange('minimap')}
            role="tab"
            type="button"
          >
            Minimap
          </button>
        </div>
        <button
          aria-label="Close right sidebar"
          className="inspector-close-button"
          onClick={onClose}
          title="Close sidebar"
          type="button"
        >
          <XIcon />
        </button>
      </div>

      {activeTab === 'context' ? (
        <div
          aria-labelledby="context-tab"
          className="inspector-panel"
          id="context-panel"
          role="tabpanel"
        >
          <SourceViewerPanel viewer={sourceViewer} />
          <SessionContextPanel detail={detail} />
          <InternalActionStepper detail={detail} />
          <SessionDetailPanel
            detail={detail}
            error={detailError}
            onOpenSource={onOpenSource}
            state={detailState}
          />
        </div>
      ) : (
        <div
          aria-labelledby="minimap-tab"
          className="inspector-panel"
          id="minimap-panel"
          role="tabpanel"
        >
          <ConversationMinimap
            detail={detail}
            onNavigateMessage={onNavigateMessage}
          />
        </div>
      )}
    </aside>
  )
}

function ConversationMinimap({
  detail,
  onNavigateMessage,
}: {
  detail: ChatSessionDetailResponse | null
  onNavigateMessage(messageId: string): void
}) {
  return (
    <nav className="conversation-minimap" aria-label="Conversation minimap">
      <div className="detail-heading">
        <h3>Minimap</h3>
        <span>{detail?.messages.length ?? 0} turns</span>
      </div>

      {detail === null || detail.messages.length === 0 ? (
        <p className="empty-copy">Select a session to navigate messages.</p>
      ) : (
        <ol className="minimap-list">
          {detail.messages.map((message) => (
            <li key={message.message_id}>
              <button
                aria-label={`${message.role}: ${message.content}`}
                onClick={() => onNavigateMessage(message.message_id)}
                type="button"
              >
                <strong>{message.role}</strong>
                <span>{message.content}</span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </nav>
  )
}

function SessionContextPanel({
  detail,
}: {
  detail: ChatSessionDetailResponse | null
}) {
  const firstUsage = detail?.provider_usage[0] ?? null

  return (
    <section className="session-context-panel" aria-label="Session context">
      <div className="detail-heading">
        <h3>Session context</h3>
        <span>{detail?.session.status ?? 'empty'}</span>
      </div>

      {detail === null ? (
        <p className="empty-copy">
          Select a session to inspect model, prompt and usage context.
        </p>
      ) : (
        <div className="session-context-grid">
          <MetricCard
            detail={detail.session.session_id}
            label="Prompt"
            value={`prompt ${detail.session.prompt_version ?? 'unknown'}`}
          />
          <MetricCard
            detail={
              firstUsage === null
                ? 'unknown provider'
                : `${firstUsage.provider} ${firstUsage.operation} ${firstUsage.status}`
            }
            label="Model"
            value={firstUsage?.model ?? 'unknown model'}
          />
          <MetricCard
            detail={`${detail.provider_usage.length} provider records`}
            label="Cost"
            value={formatSessionCost(detail.provider_usage)}
          />
          <MetricCard
            detail="Known usage only"
            label="Tokens"
            value={formatSessionTokens(detail.provider_usage)}
          />
          <MetricCard
            detail="Average known latency"
            label="Latency"
            value={formatSessionLatency(detail.provider_usage)}
          />
        </div>
      )}
    </section>
  )
}

function InternalActionStepper({
  detail,
}: {
  detail: ChatSessionDetailResponse | null
}) {
  return (
    <section className="internal-stepper" aria-label="Internal action stepper">
      <div className="detail-heading">
        <h3>Action stepper</h3>
        <span>{countInternalSteps(detail)} steps</span>
      </div>

      {detail === null || countInternalSteps(detail) === 0 ? (
        <p className="empty-copy">No stored internal actions for this session.</p>
      ) : (
        <ol className="action-step-list">
          {detail.tool_calls.map((call) => (
            <li key={`tool-${call.tool_call_id}`}>
              <span>tool call {call.status}</span>
              <strong>{call.tool_name}</strong>
              <p>{formatJsonValue(call.arguments)}</p>
              <small>{formatUnknownMs(call.latency_ms)}</small>
            </li>
          ))}
          {detail.retrieval_runs.map((run) => (
            <li key={`retrieval-${run.retrieval_run_id}`}>
              <span>retrieval {run.strategy}</span>
              <strong>{run.query}</strong>
              <p>
                top {run.top_k} / {formatUnknownMs(run.latency_ms)}
              </p>
              <ul className="action-substep-list">
                {run.retrieved_chunks.map((chunk) => (
                  <li key={chunk.retrieved_chunk_id}>
                    <strong>rank {chunk.rank}</strong>
                    <small>{formatStepperScores(chunk)}</small>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {detail.provider_usage.map((usage) => (
            <li key={`provider-${usage.provider_usage_id}`}>
              <span>provider usage {usage.status}</span>
              <strong>{usage.model}</strong>
              <p>
                {usage.provider} {usage.operation} /{' '}
                {formatUnknownTokens(usage.total_tokens)} /{' '}
                {formatUnknownCost(usage.estimated_cost_usd)}
              </p>
              <small>{formatUnknownMs(usage.latency_ms)}</small>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function SessionDetailPanel({
  detail,
  error,
  onOpenSource,
  state,
}: {
  detail: ChatSessionDetailResponse | null
  error: string | null
  onOpenSource(sourceId: string, citationSnippet: string | null): void
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
        <ol aria-label="Session messages" className="detail-list">
          {detail.messages.map((message) => (
            <li key={message.message_id}>
              <article
                aria-label={`${message.role} message`}
                className="message-article"
                id={messageElementId(message.message_id)}
                tabIndex={-1}
              >
                <strong>{message.role}</strong>
                <p>{message.content}</p>
              </article>
            </li>
          ))}
        </ol>
      </section>

      <section className="detail-section" aria-labelledby="history-tools-title">
        <h4 id="history-tools-title">Tool calls</h4>
        <CompactStateList
          emptyLabel="No stored tool calls."
          items={detail.tool_calls}
          renderItem={(call) => (
            <ToolCallDetail call={call} key={call.tool_call_id} />
          )}
        />
      </section>

      <section className="detail-section" aria-labelledby="retrieval-runs-title">
        <h4 id="retrieval-runs-title">Retrieval runs</h4>
        <CompactStateList
          emptyLabel="No stored retrieval runs."
          items={detail.retrieval_runs}
          renderItem={(run) => (
            <RetrievalRunDetail
              key={run.retrieval_run_id}
              onOpenSource={onOpenSource}
              run={run}
            />
          )}
        />
      </section>

      <section className="detail-section" aria-labelledby="provider-usage-title">
        <h4 id="provider-usage-title">Provider usage</h4>
        <CompactStateList
          emptyLabel="No provider usage stored."
          items={detail.provider_usage}
          renderItem={(usage) => (
            <ProviderUsageDetail key={usage.provider_usage_id} usage={usage} />
          )}
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

function RetrievalRunDetail({
  onOpenSource,
  run,
}: {
  onOpenSource(sourceId: string, citationSnippet: string | null): void
  run: ChatHistoryRetrievalRun
}) {
  return (
    <li key={run.retrieval_run_id}>
      <strong>{run.query}</strong>
      <div className="retrieval-run-meta">
        <span>{retrievalStrategyLabel(run)}</span>
        <span>top {run.top_k}</span>
        {run.latency_ms === null ? null : <span>latency {run.latency_ms} ms</span>}
      </div>
      <ul className="retrieved-chunk-list">
        {run.retrieved_chunks.map((chunk) => (
          <RetrievedChunkDetail
            chunk={chunk}
            key={chunk.retrieved_chunk_id}
            onOpenSource={onOpenSource}
          />
        ))}
      </ul>
    </li>
  )
}

function RetrievedChunkDetail({
  chunk,
  onOpenSource,
}: {
  chunk: ChatHistoryRetrievedChunk
  onOpenSource(sourceId: string, citationSnippet: string | null): void
}) {
  const scores = [
    formatOptionalScore('dense score', chunk.dense_score),
    formatOptionalScore('lexical score', chunk.lexical_score),
    formatOptionalScore('rrf score', chunk.rrf_score),
    formatOptionalScore('rerank score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  const sourceId = getCitationString(chunk.citation, 'source_id')
  const citationSnippet = getCitationString(chunk.citation, 'snippet')
  const sourceLabel =
    getCitationString(chunk.citation, 'source_external_id') ?? sourceId

  return (
    <li>
      <span>rank {chunk.rank}</span>
      <div>
        <p>{getCitationText(chunk.citation, 'snippet')}</p>
        {scores.length > 0 ? (
          <small className="retrieved-chunk-scores">{scores.join(' / ')}</small>
        ) : null}
        {sourceId !== null ? (
          <button
            aria-label={`View source ${sourceLabel}`}
            className="source-viewer-button retrieved-chunk-source-button"
            onClick={() => onOpenSource(sourceId, citationSnippet)}
            type="button"
          >
            View source
          </button>
        ) : null}
      </div>
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

function sessionEmptyCopy(filter: SessionNavigationFilter): string {
  if (filter === 'training') {
    return 'Sin sesiones con entrenamiento.'
  }
  if (filter === 'archived') {
    return 'Sin sesiones archivadas.'
  }
  return 'Sin sesiones activas.'
}

function formatRelativeSessionAge(iso: string): string {
  const createdAt = new Date(iso).getTime()
  if (!Number.isFinite(createdAt)) {
    return ''
  }
  const diffMs = Math.max(0, Date.now() - createdAt)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < hour) {
    return `${Math.max(1, Math.floor(diffMs / minute))}m`
  }
  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)}hr`
  }
  return `${Math.floor(diffMs / day)}d`
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

function emptyChatResponse(): ChatResponseBody {
  return {
    answer: '',
    citations: [],
    session_id: null,
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
    tool_calls: detail.tool_calls.map((call) =>
      chatToolCallFromHistory(call, detail.retrieval_runs),
    ),
  }
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

  return {
    limit:
      getJsonNumber(call.arguments, 'limit') ??
      getJsonNumber(call.arguments, 'top_k') ??
      matchingRun?.top_k ??
      0,
    name: call.tool_name,
    query:
      getCitationString(call.arguments, 'query') ??
      matchingRun?.query ??
      call.tool_name,
    result_count:
      getJsonNumber(call.result_summary, 'result_count') ??
      matchingRun?.retrieved_chunks.length ??
      0,
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

function normalizeOptionalChatRetrievalLimit(value: string): string {
  if (value.trim().length === 0) {
    return ''
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return ''
  }
  return String(
    Math.min(CHAT_RETRIEVAL_MAX_LIMIT, Math.max(1, Math.trunc(parsed))),
  )
}

function parseOptionalChatRetrievalLimit(value: string): number | null {
  if (value.trim().length === 0) {
    return null
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return null
  }
  return Math.min(CHAT_RETRIEVAL_MAX_LIMIT, Math.max(1, Math.trunc(parsed)))
}

function normalizeChatRetrievalLimit(value: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return DEFAULT_RETRIEVAL_LIMIT
  }
  return Math.min(CHAT_RETRIEVAL_MAX_LIMIT, Math.max(1, Math.trunc(parsed)))
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

function formatScore(score: number): string {
  return score.toFixed(2)
}

function formatOptionalScore(label: string, score: number | null): string | null {
  return score === null ? null : `${label} ${formatScore(score)}`
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

function retrievalStrategyLabel(run: ChatHistoryRetrievalRun): string {
  if (run.strategy === 'dense' && !run.used_rerank) {
    return 'default dense retrieval'
  }
  return run.used_rerank ? `${run.strategy} with rerank` : `${run.strategy} retrieval`
}

function statusClassName(state: RequestState): string {
  return state === 'failed' ? 'status-dot status-dot-error' : 'status-dot'
}

function sourceViewerStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Loading'
  }
  if (state === 'failed') {
    return 'Unavailable'
  }
  if (state === 'succeeded') {
    return 'Loaded'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Idle'
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

function observabilitySubmoduleLabel(submodule: ObservabilitySubmodule): string {
  if (submodule === 'costs') return 'Costs'
  if (submodule === 'errors') return 'Errors'
  if (submodule === 'latency') return 'Latency'
  return 'Summary'
}

function authoringStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Saving'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Saved'
  }
  return 'Ready'
}

function runtimeStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Refreshing'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Saved'
  }
  return 'Ready'
}

function ingestionStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Working'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Updated'
  }
  return 'Ready'
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

function updateConnectionSecret(
  connections: ProviderConnection[],
  connectionId: string,
  secret: ProviderSecretStatus,
): ProviderConnection[] {
  return connections.map((connection) => {
    if (connection.connection_id !== connectionId) {
      return connection
    }
    const nextSecrets = connection.secrets.filter(
      (item) => item.secret_name !== secret.secret_name,
    )
    return {
      ...connection,
      secrets: [...nextSecrets, secret],
    }
  })
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

function connectionsForCapability(
  connections: ProviderConnection[],
  capability: string,
): ProviderConnection[] {
  return connections.filter((connection) =>
    connection.capabilities.includes(capability),
  )
}

function missingSyncedModelMessage({
  connectionId,
  modelOptions,
  target,
}: {
  connectionId: string
  modelOptions: ProviderModelOption[]
  target: string
}): string | null {
  const trimmedConnectionId = connectionId.trim()
  if (trimmedConnectionId.length === 0 || modelOptions.length > 0) {
    return null
  }
  return `Sync models for ${trimmedConnectionId} before saving ${target}.`
}

function providerModelOptions({
  capability,
  configuredModels = [],
  connectionId,
  providerModels,
  selectedModelId,
}: {
  capability: string
  configuredModels?: ProviderModelOption[]
  connectionId: string
  providerModels: ProviderModel[]
  selectedModelId: string
}): ProviderModelOption[] {
  if (connectionId.length === 0) {
    return []
  }
  const options: ProviderModelOption[] = providerModels
    .filter(
      (model) =>
        model.connection_id === connectionId &&
        model.capabilities.includes(capability),
    )
    .map((model) => ({
      connection_id: model.connection_id,
      model_id: model.model_id,
    }))
  for (const model of configuredModels) {
    if (model.connection_id === connectionId) {
      options.push(model)
    }
  }
  if (selectedModelId.trim().length > 0) {
    options.push({
      connection_id: connectionId,
      model_id: selectedModelId.trim(),
    })
  }
  return uniqueProviderModelOptions(options)
}

function uniqueProviderModelOptions(
  options: ProviderModelOption[],
): ProviderModelOption[] {
  const seen = new Set<string>()
  const unique: ProviderModelOption[] = []
  for (const option of options) {
    const key = `${option.connection_id}\u0000${option.model_id}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    unique.push(option)
  }
  return unique
}

function connectionOptionLabel(connection: ProviderConnection): string {
  const label = metadataLabel(connection.metadata)
  if (label === null) {
    return `${connection.connection_id} (${connection.provider}/${connection.connection_type})`
  }
  return `${label} (${connection.provider}/${connection.connection_type})`
}

function metadataLabel(metadata: Record<string, unknown> | null): string | null {
  const label = metadata?.label
  return typeof label === 'string' && label.trim().length > 0
    ? label.trim()
    : null
}

function upsertIngestionJob(
  jobs: IngestionJob[],
  job: IngestionJob,
): IngestionJob[] {
  const nextJobs = jobs.filter((item) => item.id !== job.id)
  return [job, ...nextJobs]
}

function isRetryableIngestionJob(job: IngestionJob): boolean {
  return job.status === 'blocked' || job.status === 'dead_letter'
}

function formatAttempts(job: IngestionJob): string {
  return `attempt ${job.attempts} of ${job.max_attempts}`
}

function formatRunAfter(job: IngestionJob): string {
  return `run after ${job.run_after}`
}

function formatLockState(job: IngestionJob): string {
  if (job.locked_by === null && job.locked_until === null) {
    return 'unlocked'
  }
  if (job.locked_by !== null && job.locked_until !== null) {
    return `locked by ${job.locked_by} until ${job.locked_until}`
  }
  if (job.locked_by !== null) {
    return `locked by ${job.locked_by}`
  }
  return `locked until ${job.locked_until}`
}

function ingestionRunMessage(run: IngestionRunResponse): string {
  if (run.status === 'idle') {
    return 'No ingestion job was processed.'
  }
  if (run.status === 'blocked') {
    return 'The backend blocked the job before indexing completed.'
  }
  if (run.status === 'processed') {
    return run.created_document_version
      ? 'Document version was created.'
      : 'Job completed without a new document version.'
  }
  return 'Run result reported by the backend.'
}

function jobStatusClassName(status: string): string {
  return `job-status job-status-${status.replace(/[^a-z0-9_-]/gi, '-').toLowerCase()}`
}

function countInternalSteps(detail: ChatSessionDetailResponse | null): number {
  if (detail === null) {
    return 0
  }
  return (
    detail.tool_calls.length +
    detail.retrieval_runs.length +
    detail.provider_usage.length
  )
}

function focusMessage(messageId: string): void {
  document.getElementById(messageElementId(messageId))?.focus()
}

function messageElementId(messageId: string): string {
  return `chat-message-${messageId}`
}

function formatStepperScores(chunk: ChatHistoryRetrievedChunk): string {
  const scores = [
    formatOptionalScore('dense score', chunk.dense_score),
    formatOptionalScore('lexical score', chunk.lexical_score),
    formatOptionalScore('rrf score', chunk.rrf_score),
    formatOptionalScore('rerank score', chunk.rerank_score),
  ].filter((score): score is string => score !== null)
  return scores.length > 0 ? scores.join(' / ') : 'unknown score'
}

function formatSessionCost(usages: ChatHistoryProviderUsage[]): string {
  const knownCosts = usages
    .map((usage) => usage.estimated_cost_usd)
    .filter((value): value is number => value !== null)
  if (knownCosts.length === 0) {
    return 'unknown cost'
  }
  return formatUsd(knownCosts.reduce((total, value) => total + value, 0))
}

function formatSessionTokens(usages: ChatHistoryProviderUsage[]): string {
  const knownTokens = usages
    .map((usage) => usage.total_tokens)
    .filter((value): value is number => value !== null)
  if (knownTokens.length === 0) {
    return 'unknown tokens'
  }
  return `${formatNumber(knownTokens.reduce((total, value) => total + value, 0))} tokens`
}

function formatSessionLatency(usages: ChatHistoryProviderUsage[]): string {
  const knownLatencies = usages
    .map((usage) => usage.latency_ms)
    .filter((value): value is number => value !== null)
  if (knownLatencies.length === 0) {
    return 'unknown latency'
  }
  const average =
    knownLatencies.reduce((total, value) => total + value, 0) /
    knownLatencies.length
  return `${Math.round(average)} ms`
}

function formatUnknownCost(value: number | null): string {
  return value === null ? 'unknown cost' : formatUsd(value)
}

function formatUnknownTokens(value: number | null): string {
  return value === null ? 'unknown tokens' : `${formatNumber(value)} tokens`
}

function formatUnknownMs(value: number | null): string {
  return value === null ? 'unknown latency' : `${value} ms`
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

function MenuIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function XIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function MoreVerticalIcon() {
  return (
    <svg aria-hidden="true" className="ui-icon" focusable="false" viewBox="0 0 24 24">
      <path d="M12 5h.01M12 12h.01M12 19h.01" />
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

function BrainIcon({ approved }: { approved: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={approved ? 'ui-icon brain-icon brain-icon-approved' : 'ui-icon brain-icon'}
      focusable="false"
      viewBox="0 0 24 24"
    >
      <path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v.2A3.2 3.2 0 0 0 4 11.2c0 1.2.7 2.3 1.7 2.8A3.8 3.8 0 0 0 9.5 19H11V5.7a3.4 3.4 0 0 0-1.5-1.2Z" />
      <path d="M14.5 4.5A3.5 3.5 0 0 1 18 8v.2a3.2 3.2 0 0 1 2 3c0 1.2-.7 2.3-1.7 2.8a3.8 3.8 0 0 1-3.8 5H13V5.7a3.4 3.4 0 0 1 1.5-1.2Z" />
      <path d="M8 10h3M13 10h3M8.5 14H11M13 14h2.5" />
    </svg>
  )
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

export default App
