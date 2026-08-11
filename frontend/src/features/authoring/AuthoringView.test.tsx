/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import { chooseRadixSelectOption } from '@/test/radixSelect'
import type {
  IngestionJob,
  IngestionRunResponse,
  KnowledgeProposal,
  Workspace,
  WorkspaceMembership,
  Source,
  User,
} from '@/lib/apiClient'
import { AuthoringPanel } from './AuthoringView'

installPointerEventMocks()

afterEach(() => {
  cleanup()
})

const workspace: Workspace = {
  access_role: 'admin',
  budget_config_json: null,
  can_access: true,
  created_at: '2026-06-22T00:00:00Z',
  embedding_mode: 'dense',
  id: 'workspace-1',
  name: 'Demo',
  retrieval_contextualization_enabled: false,
  updated_at: '2026-06-22T00:00:00Z',
}

const restrictedWorkspace: Workspace = {
  ...workspace,
  access_role: null,
  can_access: false,
  id: 'workspace-2',
  name: 'Restricted',
}

const source: Source = {
  created_at: '2026-06-22T00:00:00Z',
  external_id: 'notes.md',
  extra_metadata: null,
  id: 'source-1',
  workspace_id: workspace.id,
  source_type: 'markdown',
  tags: ['docs'],
  updated_at: '2026-06-22T00:00:00Z',
}

const user: User = {
  created_at: '2026-06-22T00:00:00Z',
  display_name: 'Viewer User',
  id: 'user-1',
  is_active: true,
  last_workspace_id: null,
  login: 'viewer@example.com',
  system_role: 'user',
  updated_at: '2026-06-22T00:00:00Z',
}

const membership: WorkspaceMembership = {
  created_at: '2026-06-22T00:00:00Z',
  id: 'membership-1',
  workspace_id: workspace.id,
  role: 'admin',
  updated_at: '2026-06-22T00:00:00Z',
  user_id: user.id,
}

const proposal: KnowledgeProposal = {
  approved_source_id: null,
  created_at: '2026-06-22T00:00:00Z',
  id: 'proposal-1',
  origin_message_id: null,
  origin_session_id: null,
  workspace_id: workspace.id,
  proposed_text: 'Document the escalation runbook.',
  refined_text: 'Existing refined text.',
  review_note: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  status: 'pending',
  submitted_by_user_id: null,
  updated_at: '2026-06-22T00:00:00Z',
}

const ingestionJob: IngestionJob = {
  attempts: 1,
  created_at: '2026-06-22T00:00:00Z',
  id: 'job-1',
  job_type: 'ingest_source',
  last_error: 'missing content',
  locked_by: null,
  locked_until: null,
  max_attempts: 3,
  payload_json: { source_id: source.id },
  priority: 0,
  workspace_id: workspace.id,
  run_after: '2026-06-22T00:00:02Z',
  status: 'blocked',
  updated_at: '2026-06-22T00:00:00Z',
}

function ingestionJobWithStatus(status: string, id = `job-${status}`): IngestionJob {
  return {
    ...ingestionJob,
    id,
    last_error:
      status === 'blocked' || status === 'dead_letter' || status === 'failed'
        ? `${status} explanation`
        : null,
    payload_json: { source_id: `source-for-${id}` },
    status,
  }
}

const ingestionRun: IngestionRunResponse = {
  created_document_version: null,
  document_id: null,
  document_version_id: null,
  error_message: null,
  job_id: null,
  workspace_id: workspace.id,
  source_id: null,
  status: 'idle',
  worker_id: 'frontend',
}

function fiveWorkspaces(): Workspace[] {
  return [
    workspace,
    restrictedWorkspace,
    ...Array.from({ length: 3 }, (_, index) => ({
      ...workspace,
      id: `workspace-${index + 3}`,
      name: `Workspace ${index + 3}`,
    })),
  ]
}

