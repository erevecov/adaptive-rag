import { type ReactNode, useMemo, useState } from 'react'
import * as Popover from '@radix-ui/react-popover'

import { IconButton } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { SidebarItem as UiSidebarItem } from '@/components/ui/nav'
import { SessionNavigationPanel } from '@/features/history/HistoryInspectorView'
import { type RuntimeSubmodule } from '@/features/runtime/runtimeUi'
import {
  type ChatSessionDetailResponse,
  type ChatSessionSummary,
  type Project,
} from '@/lib/apiClient'
import { cn } from '@/lib/utils'

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
  isLeftSidebarOpen,
  isRightDockOpen,
  primaryView,
  sidebar,
  topline,
}: {
  children: ReactNode
  isLeftSidebarOpen: boolean
  isRightDockOpen: boolean
  primaryView: PrimaryView
  sidebar: ReactNode
  topline: ReactNode
}) {
  return (
    <main
      className={[
        'app-shell',
        isLeftSidebarOpen
          ? 'app-shell-sidebar-open'
          : 'app-shell-sidebar-closed',
        isRightDockOpen ? 'app-shell-right-dock-open' : 'app-shell-right-dock-closed',
      ].join(' ')}
      data-slot="app-shell"
    >
      {sidebar}

      <section
        className={primaryView === 'chat' ? 'workspace workspace-chat' : 'workspace'}
        aria-labelledby="workspace-title"
      >
        {topline}
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
      className={
        isRightDockInline
          ? 'workspace-grid chat-workspace-grid chat-workspace-grid-docked'
          : 'workspace-grid chat-workspace-grid'
      }
      data-slot="chat-workspace-grid"
    >
      {children}
    </div>
  )
}

