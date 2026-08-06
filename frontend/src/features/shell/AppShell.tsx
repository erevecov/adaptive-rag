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

import { Button, IconButton } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { SidebarItem as UiSidebarItem } from '@/components/ui/nav'
import * as Popover from '@/components/ui/popover'
import { SessionNavigationPanel } from '@/features/history/HistoryInspectorView'
import { type RuntimeSubmodule } from '@/features/runtime/runtimeUi'
import {
  type ChatSessionDetailResponse,
  type ChatSessionSummary,
  type Project,
} from '@/lib/apiClient'
import { useFocusTrap } from '@/lib/focusTrap'
import { cn } from '@/lib/utils'

const PROJECT_NAME_COLLATOR = new Intl.Collator(undefined, {
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
      { id: 'projects', label: 'Projects' },
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
      { id: 'project_overrides', label: 'Project Overrides' },
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
export type SettingsNavigationSelection =
  | { module: 'authoring'; submodule: AuthoringSubmodule }
  | { module: 'observability'; submodule: ObservabilitySubmodule }
  | { module: 'runtime'; submodule: RuntimeSubmodule }
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
    primaryView === 'chat' ? 'Skip to chat composer' : 'Skip to main content'

  return (
    <main
      className={cn(
        [
          'app-shell grid h-screen min-h-screen overflow-hidden bg-background p-0 text-foreground',
            'grid-cols-[var(--left-sidebar-width)_minmax(0,1fr)] motion-safe:transition-[grid-template-columns] motion-safe:duration-200 motion-safe:ease-out',
          'max-[680px]:grid-cols-1',
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
          'focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-[100]',
          'focus-visible:rounded-md focus-visible:bg-primary focus-visible:px-3 focus-visible:py-2',
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
        data-slot="app-shell-sidebar-host"
        {...(isBackgroundInert ? { inert: true } : {})}
      >
        {sidebar}
      </div>

      <section
        aria-labelledby="workspace-title"
        className={cn(
          [
            'workspace min-w-0 self-start h-screen w-full overflow-auto p-7',
            'max-[900px]:p-[18px] max-[680px]:h-screen max-[680px]:overflow-hidden max-[680px]:p-1.5',
          ],
          primaryView === 'chat'
            ? [
                'workspace-chat grid max-w-none grid-rows-[auto_minmax(0,1fr)] gap-1 overflow-hidden px-[18px] pb-2.5 pt-1.5',
                'max-[900px]:px-3.5 max-[900px]:py-3',
                'max-[680px]:gap-0 max-[680px]:px-1 max-[680px]:pb-0 max-[680px]:pt-0.5',
              ]
            : 'mx-auto max-w-[1240px]',
        )}
        data-slot="workspace"
        id="main-content"
        tabIndex={-1}
      >
        <div
          data-slot="workspace-topline-host"
          {...(isBackgroundInert ? { inert: true } : {})}
        >
          {topline}
        </div>
        {children}
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
          'workspace-grid chat-workspace-grid grid h-full min-h-0 items-stretch gap-[18px] grid-cols-[minmax(0,1fr)]',
          'max-[680px]:min-h-0',
        ],
        isRightDockInline &&
          'chat-workspace-grid-docked grid-cols-[minmax(0,1fr)_minmax(330px,390px)] max-[900px]:grid-cols-1',
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
  projectId,
  projects,
  selectedSessionId,
  sessionDetail,
  sessions,
}: {
  isChatWorkspace?: boolean
  isLeftSidebarOpen?: boolean
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
      className={cn(
        [
          'workspace-topline flex min-h-5 min-w-0 items-center gap-1.5 text-foreground tracking-tight max-[680px]:min-h-11 max-[680px]:gap-1',
        ],
        isChatWorkspace ? 'mb-0' : 'mb-[22px] max-[680px]:mb-1.5',
        !isLeftSidebarOpen && 'pl-12 max-[680px]:pl-14',
      )}
      data-slot="workspace-topline"
    >
      <h1
        className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-[13px] font-extrabold leading-[1.2] tracking-tight text-foreground max-[680px]:text-[0.625rem]"
        id="workspace-title"
        title={sessionName}
      >
        {sessionName}
      </h1>
      <span
        className="workspace-project-chip min-w-0 max-w-[min(34vw,12rem)] shrink overflow-hidden text-ellipsis whitespace-nowrap rounded-md border border-border bg-muted/15 px-1.5 py-0.5 text-[11px] font-bold leading-[1.2] text-muted-foreground max-[680px]:px-1 max-[680px]:text-[0.5625rem]"
        data-slot="workspace-project-chip"
        title={projectName}
      >
        {projectName}
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
      // Don't steal Escape from open menus/dialogs (e.g. project selector).
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
          'relative z-40 grid h-screen min-w-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden',
          // Solid card (not /90) keeps the rail opaque on purple/dark backgrounds.
          'border-r border-border bg-card shadow-[1px_0_0_0] shadow-primary/15 motion-safe:transition-[background,border-color,box-shadow,opacity,width] motion-safe:duration-200',
          'max-[680px]:fixed max-[680px]:left-0 max-[680px]:top-0 max-[680px]:h-screen',
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
'grid min-h-14 grid-cols-[36px_minmax(0,1fr)] items-center gap-2.5 border-b border-border px-3 py-2.5 shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:min-h-11 max-[680px]:gap-1 max-[680px]:px-2 max-[680px]:py-1',
          !isOpen && 'min-h-0 border-b-transparent p-0 shadow-none',
        )}
        data-slot="app-sidebar-chrome"
      >
        <IconButton
          aria-expanded={isOpen}
          className={cn(
            'border-border bg-card text-foreground hover:border-primary hover:bg-primary/15 hover:text-foreground',
            !isOpen &&
              // z-50 stays under inspector backdrop (z-60) so Menu cannot pierce the modal scrim.
              'pointer-events-auto fixed left-3.5 top-3.5 z-50 bg-card shadow-[var(--shadow-sidebar-toggle)] max-[680px]:left-3 max-[680px]:top-3',
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
          <strong className="truncate text-sm font-extrabold leading-tight tracking-tight text-foreground max-[680px]:text-[0.625rem]">
            Adaptive RAG
          </strong>
          <span className="truncate text-[11px] font-medium leading-tight tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem]">
            Workspace
          </span>
        </div>
      </div>

      <div
        className={cn(
          'grid min-h-0 min-w-0 grid-rows-[auto_auto_minmax(0,1fr)] gap-2.5 overflow-x-hidden overflow-y-auto px-2.5 pb-3 pt-2.5 motion-safe:transition-[opacity,transform] motion-safe:duration-150 max-[680px]:gap-1 max-[680px]:px-1 max-[680px]:pb-1.5 max-[680px]:pt-1',
          !isOpen && 'pointer-events-none -translate-x-2.5 opacity-0',
        )}
        data-slot="app-sidebar-content"
        {...(!isOpen ? { inert: true } : {})}
      >
        <SidebarProjectSelector
          onProjectIdChange={onProjectIdChange}
          projectId={projectId}
          projects={projects}
          state={projectState}
        />

        <nav
          aria-label="Primary Navigation"
          className="grid min-w-0 grid-cols-2 gap-1 border-b border-border pb-2.5 shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:gap-0.5 max-[680px]:pb-1"
          data-slot="sidebar-primary-navigation"
        >
          <SidebarNavButton
            active={primaryView === 'chat'}
            label="Chat"
            onClick={() => onPrimaryViewChange('chat')}
          />
          <SidebarNavButton
            active={primaryView === 'account'}
            label="My Account"
            onClick={() => onPrimaryViewChange('account')}
          />
          <SidebarNavButton
            active={primaryView === 'settings'}
            className="col-span-2"
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
  className,
  label,
  onClick,
}: {
  active: boolean
  className?: string
  label: string
  onClick(): void
}) {
  return (
    <UiSidebarItem
      active={active}
      className={cn(
        // min-w-0 so 1fr/2-col tracks shrink below label min-content (was clipping Settings).
        'h-auto min-h-8 min-w-0 w-full justify-center overflow-hidden whitespace-nowrap rounded-md px-2 py-1.5 text-center text-xs font-medium leading-tight tracking-tight max-[680px]:min-h-11 max-[680px]:px-1 max-[680px]:text-[0.625rem]',
        'hover:bg-primary/15 hover:text-foreground',
        active && 'bg-primary/15 font-semibold text-foreground',
        className,
      )}
      onClick={onClick}
      title={label}
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
    <nav
      aria-label="My Account Navigation"
      className="grid content-start items-stretch self-start border-t border-border pt-[18px] shadow-[0_-1px_0_0] shadow-primary/15 max-[680px]:pt-1.5"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight tracking-tight text-foreground uppercase max-[680px]:text-[0.625rem] max-[680px]:tracking-wider"
        data-slot="sidebar-contextual-title"
      >
        My Account
      </h2>
      <div className="mt-2.5 grid gap-1 max-[680px]:mt-1.5 max-[680px]:gap-0.5" data-slot="sidebar-contextual-group">
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
      className="grid content-start items-stretch self-start border-t border-border pt-[18px] shadow-[0_-1px_0_0] shadow-primary/15 max-[680px]:pt-1.5"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight tracking-tight text-foreground uppercase max-[680px]:text-[0.625rem] max-[680px]:tracking-wider"
        data-slot="sidebar-contextual-title"
      >
        Settings
      </h2>
      <div className="mt-2.5 grid gap-1 max-[680px]:mt-1.5 max-[680px]:gap-0.5" data-slot="sidebar-contextual-group">
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
      <div className="mt-2.5 grid gap-1" data-slot="sidebar-contextual-group">
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
      <div className="mt-2.5 grid gap-1" data-slot="sidebar-contextual-group">
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
              'relative ml-3 min-h-[30px] max-[680px]:min-h-11 w-[calc(100%-0.75rem)] rounded-md px-[18px] text-xs tracking-tight max-[680px]:px-2.5 max-[680px]:text-[0.625rem]',
              'before:absolute before:bottom-[-4px] before:left-[-5px] before:top-[-4px] before:w-px before:rounded-full before:bg-border',
              active && 'before:hidden',
            ]
          : 'min-h-9 max-[680px]:min-h-11 rounded-md px-2.5 text-sm tracking-tight max-[680px]:px-2 max-[680px]:text-[0.625rem]',
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
  const trimmedProjectId = projectId.trim()
  const selectedProject = projects.find((project) => project.id === trimmedProjectId)
  const selectedLabel =
    selectedProject?.name ??
    (trimmedProjectId.length > 0 ? 'Project selected' : 'Select project')
  const visibleProjects = useMemo(
    () => getVisibleProjectOptions(projects, projectSearch),
    [projectSearch, projects],
  )

  function handleSelectProject(nextProjectId: string) {
    onProjectIdChange(nextProjectId)
    setIsOpen(false)
    setProjectSearch('')
  }

  return (
    <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
      <div className="relative z-[90] min-w-0" data-slot="project-selector">
        <Popover.Trigger asChild>
          <Button
            aria-label={`Project selector: ${selectedLabel}`}
            className={cn(
              [
                'grid h-auto min-h-12 w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center justify-stretch gap-2',
                'rounded-lg border border-border bg-card px-2.5 py-2 text-left text-foreground motion-safe:transition-colors',
                'hover:border-primary',
              ],
              isOpen && 'border-primary bg-primary/15',
            )}
            slotName="project-selector-trigger"
            type="button"
            variant="ghost"
          >
            <span className="grid min-w-0 gap-0.5">
              <small className="text-[10px] font-extrabold uppercase tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
                Project
              </small>
              <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm font-extrabold text-foreground max-[680px]:text-[0.625rem] max-[680px]:leading-snug">
                {selectedLabel}
              </strong>
            </span>
            <ChevronDown aria-hidden="true" className="size-5" />
          </Button>
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Content
            align="start"
            className="z-[120] grid w-[var(--radix-popover-trigger-width)] gap-2 rounded-lg border border-border bg-popover p-2 text-popover-foreground shadow-[var(--shadow-popover)] max-[680px]:gap-1 max-[680px]:rounded-md max-[680px]:p-1 max-[680px]:text-[0.625rem]"
            data-slot="project-selector-popover"
            onCloseAutoFocus={(event) => event.preventDefault()}
            side="bottom"
            sideOffset={6}
          >
            <label className="grid gap-1.5 max-[680px]:gap-1" data-slot="project-selector-search">
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-wider">
                Search Projects
              </span>
              <Input
                aria-label="Search Projects"
                autoComplete="off"
                autoFocus
                className="h-[34px] text-xs max-[680px]:min-h-11 max-[680px]:text-base max-[680px]:leading-snug"
                name="project-search"
                onChange={(event) => setProjectSearch(event.currentTarget.value)}
                placeholder="Search Projects"
                type="search"
                value={projectSearch}
              />
            </label>

            <div
              className="flex items-center justify-between gap-2"
              data-slot="project-selector-popover-header"
            >
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground">
                {state === 'loading' ? 'Loading Projects…' : 'All Projects'}
              </span>
            </div>

            <div
              aria-label="Projects"
              className="grid max-h-72 gap-1 overflow-auto"
              data-slot="project-selector-list"
              role="listbox"
            >
              {visibleProjects.length > 0 ? (
                visibleProjects.map((project) => {
                  const canAccess = project.can_access !== false
                  const isSelected = project.id === trimmedProjectId

                  return (
                    <Button
                      aria-label={
                        canAccess
                          ? `Select project ${project.name}`
                          : `Project ${project.name}. No tienes acceso para ese proyecto`
                      }
                      aria-selected={isSelected}
                      className={cn(
                        [
                          'grid h-auto min-h-[42px] w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center justify-stretch gap-2 max-[680px]:min-h-11 max-[680px]:gap-1',
                          'rounded-md border border-transparent bg-transparent px-2 py-1.5 text-left text-sm tracking-tight text-muted-foreground motion-safe:transition-colors max-[680px]:px-1 max-[680px]:text-[0.625rem]',
                          'hover:border-border',
                        ],
                        isSelected && 'border-primary/40 bg-primary/15 text-foreground',
                        !canAccess && 'cursor-not-allowed opacity-55',
                      )}
                      data-selected={isSelected ? '' : undefined}
                      disabled={!canAccess}
                      key={project.id}
                      onClick={() => handleSelectProject(project.id)}
                      role="option"
                      slotName="project-selector-option"
                      title={
                        canAccess ? undefined : 'No tienes acceso para ese proyecto'
                      }
                      type="button"
                      variant="ghost"
                    >
                      <span className="grid min-w-0 gap-0.5 max-[680px]:gap-0">
                        <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-xs font-extrabold tracking-tight text-foreground max-[680px]:text-[0.625rem]">
                          {project.name}
                        </strong>
                      </span>
                      {!canAccess ? (
                        <span
                          aria-label="No tienes acceso para ese proyecto"
                          className="inline-flex justify-self-end text-muted-foreground"
                          data-slot="project-selector-lock"
                          title="No tienes acceso para ese proyecto"
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
                  data-slot="project-selector-empty"
                >
                  No Projects match.
                </p>
              )}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </div>
    </Popover.Root>
  )
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
