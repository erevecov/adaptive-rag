import {
  type CSSProperties,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, LockKeyhole, Menu } from 'lucide-react'

import { WorkspaceNavigation } from '@/components/beautiful-ui'
import { Button, IconButton } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import * as Popover from '@/components/ui/popover'
import { SessionNavigationPanel } from '@/features/history/HistoryInspectorView'
import { type JobsSubmodule } from '@/features/jobs/jobPlatformUi'
import { type RuntimeSubmodule } from '@/features/runtime/runtimeUi'
import {
  type ChatSessionDetailResponse,
  type ChatSessionSummary,
  type Workspace,
} from '@/lib/apiClient'
import { useFocusTrap } from '@/lib/focusTrap'
import { cn } from '@/lib/utils'

const WORKSPACE_NAME_COLLATOR = new Intl.Collator(undefined, {
  sensitivity: 'base',
})

/** Matches shell CSS breakpoint `max-[680px]` (fixed mobile sidebar). */
const SHELL_MOBILE_MAX_WIDTH_PX = 680

function readIsShellMobileViewport(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  return window.innerWidth <= SHELL_MOBILE_MAX_WIDTH_PX
}

function useIsShellMobileViewport(): boolean {
  const [isMobile, setIsMobile] = useState(readIsShellMobileViewport)

  useEffect(() => {
    const onResize = () => setIsMobile(readIsShellMobileViewport())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return isMobile
}

const SETTINGS_NAVIGATION = [
  {
    id: 'authoring',
    label: 'Authoring',
    submodules: [
      { id: 'workspaces', label: 'Workspaces' },
      { id: 'users', label: 'Users' },
      { id: 'knowledge', label: 'Knowledge' },
      { id: 'sources', label: 'Sources' },
      { id: 'retrieval', label: 'Retrieval Playground' },
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
      { id: 'model_catalog', label: 'Model Catalog' },
      { id: 'global_defaults', label: 'Global Defaults' },
      { id: 'workspace_overrides', label: 'Workspace Overrides' },
    ],
  },
  {
    id: 'jobs',
    label: 'Background Jobs',
    submodules: [
      { id: 'jobs', label: 'Jobs' },
      { id: 'schedules', label: 'Schedules' },
      { id: 'queues', label: 'Queues', superadminOnly: true },
      { id: 'workers', label: 'Workers', superadminOnly: true },
    ],
  },
] as const

const AUTHORING_NAVIGATION = SETTINGS_NAVIGATION[0]
const OBSERVABILITY_NAVIGATION = SETTINGS_NAVIGATION[1]
const RUNTIME_NAVIGATION = SETTINGS_NAVIGATION[2]
const JOBS_NAVIGATION = SETTINGS_NAVIGATION[3]

const ACCOUNT_MODULES = [
  { id: 'appearance', label: 'Appearance' },
  { id: 'memory', label: 'Memory' },
] as const

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type PrimaryView = 'chat' | 'account' | 'settings'
export type AccountModule = (typeof ACCOUNT_MODULES)[number]['id']
export type SettingsModule = (typeof SETTINGS_NAVIGATION)[number]['id']
export type AuthoringSubmodule =
  (typeof SETTINGS_NAVIGATION)[0]['submodules'][number]['id']
export type ObservabilitySubmodule =
  (typeof SETTINGS_NAVIGATION)[1]['submodules'][number]['id']
export type SettingsSubmodule =
  | AuthoringSubmodule
  | ObservabilitySubmodule
  | RuntimeSubmodule
  | JobsSubmodule
export type SettingsNavigationSelection =
  | { module: 'authoring'; submodule: AuthoringSubmodule }
  | { module: 'observability'; submodule: ObservabilitySubmodule }
  | { module: 'runtime'; submodule: RuntimeSubmodule }
  | { module: 'jobs'; submodule: JobsSubmodule }
export type SessionNavigationFilter = 'active' | 'training' | 'archived'

export function AppShell({
  children,
  isBackgroundInert = false,
  isLeftSidebarOpen,
  isRightDockOpen,
  primaryView,
  sidebar,
  topline,
}: {
  children: ReactNode
  /** When true (inspector overlay), sidebar + topline leave the a11y tree. */
  isBackgroundInert?: boolean
  isLeftSidebarOpen: boolean
  isRightDockOpen: boolean
  primaryView: PrimaryView
  sidebar: ReactNode
  topline: ReactNode
}) {
  const skipHref = primaryView === 'chat' ? '#chat-composer' : '#main-content'
  const skipLabel =
    primaryView === 'chat' ? 'Skip To Chat Composer' : 'Skip To Main Content'

  return (
    <main
      className={cn(
        // Flex shell (not CSS grid): grid min-height:auto on items let long
        // session transcripts expand the main column past 100vh and scroll the
        // whole page (composer mid-screen + empty void). Flex + min-h-0 pins it.
        [
          'app-shell flex h-full max-h-full min-h-0 overflow-hidden bg-background p-0 text-foreground',
          'motion-safe:transition-[padding] motion-safe:duration-200 motion-safe:ease-out',
          'max-[680px]:flex-col',
        ],
        isLeftSidebarOpen
          ? 'app-shell-sidebar-open'
          : 'app-shell-sidebar-closed',
        isRightDockOpen
          ? 'app-shell-right-dock-open'
          : 'app-shell-right-dock-closed',
      )}
      data-slot="app-shell"
      style={
        {
          // Wide enough for 2-col primary nav + Activos/Train/Archivados without clipping.
          '--left-sidebar-width': isLeftSidebarOpen ? '280px' : '0px',
        } as CSSProperties
      }
    >
      {/* First focusable control for keyboard users (Tab from document start). */}
      <a
        className={cn(
          'sr-only focus-visible:not-sr-only',
          'focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-[100] max-[680px]:focus-visible:left-1.5 max-[680px]:focus-visible:top-1.5',
          'focus-visible:rounded-md focus-visible:bg-primary focus-visible:px-3 focus-visible:py-2 max-[680px]:focus-visible:px-1 max-[680px]:focus-visible:py-0.5 max-[680px]:focus-visible:text-[0.5625rem]',
          'focus-visible:text-sm focus-visible:font-semibold focus-visible:text-primary-foreground',
          // Match primary Button: ring against primary fill (critical on purple).
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        )}
        data-slot="skip-link"
        href={skipHref}
        {...(isBackgroundInert ? { inert: true } : {})}
      >
        {skipLabel}
      </a>

      <div
        className={cn(
          'h-full min-h-0 shrink-0 overflow-hidden',
          'w-[var(--left-sidebar-width)] motion-safe:transition-[width] motion-safe:duration-200 motion-safe:ease-out',
          // Mobile: sidebar is fixed overlay; host takes no flow space.
          'max-[680px]:h-0 max-[680px]:w-0',
        )}
        data-slot="app-shell-sidebar-host"
        {...(isBackgroundInert ? { inert: true } : {})}
      >
        {sidebar}
      </div>

      <section
        aria-labelledby="workspace-title"
        className={cn(
          'workspace flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden',
          primaryView === 'chat'
            ? [
                // Chat: fixed viewport. overflow-hidden ONLY (never overflow-auto)
                // so the transcript is the sole scroller and the composer stays pinned.
                // pr-0: scrollbar sits on the right edge; content pads itself.
                'workspace-chat gap-1 pl-[18px] pr-0 pb-2.5 pt-1.5',
                'max-[900px]:pl-3.5 max-[900px]:py-3',
                'max-[680px]:gap-0 max-[680px]:pl-1 max-[680px]:pb-0 max-[680px]:pt-0.5',
              ]
            : [
                // Full-width column + pr-0 so the body scrollbar is flush right
                // (content inside workspace-body supplies horizontal padding).
                // No reserved top chrome: workspace chip floats when sidebar is closed.
                'overflow-hidden gap-0 pl-0 pr-0 pb-2.5 pt-0 w-full',
                'max-[900px]:pb-3',
                'max-[680px]:pb-0',
              ],
        )}
        data-slot="workspace"
        id="main-content"
        tabIndex={-1}
      >
        <div
          className={cn(
            'min-h-0 shrink-0',
            // Outside chat the topline must not reserve vertical space.
            primaryView !== 'chat' && 'contents',
          )}
          data-slot="workspace-topline-host"
          {...(isBackgroundInert ? { inert: true } : {})}
        >
          {topline}
        </div>
        <div
          className={cn(
            'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden',
            // pr-0: settings/account scrollbar hugs the main column edge.
            primaryView !== 'chat' && 'overflow-y-auto overflow-x-hidden pr-0',
          )}
          data-slot="workspace-body"
        >
          {primaryView === 'chat' ? (
            children
          ) : (
            <div
              className={cn(
                'mx-auto w-full max-w-[1240px] pl-[18px] pr-[18px] pt-0',
                'max-[900px]:pl-3.5 max-[900px]:pr-3.5',
                'max-[680px]:px-1',
                // Clear fixed hamburger when the left rail is collapsed.
                !isLeftSidebarOpen && 'pl-12 max-[680px]:pl-11',
              )}
              data-slot="workspace-body-content"
            >
              {children}
            </div>
          )}
        </div>
      </section>
    </main>
  )
}

export function ChatWorkspaceGrid({
  children,
  isRightDockInline,
}: {
  children: ReactNode
  isRightDockInline: boolean
}) {
  return (
    <div
      className={cn(
        [
          // Flex fill of workspace-body — never size from transcript content.
          'workspace-grid chat-workspace-grid flex h-full min-h-0 min-w-0 flex-1 gap-[18px] overflow-hidden',
          'max-[680px]:min-h-0',
        ],
        isRightDockInline &&
          'chat-workspace-grid-docked max-[900px]:flex-col',
      )}
      data-slot="chat-workspace-grid"
    >
      {children}
    </div>
  )
}

export function WorkspaceTopline({
  isChatWorkspace = false,
  isLeftSidebarOpen = true,
  workspaceId,
  workspaces,
  selectedSessionId,
  sessionDetail,
  sessions,
}: {
  isChatWorkspace?: boolean
  isLeftSidebarOpen?: boolean
  workspaceId: string
  workspaces: Workspace[]
  selectedSessionId: string | null
  sessionDetail: ChatSessionDetailResponse | null
  sessions: ChatSessionSummary[]
}) {
  const workspaceName = getWorkspaceName(workspaceId, workspaces)
  const sessionName = getWorkspaceSessionName({
    selectedSessionId,
    sessionDetail,
    sessions,
  })

  // Outside chat: no session title and no layout strip. Workspace chip only when
  // the left rail is collapsed (workspace selector is already in the open sidebar).
  if (!isChatWorkspace) {
    if (isLeftSidebarOpen) {
      return (
        <h1 className="sr-only" id="workspace-title">
          Workspace
        </h1>
      )
    }

    return (
      <>
        <h1 className="sr-only" id="workspace-title">
          Workspace
        </h1>
        <span
          aria-label={`Workspace ${workspaceName}`}
          className={cn(
            // Float over content — zero flow height. Sit near the menu, slightly left of the far edge.
            'workspace-topline workspace-chip pointer-events-auto fixed right-14 top-1.5 z-40',
            'max-w-[min(34vw,12rem)] overflow-hidden text-ellipsis whitespace-nowrap',
            'rounded-md border border-border bg-background px-1.5 py-0.5 text-[11px] font-bold leading-[1.2]',
            'text-muted-foreground',
            'max-[680px]:right-11 max-[680px]:top-0.5 max-[680px]:border-primary/95 max-[680px]:px-0.5 max-[680px]:text-[0.5625rem]',
          )}
          data-slot="workspace-chip"
          title={workspaceName}
        >
          {workspaceName}
        </span>
      </>
    )
  }

  return (
    <header
      aria-label={`Current session ${sessionName}, workspace ${workspaceName}`}
      className={cn(
        [
          'workspace-topline mb-0 flex min-h-5 min-w-0 items-center gap-1.5 pr-[18px] text-foreground tracking-tight',
          'max-[900px]:pr-3.5 max-[680px]:min-h-11 max-[680px]:gap-0.5 max-[680px]:pr-1',
        ],
        !isLeftSidebarOpen && 'pl-12 max-[680px]:pl-14',
      )}
      data-slot="workspace-topline"
    >
      <h1
        className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-[13px] font-extrabold leading-[1.2] tracking-tight text-foreground max-[680px]:text-[0.5625rem]"
        id="workspace-title"
        title={sessionName}
      >
        {sessionName}
      </h1>
      <span
        className="workspace-chip min-w-0 max-w-[min(34vw,12rem)] shrink overflow-hidden text-ellipsis whitespace-nowrap rounded-md border border-border bg-muted/15 px-1.5 py-0.5 text-[11px] font-bold leading-[1.2] text-muted-foreground max-[680px]:border-primary/95 max-[680px]:bg-card max-[680px]:px-0.5 max-[680px]:text-[0.5625rem]"
        data-slot="workspace-chip"
        title={workspaceName}
      >
        {workspaceName}
      </span>
    </header>
  )
}

export function AppSidebar({
  accountModule,
  authoringSubmodule,
  canLoadMoreSessions,
  error,
  isOpen,
  jobsSubmodule,
  canManageJobPlatform,
  observabilitySubmodule,
  onArchiveSession,
  onAccountModuleChange,
  onDeleteSession,
  onLoadMoreSessions,
  onPrimaryViewChange,
  onWorkspaceIdChange,
  onRenameSession,
  onSelectSession,
  onSettingsModuleChange,
  onSettingsSubmoduleChange,
  onStartNewSession,
  onStatusFilterChange,
  onToggle,
  onUnarchiveSession,
  primaryView,
  workspaceId,
  workspaceState,
  workspaces,
  runtimeSubmodule,
  selectedSessionId,
  sessions,
  sessionState,
  settingsModule,
  statusFilter,
}: {
  accountModule: AccountModule
  authoringSubmodule: AuthoringSubmodule
  canManageJobPlatform: boolean
  canLoadMoreSessions: boolean
  error: string | null
  isOpen: boolean
  jobsSubmodule: JobsSubmodule
  observabilitySubmodule: ObservabilitySubmodule
  onArchiveSession(sessionId: string): void
  onAccountModuleChange(module: AccountModule): void
  onDeleteSession(sessionId: string): void
  onLoadMoreSessions(): void
  onPrimaryViewChange(view: PrimaryView): void
  onWorkspaceIdChange(workspaceId: string): void
  onRenameSession(sessionId: string, title: string): void
  onSelectSession(sessionId: string): void
  onSettingsModuleChange(module: SettingsModule): void
  onSettingsSubmoduleChange(selection: SettingsNavigationSelection): void
  onStartNewSession(): void
  onStatusFilterChange(filter: SessionNavigationFilter): void
  onToggle(): void
  onUnarchiveSession(sessionId: string): void
  primaryView: PrimaryView
  workspaceId: string
  workspaceState: RequestState
  workspaces: Workspace[]
  runtimeSubmodule: RuntimeSubmodule
  selectedSessionId: string | null
  sessions: ChatSessionSummary[]
  sessionState: RequestState
  settingsModule: SettingsModule
  statusFilter: SessionNavigationFilter
}) {
  const isMobileShell = useIsShellMobileViewport()
  const sidebarRef = useRef<HTMLElement>(null)
  const trapMobileSidebar = isOpen && isMobileShell
  useFocusTrap(sidebarRef, trapMobileSidebar)

  useEffect(() => {
    if (!trapMobileSidebar) {
      return
    }
    const main = document.getElementById('main-content')
    if (main === null) {
      return
    }
    const hadInert = main.hasAttribute('inert')
    main.setAttribute('inert', '')
    return () => {
      if (!hadInert) {
        main.removeAttribute('inert')
      }
    }
  }, [trapMobileSidebar])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || event.defaultPrevented) {
        return
      }
      // Inspector overlay owns Escape while aria-modal dialog is open.
      if (document.querySelector('[role="dialog"][aria-modal="true"]')) {
        return
      }
      // Don't steal Escape from open menus/dialogs (e.g. workspace selector).
      const target = event.target
      if (
        target instanceof HTMLElement &&
        target.closest(
          '[data-state="open"][role="menu"], [data-state="open"][role="listbox"], [role="dialog"][data-state="open"]',
        )
      ) {
        return
      }
      event.preventDefault()
      onToggle()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onToggle])

  return (
    <aside
      aria-label="Primary Sidebar"
      className={cn(
        [
          'relative z-40 grid h-full min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden',
          // Solid card (not /90) keeps the rail opaque on purple/dark backgrounds.
          'border-r border-border bg-card shadow-[1px_0_0_0] shadow-primary/15 motion-safe:transition-[background,border-color,box-shadow,opacity,width] motion-safe:duration-200',
          'max-[680px]:fixed max-[680px]:left-0 max-[680px]:top-0 max-[680px]:h-svh',
        ],
        isOpen
          ? 'w-[280px] max-[680px]:w-[min(86vw,280px)] max-[680px]:shadow-[var(--shadow-mobile-sidebar)]'
          : 'w-0 overflow-visible border-r-transparent bg-transparent pointer-events-none max-[680px]:shadow-none',
      )}
      data-slot="app-sidebar"
      data-state={isOpen ? 'open' : 'closed'}
      ref={sidebarRef}
    >
      {isOpen && isMobileShell && typeof document !== 'undefined'
        ? createPortal(
            <Button
              aria-label="Close Left Sidebar"
              // z-30 sits below fixed mobile sidebar (z-40); matches inspector overlay-backdrop language.
              // tabIndex=-1: clickable scrim stays out of sequential keyboard focus.
              className="fixed inset-0 z-30 h-auto cursor-pointer rounded-none border-0 bg-[var(--overlay-backdrop)] p-0 text-transparent hover:bg-[var(--overlay-backdrop)]"
              data-testid="sidebar-backdrop"
              onClick={onToggle}
              slotName="sidebar-backdrop"
              tabIndex={-1}
              type="button"
              variant="ghost"
            />,
            document.body,
          )
        : null}
      <div
        className={cn(
'grid min-h-14 grid-cols-[36px_minmax(0,1fr)] items-center gap-2.5 border-b border-border px-3 py-2.5 shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:shadow-primary/95 max-[680px]:min-h-11 max-[680px]:gap-0.5 max-[680px]:px-0.5 max-[680px]:py-0.5',
          !isOpen && 'min-h-0 border-b-transparent p-0 shadow-none',
        )}
        data-slot="app-sidebar-chrome"
      >
        <IconButton
          aria-expanded={isOpen}
          className={cn(
            'border-border bg-card text-foreground hover:border-primary hover:bg-primary/15 max-[680px]:hover:bg-primary/65 hover:text-foreground active:bg-primary/20 max-[680px]:active:bg-primary/95',
            !isOpen &&
              // z-50 stays under inspector backdrop (z-60) so Menu cannot pierce the modal scrim.
              'pointer-events-auto fixed left-3.5 top-3.5 z-50 bg-card shadow-[var(--shadow-sidebar-toggle)] max-[680px]:left-0.5 max-[680px]:top-0.5 max-[680px]:border max-[680px]:border-primary/95',
          )}
          label={isOpen ? 'Collapse Left Sidebar' : 'Open Left Sidebar'}
          onClick={onToggle}
        >
          <Menu aria-hidden="true" className="size-5" />
        </IconButton>
        <div
          className={cn(
            'grid min-w-0 gap-0.5 motion-safe:transition-[opacity,transform] motion-safe:duration-150',
            !isOpen && 'pointer-events-none -translate-x-2.5 opacity-0',
          )}
          aria-hidden={!isOpen}
          data-slot="sidebar-brand"
        >
          <strong className="truncate text-sm font-extrabold leading-tight tracking-tight text-foreground max-[680px]:text-[0.5625rem]">
            Adaptive RAG
          </strong>
          <span className="truncate text-[11px] font-medium leading-tight tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem]">
            Workspace
          </span>
        </div>
      </div>

      <div
        className={cn(
          // overflow-hidden: only the session list (or contextual nav) scrolls —
          // not workspace selector / primary nav — so the thumb starts at row 1.
          // pr-0: session list scrollbar flush to the rail edge.
          'grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-2.5 overflow-hidden pl-2.5 pr-0 pb-3 pt-2.5 motion-safe:transition-[opacity,transform] motion-safe:duration-150 max-[680px]:gap-0.5 max-[680px]:pl-1 max-[680px]:pb-1 max-[680px]:pt-0.5',
          !isOpen && 'pointer-events-none -translate-x-2.5 opacity-0',
        )}
        data-slot="app-sidebar-content"
        {...(!isOpen ? { inert: true } : {})}
      >
        <div className="grid shrink-0 gap-2.5 pr-2.5 max-[680px]:gap-0.5 max-[680px]:pr-1">
        <SidebarWorkspaceSelector
          onWorkspaceIdChange={onWorkspaceIdChange}
          workspaceId={workspaceId}
          workspaces={workspaces}
          state={workspaceState}
        />

        <div
          className={cn(
            'min-w-0 border-b border-border pb-2.5 shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:pb-0.5 max-[680px]:shadow-primary/95',
            '[&_[data-slot=workspace-navigation]]:gap-0 [&_[data-slot=nav-section]]:gap-0',
            '[&_[data-slot=nav-section-content]]:!grid [&_[data-slot=nav-section-content]]:grid-cols-2',
            '[&_[data-slot=nav-section-content]]:gap-1 max-[680px]:[&_[data-slot=nav-section-content]]:gap-0.5',
            '[&_[data-slot=sidebar-item]]:h-auto [&_[data-slot=sidebar-item]]:min-h-8 [&_[data-slot=sidebar-item]]:justify-center',
            '[&_[data-slot=sidebar-item]]:overflow-hidden [&_[data-slot=sidebar-item]]:whitespace-nowrap [&_[data-slot=sidebar-item]]:px-2',
            '[&_[data-slot=sidebar-item]]:text-center [&_[data-slot=sidebar-item]]:text-xs [&_[data-slot=sidebar-item]]:leading-tight',
            '[&_[data-slot=sidebar-item]:last-child]:col-span-2 max-[680px]:[&_[data-slot=sidebar-item]]:min-h-11',
            'max-[680px]:[&_[data-slot=sidebar-item]]:px-0.5 max-[680px]:[&_[data-slot=sidebar-item]]:text-[0.5625rem]',
            'max-[680px]:[&_[data-slot=sidebar-item]]:hover:bg-primary/65 max-[680px]:[&_[data-slot=sidebar-item][data-active]]:bg-primary/45',
          )}
        >
          <WorkspaceNavigation
            label="Primary Navigation"
            onNavigate={(id) => {
              if (id === 'chat' || id === 'account' || id === 'settings') {
                onPrimaryViewChange(id)
              }
            }}
            sections={[
              {
                id: 'primary',
                items: [
                  { active: primaryView === 'chat', id: 'chat', label: 'Chat' },
                  {
                    active: primaryView === 'account',
                    id: 'account',
                    label: 'My Account',
                  },
                  {
                    active: primaryView === 'settings',
                    id: 'settings',
                    label: 'Settings',
                  },
                ],
                label: '',
              },
            ]}
          />
        </div>
        </div>

        {primaryView === 'chat' ? (
          <SessionNavigationPanel
            canLoadMore={canLoadMoreSessions}
            error={error}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
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
            activeJobsSubmodule={jobsSubmodule}
            canManageJobPlatform={canManageJobPlatform}
            onModuleChange={onSettingsModuleChange}
            onSubmoduleChange={onSettingsSubmoduleChange}
          />
        )}
      </div>
    </aside>
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
    <nav
      aria-label="My Account Navigation"
      className="scrollbar-chat grid min-h-0 content-start items-stretch self-stretch overflow-y-auto overflow-x-hidden border-t border-border pr-2.5 pt-[18px] shadow-[0_-1px_0_0] shadow-primary/15 max-[680px]:pr-1 max-[680px]:shadow-primary/65 max-[680px]:pt-1"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight tracking-tight text-foreground uppercase max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider"
        data-slot="sidebar-contextual-title"
      >
        My Account
      </h2>
      <div className="mt-2.5 grid gap-1 max-[680px]:mt-1 max-[680px]:gap-0.5" data-slot="sidebar-contextual-group">
        {ACCOUNT_MODULES.map((module) => {
          const active = module.id === activeModule
          return (
            <SidebarContextualButton
              active={active}
              key={module.id}
              onClick={() => onModuleChange(module.id)}
              slot="sidebar-contextual-item"
            >
              {module.label}
            </SidebarContextualButton>
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
  activeJobsSubmodule,
  canManageJobPlatform,
  onModuleChange,
  onSubmoduleChange,
}: {
  activeAuthoringSubmodule: AuthoringSubmodule
  activeModule: SettingsModule
  activeObservabilitySubmodule: ObservabilitySubmodule
  activeRuntimeSubmodule: RuntimeSubmodule
  activeJobsSubmodule: JobsSubmodule
  canManageJobPlatform: boolean
  onModuleChange(module: SettingsModule): void
  onSubmoduleChange(selection: SettingsNavigationSelection): void
}) {
  const activeSubmodule = getActiveSettingsSubmodule(
    activeModule,
    activeAuthoringSubmodule,
    activeObservabilitySubmodule,
    activeRuntimeSubmodule,
    activeJobsSubmodule,
  )
  const renderSubmoduleButton = (
    selection: SettingsNavigationSelection,
    label: string,
  ) => {
    const submoduleActive = selection.submodule === activeSubmodule
    return (
      <SidebarContextualButton
        active={submoduleActive}
        key={selection.submodule}
        onClick={() => onSubmoduleChange(selection)}
        slot="sidebar-contextual-subitem"
        subitem
      >
        {label}
      </SidebarContextualButton>
    )
  }

  return (
    <nav
      aria-label="Settings Navigation"
      className="scrollbar-chat grid min-h-0 content-start items-stretch self-stretch overflow-y-auto overflow-x-hidden border-t border-border pr-2.5 pt-[18px] shadow-[0_-1px_0_0] shadow-primary/15 max-[680px]:pr-1 max-[680px]:shadow-primary/65 max-[680px]:pt-1"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight tracking-tight text-foreground uppercase max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider"
        data-slot="sidebar-contextual-title"
      >
        Settings
      </h2>
      <div className="mt-2.5 grid gap-1 max-[680px]:mt-1 max-[680px]:gap-0.5" data-slot="sidebar-contextual-group">
        <SidebarContextualButton
          active={activeModule === AUTHORING_NAVIGATION.id}
          onClick={() => onModuleChange(AUTHORING_NAVIGATION.id)}
          slot="sidebar-contextual-item"
        >
          {AUTHORING_NAVIGATION.label}
        </SidebarContextualButton>

        {activeModule === AUTHORING_NAVIGATION.id
          ? AUTHORING_NAVIGATION.submodules.map((submodule) =>
              renderSubmoduleButton(
                { module: AUTHORING_NAVIGATION.id, submodule: submodule.id },
                submodule.label,
              ),
            )
          : null}
      </div>
      <div className="mt-2.5 grid gap-1 max-[680px]:gap-0.5 max-[680px]:mt-1" data-slot="sidebar-contextual-group">
        <SidebarContextualButton
          active={activeModule === OBSERVABILITY_NAVIGATION.id}
          onClick={() => onModuleChange(OBSERVABILITY_NAVIGATION.id)}
          slot="sidebar-contextual-item"
        >
          {OBSERVABILITY_NAVIGATION.label}
        </SidebarContextualButton>

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
      <div className="mt-2.5 grid gap-1 max-[680px]:gap-0.5 max-[680px]:mt-1" data-slot="sidebar-contextual-group">
        <SidebarContextualButton
          active={activeModule === JOBS_NAVIGATION.id}
          onClick={() => onModuleChange(JOBS_NAVIGATION.id)}
          slot="sidebar-contextual-item"
        >
          {JOBS_NAVIGATION.label}
        </SidebarContextualButton>

        {activeModule === JOBS_NAVIGATION.id
          ? JOBS_NAVIGATION.submodules
              .filter(
                (submodule) =>
                  !("superadminOnly" in submodule) || canManageJobPlatform,
              )
              .map((submodule) =>
                renderSubmoduleButton(
                  { module: JOBS_NAVIGATION.id, submodule: submodule.id },
                  submodule.label,
                ),
              )
          : null}
      </div>
      <div className="mt-2.5 grid gap-1 max-[680px]:gap-0.5 max-[680px]:mt-1" data-slot="sidebar-contextual-group">
        <SidebarContextualButton
          active={activeModule === RUNTIME_NAVIGATION.id}
          onClick={() => onModuleChange(RUNTIME_NAVIGATION.id)}
          slot="sidebar-contextual-item"
        >
          {RUNTIME_NAVIGATION.label}
        </SidebarContextualButton>

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

function SidebarContextualButton({
  active,
  children,
  onClick,
  slot,
  subitem = false,
}: {
  active: boolean
  children: ReactNode
  onClick(): void
  slot: 'sidebar-contextual-item' | 'sidebar-contextual-subitem'
  subitem?: boolean
}) {
  return (
    <Button
      aria-pressed={active}
      className={cn(
        [
          'h-auto w-full cursor-pointer justify-start border border-transparent bg-transparent text-left text-muted-foreground',
          'hover:border-border',
          'disabled:cursor-not-allowed disabled:opacity-55',
        ],
        subitem
          ? [
              'relative ml-3 min-h-[30px] max-[680px]:min-h-11 w-[calc(100%-0.75rem)] rounded-md px-[18px] text-xs tracking-tight max-[680px]:px-0.5 max-[680px]:text-[0.5625rem]',
              'before:absolute before:bottom-[-4px] before:left-[-5px] before:top-[-4px] before:w-px before:rounded-full before:bg-border',
              active && 'before:hidden',
            ]
          : 'min-h-9 max-[680px]:min-h-11 rounded-md px-2.5 text-sm tracking-tight max-[680px]:px-0.5 max-[680px]:text-[0.5625rem]',
        active && 'border-primary/40 bg-primary/15 text-foreground',
      )}
      data-active={active ? '' : undefined}
      onClick={onClick}
      slotName={slot}
      type="button"
      variant="ghost"
    >
      {children}
    </Button>
  )
}

function getActiveSettingsSubmodule(
  activeModule: SettingsModule,
  activeAuthoringSubmodule: AuthoringSubmodule,
  activeObservabilitySubmodule: ObservabilitySubmodule,
  activeRuntimeSubmodule: RuntimeSubmodule,
  activeJobsSubmodule: JobsSubmodule,
): SettingsSubmodule {
  if (activeModule === 'authoring') {
    return activeAuthoringSubmodule
  }
  if (activeModule === 'observability') {
    return activeObservabilitySubmodule
  }
  if (activeModule === 'runtime') {
    return activeRuntimeSubmodule
  }
  return activeJobsSubmodule
}

function SidebarWorkspaceSelector({
  onWorkspaceIdChange,
  workspaceId,
  workspaces,
  state,
}: {
  onWorkspaceIdChange(workspaceId: string): void
  workspaceId: string
  workspaces: Workspace[]
  state: RequestState
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [workspaceSearch, setWorkspaceSearch] = useState('')
  const trimmedWorkspaceId = workspaceId.trim()
  const selectedWorkspace = workspaces.find((workspace) => workspace.id === trimmedWorkspaceId)
  const selectedLabel =
    selectedWorkspace?.name ??
    (trimmedWorkspaceId.length > 0 ? 'Workspace Selected' : 'Select Workspace')
  const visibleWorkspaces = useMemo(
    () => getVisibleWorkspaceOptions(workspaces, workspaceSearch),
    [workspaceSearch, workspaces],
  )

  function handleSelectWorkspace(nextWorkspaceId: string) {
    onWorkspaceIdChange(nextWorkspaceId)
    setIsOpen(false)
    setWorkspaceSearch('')
  }

  return (
    <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
      <div className="relative z-[90] min-w-0" data-slot="workspace-selector">
        <Popover.Trigger asChild>
          <Button
            aria-label={`Workspace selector: ${selectedLabel}`}
            className={cn(
              [
                'grid h-auto min-h-12 w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center justify-stretch gap-2 max-[680px]:gap-0.5',
                'rounded-lg border border-border bg-card px-2.5 py-2 text-left text-foreground motion-safe:transition-colors max-[680px]:rounded-md max-[680px]:border-primary/95 max-[680px]:px-0.5 max-[680px]:py-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95',
                'hover:border-primary',
              ],
              isOpen && 'border-primary bg-primary/15',
            )}
            slotName="workspace-selector-trigger"
            type="button"
            variant="ghost"
          >
            <span className="grid min-w-0 gap-0.5">
              <small className="text-[10px] font-extrabold uppercase tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
                Workspace
              </small>
              <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm font-extrabold text-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug">
                {selectedLabel}
              </strong>
            </span>
            <ChevronDown aria-hidden="true" className="size-5" />
          </Button>
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Content
            align="start"
            className="z-[120] grid w-[var(--radix-popover-trigger-width)] gap-2 rounded-lg border border-border bg-popover p-2 text-popover-foreground shadow-[var(--shadow-popover)] max-[680px]:gap-0.5 max-[680px]:rounded-md max-[680px]:border-primary/95 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95"
            data-slot="workspace-selector-popover"
            onCloseAutoFocus={(event) => event.preventDefault()}
            side="bottom"
            sideOffset={6}
          >
            <label className="grid gap-1.5 max-[680px]:gap-0.5" data-slot="workspace-selector-search">
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
                Search Workspaces
              </span>
              <Input
                aria-label="Search Workspaces"
                autoComplete="off"
                autoFocus
                className="h-[34px] text-xs max-[680px]:min-h-11 max-[680px]:text-base max-[680px]:leading-snug"
                name="workspace-search"
                onChange={(event) => setWorkspaceSearch(event.currentTarget.value)}
                placeholder="Search Workspaces"
                type="search"
                value={workspaceSearch}
              />
            </label>

            <div
              className="flex items-center justify-between gap-2 max-[680px]:gap-0.5"
              data-slot="workspace-selector-popover-header"
            >
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground">
                {state === 'loading' ? 'Loading Workspaces…' : 'All Workspaces'}
              </span>
            </div>

            <div
              aria-label="Workspaces"
              className="grid max-h-72 gap-1 overflow-auto max-[680px]:gap-0.5"
              data-slot="workspace-selector-list"
              role="listbox"
            >
              {visibleWorkspaces.length > 0 ? (
                visibleWorkspaces.map((workspace) => {
                  const canAccess = workspace.can_access !== false
                  const isSelected = workspace.id === trimmedWorkspaceId

                  return (
                    <Button
                      aria-label={
                        canAccess
                          ? `Select Workspace ${workspace.name}`
                          : `Workspace ${workspace.name}. No tienes acceso a ese workspace`
                      }
                      aria-selected={isSelected}
                      className={cn(
                        [
                          'grid h-auto min-h-[42px] w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center justify-stretch gap-2 max-[680px]:min-h-11 max-[680px]:gap-0.5',
                          'rounded-md border border-transparent bg-transparent px-2 py-1.5 text-left text-sm tracking-tight text-muted-foreground motion-safe:transition-colors max-[680px]:px-0.5 max-[680px]:text-[0.5625rem]',
                          'hover:border-border',
                        ],
                        isSelected && 'border-primary/40 bg-primary/15 text-foreground',
                        !canAccess && 'cursor-not-allowed opacity-55',
                      )}
                      data-selected={isSelected ? '' : undefined}
                      disabled={!canAccess}
                      key={workspace.id}
                      onClick={() => handleSelectWorkspace(workspace.id)}
                      role="option"
                      slotName="workspace-selector-option"
                      title={
                        canAccess ? undefined : 'No tienes acceso a ese workspace'
                      }
                      type="button"
                      variant="ghost"
                    >
                      <span className="grid min-w-0 gap-0.5 max-[680px]:gap-0">
                        <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-xs font-extrabold tracking-tight text-foreground max-[680px]:text-[0.5625rem]">
                          {workspace.name}
                        </strong>
                      </span>
                      {!canAccess ? (
                        <span
                          aria-label="No tienes acceso a ese workspace"
                          className="inline-flex justify-self-end text-muted-foreground"
                          data-slot="workspace-selector-lock"
                          title="No tienes acceso a ese workspace"
                        >
                          <LockKeyhole aria-hidden="true" className="size-3.5" />
                        </span>
                      ) : null}
                    </Button>
                  )
                })
              ) : (
                <p
                  className="m-0 text-xs font-bold text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug"
                  data-slot="workspace-selector-empty"
                >
                  No Workspaces match.
                </p>
              )}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </div>
    </Popover.Root>
  )
}

function getVisibleWorkspaceOptions(workspaces: Workspace[], search: string): Workspace[] {
  const normalizedSearch = search.trim().toLowerCase()
  const filteredWorkspaces =
    normalizedSearch.length === 0
      ? workspaces
      : workspaces.filter((workspace) =>
          workspace.name.toLowerCase().includes(normalizedSearch),
        )

  return [...filteredWorkspaces].sort((left, right) => {
    const leftCanAccess = left.can_access !== false
    const rightCanAccess = right.can_access !== false
    if (leftCanAccess !== rightCanAccess) {
      return leftCanAccess ? -1 : 1
    }

    const nameComparison = WORKSPACE_NAME_COLLATOR.compare(left.name, right.name)
    return nameComparison === 0 ? left.id.localeCompare(right.id) : nameComparison
  })
}

function getWorkspaceName(workspaceId: string, workspaces: Workspace[]): string {
  const trimmedWorkspaceId = workspaceId.trim()
  const workspace = workspaces.find((item) => item.id === trimmedWorkspaceId)
  const name = workspace?.name.trim()
  if (name !== undefined && name.length > 0) {
    return name
  }
  return trimmedWorkspaceId.length > 0 ? 'Workspace seleccionado' : 'Sin workspace'
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

function sessionDisplayTitle(session: ChatSessionSummary): string {
  const title = session.title?.trim()
  if (title !== undefined && title.length > 0) {
    return title
  }
  return shortSessionId(session.session_id)
}

function shortSessionId(sessionId: string): string {
  if (sessionId.length <= 12) {
    return sessionId
  }
  return sessionId.slice(0, 8)
}