export function WorkspaceTopline({
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
  return (
    <aside
      aria-label="Primary sidebar"
      className={cn(
        [
          'relative z-40 grid h-screen min-w-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden',
          'border-r border-border bg-card/90 transition-[background,border-color,opacity,width] duration-200',
          'max-[680px]:fixed max-[680px]:left-0 max-[680px]:top-0 max-[680px]:h-screen',
        ],
        isOpen
          ? 'w-[306px] max-[680px]:w-[min(86vw,306px)] max-[680px]:shadow-[var(--shadow-mobile-sidebar)]'
          : 'w-0 overflow-visible border-r-transparent bg-transparent pointer-events-none max-[680px]:shadow-none',
      )}
      data-slot="app-sidebar"
      data-state={isOpen ? 'open' : 'closed'}
    >
      <div
        className={cn(
          'grid min-h-[72px] grid-cols-[42px_minmax(0,1fr)] items-center gap-3 px-4 py-3.5',
          !isOpen && 'min-h-0 p-0',
        )}
        data-slot="app-sidebar-chrome"
      >
        <IconButton
          aria-expanded={isOpen}
          className={cn(
            'border-border bg-card text-foreground hover:border-primary hover:bg-accent hover:text-accent-foreground',
            !isOpen &&
              'pointer-events-auto fixed left-3.5 top-3.5 z-[70] bg-card/90 shadow-[var(--shadow-sidebar-toggle)] max-[680px]:left-3 max-[680px]:top-3',
          )}
          label={isOpen ? 'Collapse left sidebar' : 'Open left sidebar'}
          onClick={onToggle}
        >
          <MenuIcon />
        </IconButton>
        <div
          className={cn(
            'grid min-w-0 gap-1 transition-[opacity,transform] duration-150',
            !isOpen && 'pointer-events-none -translate-x-2.5 opacity-0',
          )}
          aria-hidden={!isOpen}
          data-slot="sidebar-brand"
        >
          <strong>Adaptive RAG</strong>
          <span>Workspace</span>
        </div>
      </div>

      <div
        className={cn(
          'grid min-h-0 grid-rows-[auto_auto_minmax(0,1fr)] gap-[18px] overflow-x-hidden overflow-y-auto px-4 pb-[18px] transition-[opacity,transform] duration-150',
          !isOpen && 'pointer-events-none -translate-x-2.5 opacity-0',
        )}
        data-slot="app-sidebar-content"
      >
        <SidebarProjectSelector
          onProjectIdChange={onProjectIdChange}
          projectId={projectId}
          projects={projects}
          state={projectState}
        />

        <nav
          aria-label="Primary navigation"
          className="grid grid-cols-[minmax(56px,auto)_minmax(104px,1fr)_minmax(74px,auto)] gap-2 border-b border-border pb-3.5"
          data-slot="sidebar-primary-navigation"
        >
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
      className="min-h-10 justify-center overflow-hidden px-2 text-center text-xs"
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
    <nav
      aria-label="My account navigation"
      className="grid content-start items-stretch self-start border-t border-border pt-[18px]"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight text-foreground uppercase"
        data-slot="sidebar-contextual-title"
      >
        My account
      </h2>
      <div className="mt-2.5 grid gap-1" data-slot="sidebar-contextual-group">
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
      aria-label="Settings navigation"
      className="grid content-start items-stretch self-start border-t border-border pt-[18px]"
      data-slot="sidebar-contextual-navigation"
    >
      <h2
        className="text-sm font-semibold leading-tight text-foreground uppercase"
        data-slot="sidebar-contextual-title"
      >
        Settings
      </h2>
      <div className="mt-2.5 grid gap-1" data-slot="sidebar-contextual-group">
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
    <button
      aria-pressed={active}
      className={cn(
        [
          'flex w-full cursor-pointer items-center justify-start border border-transparent bg-transparent text-left text-muted-foreground transition-colors',
          'hover:border-border hover:bg-accent hover:text-accent-foreground',
          'disabled:cursor-not-allowed disabled:opacity-55',
        ],
        subitem
          ? [
              'relative ml-3 min-h-[30px] w-[calc(100%-0.75rem)] rounded-md px-[18px] text-xs',
              'before:absolute before:bottom-[-4px] before:left-[-5px] before:top-[-4px] before:w-px before:rounded-full before:bg-border',
              active && 'before:hidden',
            ]
          : 'min-h-9 rounded-md px-2.5 text-sm',
        active && 'border-border bg-accent text-accent-foreground',
      )}
      data-active={active ? '' : undefined}
      data-slot={slot}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
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
          <button
            aria-label={`Project selector: ${selectedLabel}`}
            className={cn(
              [
                'grid min-h-12 w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-2',
                'rounded-lg border border-border bg-card px-2.5 py-2 text-left text-foreground transition-colors',
                'hover:border-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              ],
              isOpen && 'border-primary bg-accent',
            )}
            data-slot="project-selector-trigger"
            type="button"
          >
            <span className="grid min-w-0 gap-0.5">
              <small className="text-[10px] font-extrabold uppercase text-muted-foreground">
                Project
              </small>
              <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm font-extrabold text-foreground">
                {selectedLabel}
              </strong>
            </span>
            <ChevronDownIcon />
          </button>
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Content
            align="start"
            className="z-[120] grid w-[var(--radix-popover-trigger-width)] gap-2 rounded-lg border border-border bg-popover p-2 text-popover-foreground shadow-[var(--shadow-popover)]"
            data-slot="project-selector-popover"
            onCloseAutoFocus={(event) => event.preventDefault()}
            side="bottom"
            sideOffset={6}
          >
            <label className="grid gap-1.5" data-slot="project-selector-search">
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground">
                Search projects
              </span>
              <Input
                aria-label="Search projects"
                autoComplete="off"
                autoFocus
                className="h-[34px] text-xs"
                name="project-search"
                onChange={(event) => setProjectSearch(event.currentTarget.value)}
                placeholder="Search projects"
                type="search"
                value={projectSearch}
              />
            </label>

            <div
              className="flex items-center justify-between gap-2"
              data-slot="project-selector-popover-header"
            >
              <span className="text-[10px] font-extrabold uppercase text-muted-foreground">
                {state === 'loading' ? 'Loading projects...' : 'All projects'}
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
                    <button
                      aria-label={
                        canAccess
                          ? `Select project ${project.name}`
                          : `Project ${project.name}. No tienes acceso para ese proyecto`
                      }
                      aria-selected={isSelected}
                      className={cn(
                        [
                          'grid min-h-[42px] w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-2',
                          'rounded-md border border-transparent bg-transparent px-2 py-1.5 text-left text-muted-foreground transition-colors',
                          'hover:border-border hover:bg-accent hover:text-accent-foreground',
                        ],
                        isSelected && 'border-border bg-accent text-accent-foreground',
                        !canAccess && 'cursor-not-allowed opacity-55',
                      )}
                      data-selected={isSelected ? '' : undefined}
                      data-slot="project-selector-option"
                      disabled={!canAccess}
                      key={project.id}
                      onClick={() => handleSelectProject(project.id)}
                      role="option"
                      title={
                        canAccess ? undefined : 'No tienes acceso para ese proyecto'
                      }
                      type="button"
                    >
                      <span className="grid min-w-0 gap-0.5">
                        <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-xs font-extrabold text-foreground">
                          {project.name}
                        </strong>
                      </span>
                      {!canAccess ? (
                        <span
                          aria-label="No tienes acceso para ese proyecto"
                          className="inline-flex justify-self-end text-muted-foreground [&_.ui-icon]:h-3.5 [&_.ui-icon]:w-3.5"
                          data-slot="project-selector-lock"
                          title="No tienes acceso para ese proyecto"
                        >
                          <LockIcon />
                        </span>
                      ) : null}
                    </button>
                  )
                })
              ) : (
                <p
                  className="m-0 text-xs font-bold text-muted-foreground"
                  data-slot="project-selector-empty"
                >
                  No projects match.
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