function fiveUsers(): User[] {
  return Array.from({ length: 5 }, (_, index) => ({
    ...user,
    display_name: `User ${index + 1}`,
    id: `user-${index + 1}`,
    login: `user-${index + 1}@example.com`,
  }))
}

function fiveSources(): Source[] {
  return Array.from({ length: 5 }, (_, index) => ({
    ...source,
    external_id: `source-${index + 1}.md`,
    id: `source-${index + 1}`,
  }))
}

function noopSubmit(event: React.FormEvent<HTMLFormElement>) {
  event.preventDefault()
}

function renderAuthoringPanel(
  overrides: Partial<React.ComponentProps<typeof AuthoringPanel>> = {},
) {
  const props: React.ComponentProps<typeof AuthoringPanel> = {
    accessError: null,
    accessState: 'idle',
    activeSubmodule: 'workspaces',
    ingestionError: null,
    ingestionJobs: [ingestionJob],
    ingestionRun,
    ingestionState: 'idle',
    knowledgeProposals: [proposal],
    knowledgeReviewError: null,
    knowledgeReviewState: 'idle',
    memberRole: 'viewer',
    memberUserId: '',
    memberships: [membership],
    onApproveKnowledgeProposal: vi.fn(),
    onCreateWorkspace: vi.fn(noopSubmit),
    onCreateSource: vi.fn(noopSubmit),
    onCreateUser: vi.fn(noopSubmit),
    onDeactivateUser: vi.fn(),
    onDeleteMembership: vi.fn(),
    onDeleteWorkspace: vi.fn(),
    onDeleteSource: vi.fn(),
    onEnqueueIngestion: vi.fn(),
    onMemberRoleChange: vi.fn(),
    onMemberUserIdChange: vi.fn(),
    onWorkspaceIdChange: vi.fn(),
    onWorkspaceNameChange: vi.fn(),
    onProposalDraftChange: vi.fn(),
    onProposalRejectReasonChange: vi.fn(),
    onRefreshAccess: vi.fn(),
    onRefreshIngestionJobs: vi.fn(),
    onRefreshKnowledgeProposals: vi.fn(),
    onRefreshSources: vi.fn(),
    onRefineKnowledgeProposal: vi.fn(),
    onRejectKnowledgeProposal: vi.fn(),
    onRetryIngestionJob: vi.fn(),
    onRevokeAccessToken: vi.fn(),
    onRunNextIngestion: vi.fn(),
    onSaveWorkspaceMembership: vi.fn(noopSubmit),
    onSelectWorkspace: vi.fn(),
    onSourceContentChange: vi.fn(),
    onSourceExternalIdChange: vi.fn(),
    onSourceFileChange: vi.fn(),
    onSourceTagsChange: vi.fn(),
    onSourceTypeChange: vi.fn(),
    onUserAccessTokenChange: vi.fn(),
    onUserDisplayNameChange: vi.fn(),
    onUserLoginChange: vi.fn(),
    onUserSystemRoleChange: vi.fn(),
    workspaceError: null,
    workspaceId: workspace.id,
    workspaceName: '',
    workspaceState: 'idle',
    workspaces: [workspace, restrictedWorkspace],
    proposalDrafts: {},
    proposalRejectReasons: {},
    sourceContent: '',
    sourceError: null,
    sourceExternalId: '',
    sourceFileName: '',
    sourceState: 'idle',
    sourceTags: '',
    sourceType: 'markdown',
    sources: [source],
    userAccessToken: '',
    userDisplayName: '',
    userLogin: '',
    userSystemRole: 'user',
    users: [user],
    ...overrides,
  }

  return {
    props,
    view: render(<AuthoringPanel {...props} />),
  }
}

function expectNoLegacyAuthoringClasses(container: HTMLElement) {
  expect(container.querySelector('.authoring-row')).toBeNull()
  expect(container.querySelector('.authoring-form')).toBeNull()
  expect(container.querySelector('.authoring-panel')).toBeNull()
  expect(container.querySelector('.ingestion-panel')).toBeNull()
}

describe('AuthoringPanel', () => {
  test('adopts searchable record grids only for long workspace, user, and source collections', async () => {
    const userDriver = userEvent.setup()
    const workspaceView = renderAuthoringPanel({ workspaces: fiveWorkspaces() })
    expect(
      screen.getByRole('region', { name: 'Workspaces' }).getAttribute('data-slot'),
    ).toBe('records-grid')
    const workspaceSearch = screen.getByRole('region', {
      name: 'Find Workspaces',
    })
    expect(workspaceSearch.getAttribute('data-slot')).toBe('command-search')
    expect(within(workspaceSearch).queryByRole('list')).toBeNull()
    expect(
      within(screen.getByRole('region', { name: 'Workspaces' })).getByText(
        'Demo',
      ),
    ).toBeTruthy()
    const workspaceSearchbox = within(workspaceSearch).getByRole('searchbox')
    await userDriver.type(workspaceSearchbox, 'Demo')
    await userDriver.click(
      within(workspaceSearch).getByRole('button', { name: /^Demo/ }),
    )
    expect(workspaceView.props.onSelectWorkspace).toHaveBeenCalledWith(
      fiveWorkspaces()[0],
    )
    vi.mocked(workspaceView.props.onSelectWorkspace).mockClear()
    await userDriver.clear(workspaceSearchbox)
    await userDriver.type(workspaceSearchbox, 'Restricted')
    await userDriver.click(
      within(workspaceSearch).getByRole('button', { name: /^Restricted/ }),
    )
    expect(workspaceView.props.onSelectWorkspace).not.toHaveBeenCalled()
    expect(document.activeElement?.id).toBe(
      `authoring-workspace-${restrictedWorkspace.id}`,
    )
    workspaceView.view.unmount()

    const usersView = renderAuthoringPanel({
      activeSubmodule: 'users',
      users: fiveUsers(),
    })
    expect(
      screen.getByRole('region', { name: 'Users' }).getAttribute('data-slot'),
    ).toBe('records-grid')
    const userSearch = screen.getByRole('region', { name: 'Find Users' })
    expect(userSearch.getAttribute('data-slot')).toBe('command-search')
    expect(within(userSearch).queryByRole('list')).toBeNull()
    await userDriver.type(
      within(userSearch).getByRole('searchbox'),
      'user-1@example.com',
    )
    await userDriver.click(
      within(userSearch).getByRole('button', { name: /^user-1@example\.com/ }),
    )
    expect(document.activeElement?.id).toBe('authoring-user-user-1')
    usersView.view.unmount()

    const sourcesView = renderAuthoringPanel({
      activeSubmodule: 'sources',
      sources: fiveSources(),
    })
    expect(
      screen.getByRole('region', { name: 'Sources' }).getAttribute('data-slot'),
    ).toBe('records-grid')
    const sourceSearch = screen.getByRole('region', { name: 'Find Sources' })
    expect(sourceSearch.getAttribute('data-slot')).toBe('command-search')
    expect(within(sourceSearch).queryByRole('list')).toBeNull()
    await userDriver.type(
      within(sourceSearch).getByRole('searchbox'),
      'source-1.md',
    )
    await userDriver.click(
      within(sourceSearch).getByRole('button', { name: /^source-1\.md/ }),
    )
    expect(document.activeElement?.id).toBe('authoring-source-source-1')
    sourcesView.view.unmount()

    renderAuthoringPanel({ workspaces: [workspace, restrictedWorkspace] })
    expect(screen.queryByRole('region', { name: 'Find Workspaces' })).toBeNull()
  })

  test('adopts proposal decision patterns without changing lifecycle callbacks', async () => {
    const userDriver = userEvent.setup()
    const ready = renderAuthoringPanel({
      activeSubmodule: 'knowledge',
      proposalRejectReasons: { [proposal.id]: 'Duplicate guidance' },
    })

    expect(
      screen.getByRole('article', {
        name: `Knowledge Proposal ${proposal.id}`,
      }).getAttribute('data-slot'),
    ).toBe('recommendation-panel')
    expect(
      screen.getByRole('region', {
        name: `Review Knowledge Proposal ${proposal.id}`,
      }).getAttribute('data-slot'),
    ).toBe('approval-prompt')
    expect(
      screen.getByRole('region', {
        name: `Changes for Knowledge Proposal ${proposal.id}`,
      }).getAttribute('data-slot'),
    ).toBe('change-table')

    await userDriver.click(
      screen.getByRole('button', { name: /^Approve / }),
    )
    await userDriver.click(screen.getByRole('button', { name: /^Refine / }))
    await userDriver.click(screen.getByRole('button', { name: /^Reject / }))
    expect(ready.props.onApproveKnowledgeProposal).toHaveBeenCalledWith(proposal)
    expect(ready.props.onRefineKnowledgeProposal).toHaveBeenCalledWith(proposal)
    expect(ready.props.onRejectKnowledgeProposal).toHaveBeenCalledWith(proposal)
    ready.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'knowledge',
      knowledgeProposals: [{ ...proposal, refined_text: null }],
    })
    expect(screen.queryByRole('region', { name: /Changes for Knowledge Proposal/ })).toBeNull()
    expect(
      (screen.getByRole('button', { name: /^Reject / }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
  })

  test('adopts ingestion task patterns while retrying the exact job', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel({ activeSubmodule: 'sources' })

    expect(
      screen
        .getByRole('region', { name: 'Active and Attention Ingestion Jobs' })
        .getAttribute('data-slot'),
    ).toBe('agent-task-list')
    expect(
      view.container.querySelector('[data-slot="filtered-task-table"]'),
    ).toBeTruthy()
    await userDriver.click(
      screen.getByRole('button', { name: `Retry ingestion job ${ingestionJob.id}` }),
    )
    expect(props.onRetryIngestionJob).toHaveBeenCalledWith(ingestionJob)
  })

  test('uses LoadingGrid only for active collection loads', () => {
    const loading = renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'loading',
      workspaces: [],
    })
    expect(
      screen
        .getByRole('status', { name: 'Loading Workspaces…' })
        .getAttribute('data-slot'),
    ).toBe('loading-grid')
    expect(
      loading.view.container.querySelector('[data-slot-state="empty"]'),
    ).toBeNull()
    loading.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'idle',
      workspaces: [],
    })
    expect(screen.queryByRole('status', { name: 'Loading Workspaces…' })).toBeNull()
    expect(screen.getByText('No Workspaces Yet.')).toBeTruthy()
  })

  test('primary Create buttons keep min-h and stable Creating labels', () => {
    const idle = renderAuthoringPanel({ activeSubmodule: 'workspaces' })
    const create = screen.getByRole('button', { name: 'Create Workspace' })
    expect(create.className).toMatch(/min-h-9/)
    expect(create.textContent).toContain('Create Workspace')
    idle.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'loading',
    })
    const busy = screen.getByRole('button', { name: 'Creating…' })
    expect(busy.className).toMatch(/min-h-9/)
    expect(busy.textContent).toContain('Creating…')
  })

  test('workspaces submodule uses tokenized panels, controls, and data rows', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel()

    expect(screen.getByLabelText('Workspace Name').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByRole('region', { name: 'Authoring Workspaces' })).toBeTruthy()
    expect(screen.getByText('Ready').getAttribute('data-slot')).toBe('badge')
    expect(
      view.container.querySelector('[data-slot="panel"]'),
    ).toBeTruthy()
    expect(
      screen
        .getByRole('region', { name: 'Workspaces' })
        .querySelectorAll('tbody tr').length,
    ).toBe(2)
    expectNoLegacyAuthoringClasses(view.container)

    await userDriver.click(screen.getByRole('button', { name: 'Select Demo' }))
    expect(props.onSelectWorkspace).toHaveBeenCalledWith(workspace)
    await userDriver.click(
      screen.getByRole('button', { name: 'Delete workspace Demo' }),
    )
    expect(props.onDeleteWorkspace).toHaveBeenCalledWith(workspace)
    expect(
      screen.getByRole('button', { name: 'Select Restricted' }).getAttribute(
        'disabled',
      ),
    ).not.toBeNull()
  })

  test('sorts workspace Access by the exact displayed permission including No Access', async () => {
    const userDriver = userEvent.setup()
    const modeWorkspace: Workspace = {
      ...workspace,
      access_role: null,
      can_access: true,
      id: 'workspace-mode',
      name: 'Mode workspace',
    }
    renderAuthoringPanel({ workspaces: [restrictedWorkspace, modeWorkspace] })

    const grid = screen.getByRole('region', { name: 'Workspaces' })
    await userDriver.click(within(grid).getByRole('button', { name: 'Access' }))

    const rows = Array.from(grid.querySelectorAll('tbody tr'))
    expect(rows).toHaveLength(2)
    expect(rows[0].textContent).toContain('Mode workspace')
    expect(rows[0].textContent).toContain('Dense')
    expect(rows[1].textContent).toContain('Restricted')
    expect(rows[1].textContent).toContain('No Access')
  })

  test('users submodule keeps form labels addressable and uses Radix selects', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel({ activeSubmodule: 'users' })

    expect(screen.getByLabelText('User Login').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Display Name').getAttribute('data-slot')).toBe(
      'input',
    )
    const accessToken = screen.getByLabelText('Access Token')
    expect(accessToken.getAttribute('data-slot')).toBe('input')
    expect(accessToken.getAttribute('type')).toBe('password')
    expect(accessToken.getAttribute('aria-describedby')).toBe(
      'authoring-user-access-token-help',
    )
    const tokenHelp = screen.getByText('Paste Once; Never Shown After Save.')
    expect(tokenHelp.getAttribute('data-slot')).toBe('field-help')
    expect(tokenHelp.id).toBe('authoring-user-access-token-help')
    expect(tokenHelp.closest('[data-slot="field-control"]')).toBeNull()
    expect(tokenHelp.closest('[data-slot="field"]')).toBeTruthy()
    expect(screen.getByLabelText('System Role').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    expect(screen.getByLabelText('Workspace Role').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    await chooseRadixSelectOption(
      userDriver,
      screen.getByLabelText('System Role'),
      'Superadmin',
    )
    await chooseRadixSelectOption(
      userDriver,
      screen.getByLabelText('Workspace Role'),
      'Admin',
    )
    expect(props.onUserSystemRoleChange).toHaveBeenCalledWith('superadmin')
    expect(props.onMemberRoleChange).toHaveBeenCalledWith('admin')
    expect(screen.getAllByText(user.id).length).toBeGreaterThanOrEqual(1)
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('workspace list shows loading instead of empty while busy', () => {
    const { view } = renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'loading',
      workspaces: [],
    })

    expect(screen.queryByText('No Workspaces Yet.')).toBeNull()
    const loadingState = view.container.querySelector('[data-slot-state="loading"]')
    expect(loadingState).toBeTruthy()
    expect(
      loadingState?.querySelector('[data-slot="loading-grid"]')?.textContent,
    ).toContain('Loading Workspaces')
    view.unmount()
  })

  test('knowledge submodule renders proposal actions through tokenized controls', () => {
    const { view } = renderAuthoringPanel({ activeSubmodule: 'knowledge' })

    expect(screen.getByLabelText('Refined Text').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(screen.getByDisplayValue('Existing refined text.')).toBeTruthy()
    expect(screen.getByRole('button', { name: /^Refine / })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^Approve / })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^Reject / })).toBeTruthy()
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('sources submodule exposes ingestion operations and metadata', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel({ activeSubmodule: 'sources' })

    expect(screen.getByLabelText('Workspace ID').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Source Type').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    expect(screen.getByLabelText('Content').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(
      screen.getByRole('button', { name: 'Enqueue ingestion for notes.md' }),
    ).toBeTruthy()
    await userDriver.click(
      screen.getByRole('button', { name: 'Delete source notes.md' }),
    )
    expect(props.onDeleteSource).toHaveBeenCalledWith(source)
    expect(screen.getByText('Attempt 1/3')).toBeTruthy()
    expect(screen.getByText('No Ingestion Job Was Processed.')).toBeTruthy()
    const lastRun = view.container.querySelector(
      '[data-slot="ingestion-last-run"]',
    )
    expect(lastRun).toBeTruthy()
    expect(lastRun?.textContent).toMatch(/Last Run/)
    expect(lastRun?.textContent).toMatch(/Idle/)
    expect(
      lastRun?.querySelector('[data-slot="badge"]')?.getAttribute('data-tone'),
    ).toBe('neutral')
    expect(lastRun?.querySelector('[data-slot="badge"]')?.className).toMatch(
      /tabular-nums/,
    )
    expect(
      screen.getByRole('button', { name: 'Retry ingestion job job-1' }),
    ).toBeTruthy()
    await chooseRadixSelectOption(
      userDriver,
      screen.getByLabelText('Source Type'),
      'URL',
    )
    expect(props.onSourceTypeChange).toHaveBeenCalledWith('url')
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('distinguishes loading lists from empty and canceled status', () => {
    const loading = renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'loading',
      workspaces: [],
    })
    expect(screen.getByText('Loading Workspaces…')).toBeTruthy()
    const loadingState = loading.view.container.querySelector(
      '[data-slot-state="loading"]',
    )
    expect(loadingState).toBeTruthy()
    expect(
      loadingState?.querySelector('[data-slot="loading-grid"]'),
    ).toBeTruthy()
    expect(
      loadingState?.querySelector('[data-slot="loading-mark"]')?.innerHTML,
    ).toMatch(/motion-safe:animate-pulse/)
    loading.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'canceled',
      workspaces: [workspace],
    })
    expect(screen.getByText('Canceled').getAttribute('data-tone')).toBe(
      'neutral',
    )
  })

  test('shows soft-deleted workspace timestamp and danger tone', () => {
    const deleted: Workspace = {
      ...workspace,
      deleted_at: '2026-06-22T12:00:00Z',
      id: 'workspace-deleted',
      name: 'Gone',
    }
    renderAuthoringPanel({ workspaces: [deleted] })
    expect(screen.getByText('Deleted').getAttribute('data-tone')).toBe('danger')
    expect(screen.getByText(/Deleted /)).toBeTruthy()
  })

  test('shows per-column empties when users or memberships are missing', () => {
    renderAuthoringPanel({
      activeSubmodule: 'users',
      memberships: [],
      users: [user],
    })
    expect(screen.getByText('No Workspace Memberships Yet.')).toBeTruthy()
    expect(screen.getByText(user.login)).toBeTruthy()
    cleanup()

    renderAuthoringPanel({
      activeSubmodule: 'users',
      memberships: [membership],
      users: [],
    })
    expect(screen.getByText('No Users Yet.')).toBeTruthy()
    expect(screen.getByText(membership.user_id)).toBeTruthy()
  })

  test('Title Case soft-delete and inactive badges keep full contrast', () => {
    const deletedSource: Source = {
      ...source,
      deleted_at: '2026-06-22T12:00:00Z',
      external_id: 'gone-source',
      id: 'source-deleted',
    }
    const inactiveUser: User = {
      ...user,
      id: 'user-inactive',
      is_active: false,
      login: 'inactive@example.com',
    }
    renderAuthoringPanel({
      activeSubmodule: 'sources',
      sources: [deletedSource],
    })
    expect(screen.getByText('Deleted').getAttribute('data-tone')).toBe('danger')
    expect(screen.getByText(/Deleted /)).toBeTruthy()
    cleanup()

    const { view } = renderAuthoringPanel({
      activeSubmodule: 'users',
      users: [inactiveUser],
    })
    expect(screen.getByText('Inactive').getAttribute('data-tone')).toBe(
      'warning',
    )
    expect(
      view.container.querySelector('[data-inactive]')?.querySelector('strong')
        ?.className,
    ).toMatch(/text-muted-foreground/)
  })

  test('knowledge empty is structured and proposal status is Title Case', () => {
    renderAuthoringPanel({
      activeSubmodule: 'knowledge',
      knowledgeProposals: [],
    })
    expect(screen.getByText('No Pending Proposals.')).toBeTruthy()
    expect(
      screen.getByText(/Refresh After Chat Surfaces a Knowledge Draft/),
    ).toBeTruthy()
    cleanup()

    renderAuthoringPanel({
      activeSubmodule: 'knowledge',
      knowledgeProposals: [proposal],
    })
    expect(screen.getByText('Pending')).toBeTruthy()
  })

  test('knowledge status says Working while busy and gates Reject without reason', () => {
    renderAuthoringPanel({
      activeSubmodule: 'knowledge',
      knowledgeReviewState: 'loading',
      knowledgeProposals: [proposal],
    })
    expect(screen.getByText('Working').getAttribute('data-slot')).toBe('badge')
    expect(
      (screen.getByRole('button', { name: /^Reject / }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
    expect(
      (screen.getByRole('button', { name: /^Approve / }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
    expect(
      (screen.getByRole('button', { name: /^Refine / }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
  })

  test('groups ingestion jobs by status with relative run-after', () => {
    const running: IngestionJob = {
      ...ingestionJob,
      id: 'job-running',
      status: 'running',
      last_error: null,
    }
    const { view } = renderAuthoringPanel({
      activeSubmodule: 'sources',
      ingestionJobs: [ingestionJob, running],
    })
    expect(
      view.container.querySelector('[data-slot="ingestion-job-groups"]'),
    ).toBeTruthy()
    expect(screen.getAllByText('Running').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Blocked').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Run after/).length).toBeGreaterThan(0)
    expect(
      screen.getByRole('button', { name: 'Retry ingestion job job-1' }),
    ).toBeTruthy()
  })

  test('keeps exact ingestion statuses while separating active attention from full history', () => {
    const statuses = ['queued', 'running', 'succeeded', 'failed', 'blocked', 'dead_letter']
    const jobs = statuses.map((status) => ingestionJobWithStatus(status))
    jobs[4] = {
      ...jobs[4],
      last_error: 'unique blocked explanation',
      payload_json: { source_id: 'only-in-job-42' },
    }
    const { view } = renderAuthoringPanel({
      activeSubmodule: 'sources',
      ingestionJobs: jobs,
    })

    const summary = screen.getByRole('region', {
      name: 'Active and Attention Ingestion Jobs',
    })
    const detail = screen.getByRole('region', { name: 'Ingestion Job Details' })
    expect(summary.getAttribute('data-slot')).toBe('agent-task-list')
    expect(detail.getAttribute('data-slot')).toBe('filtered-task-table')
    expect(screen.getAllByRole('region', { name: 'Ingestion Job Details' })).toHaveLength(1)

    for (const [status, label] of [
      ['queued', 'Queued'],
      ['running', 'Running'],
      ['failed', 'Failed'],
      ['blocked', 'Blocked'],
      ['dead_letter', 'Dead Letter'],
    ] as const) {
      const row = summary.querySelector(`[data-status="${status}"]`)
      expect(row).not.toBeNull()
      expect(row?.querySelector('[data-slot="badge"]')?.textContent).toBe(label)
      expect(
        row
          ?.querySelector('[data-slot="agent-task-status-icon"]')
          ?.getAttribute('class')
          ?.includes('motion-safe:animate-spin'),
      ).toBe(status === 'running')
    }
    expect(summary.querySelector('[data-status="succeeded"]')).toBeNull()

    for (const [status, label] of [
      ['queued', 'Queued'],
      ['running', 'Running'],
      ['succeeded', 'Succeeded'],
      ['failed', 'Failed'],
      ['blocked', 'Blocked'],
      ['dead_letter', 'Dead Letter'],
    ] as const) {
      expect(detail.querySelector(`[data-job-status="${status}"]`)?.textContent).toBe(label)
    }
    expect(screen.getAllByText('Source only-in-job-42')).toHaveLength(1)
    expect(screen.getAllByText('unique blocked explanation')).toHaveLength(1)
    expect(view.container.querySelector('[data-slot="ingestion-job-groups"]')).toBeTruthy()
  })

  test('bounds the operational summary while retaining every ingestion job in details', () => {
    const jobs = [
      ...Array.from({ length: 8 }, (_, index) =>
        ingestionJobWithStatus(index % 2 === 0 ? 'running' : 'queued', `active-${index}`),
      ),
      ingestionJobWithStatus('succeeded', 'history-1'),
      ingestionJobWithStatus('succeeded', 'history-2'),
    ]
    renderAuthoringPanel({ activeSubmodule: 'sources', ingestionJobs: jobs })

    const summary = screen.getByRole('region', {
      name: 'Active and Attention Ingestion Jobs',
    })
    const detail = screen.getByRole('region', { name: 'Ingestion Job Details' })
    expect(summary.querySelectorAll('[data-slot="agent-task-row"]')).toHaveLength(5)
    expect(detail.querySelectorAll('tbody tr')).toHaveLength(10)
  })

  test('resets a vanished ingestion filter to All without reactivating it later', async () => {
    const userDriver = userEvent.setup()
    const blocked = ingestionJobWithStatus('blocked')
    const running = ingestionJobWithStatus('running')
    const { props, view } = renderAuthoringPanel({
      activeSubmodule: 'sources',
      ingestionJobs: [blocked, running],
    })

    let detail = screen.getByRole('region', { name: 'Ingestion Job Details' })
    await userDriver.click(within(detail).getByRole('button', { name: 'Blocked' }))
    expect(within(detail).getByRole('button', { name: 'Blocked' }).getAttribute('aria-pressed')).toBe(
      'true',
    )

    view.rerender(<AuthoringPanel {...props} ingestionJobs={[running]} />)
    detail = screen.getByRole('region', { name: 'Ingestion Job Details' })
    expect(within(detail).getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe(
      'true',
    )

    view.rerender(<AuthoringPanel {...props} ingestionJobs={[running, blocked]} />)
    detail = screen.getByRole('region', { name: 'Ingestion Job Details' })
    expect(within(detail).getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(
      within(detail).getByRole('button', { name: 'Blocked' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })

  test('binary source upload shows idle and selected file status', async () => {
    const userDriver = userEvent.setup()
    const idle = renderAuthoringPanel({
      activeSubmodule: 'sources',
      sourceType: 'pdf',
    })
    const status = idle.view.container.querySelector(
      '[data-slot="source-file-status"]',
    )
    expect(status?.textContent).toBe('No File Selected.')
    expect(screen.getByLabelText('File').getAttribute('type')).toBe('file')
    expect(screen.getByLabelText('File').className).toMatch(/min-h-9/)
    idle.view.unmount()

    const onSourceFileChange = vi.fn()
    renderAuthoringPanel({
      activeSubmodule: 'sources',
      onSourceFileChange,
      sourceFileName: 'handbook.pdf',
      sourceType: 'pdf',
    })
    expect(
      screen.getByText(/Selected: handbook\.pdf/).getAttribute('data-slot'),
    ).toBe('source-file-status')
    await userDriver.click(
      screen.getByRole('button', { name: 'Clear Selected File' }),
    )
    expect(onSourceFileChange).toHaveBeenCalledWith(null)
  })
})
