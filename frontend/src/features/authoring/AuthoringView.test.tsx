/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { installPointerEventMocks } from '@/test/pointerEvents'
import { chooseRadixSelectOption } from '@/test/radixSelect'
import type {
  IngestionJob,
  IngestionRunResponse,
  KnowledgeProposal,
  Project,
  ProjectMembership,
  Source,
  User,
} from '@/lib/apiClient'
import { AuthoringPanel } from './AuthoringView'

installPointerEventMocks()

afterEach(() => {
  cleanup()
})

const project: Project = {
  access_role: 'admin',
  budget_config_json: null,
  can_access: true,
  created_at: '2026-06-22T00:00:00Z',
  embedding_mode: 'dense',
  id: 'project-1',
  name: 'Demo',
  retrieval_contextualization_enabled: false,
  updated_at: '2026-06-22T00:00:00Z',
}

const restrictedProject: Project = {
  ...project,
  access_role: null,
  can_access: false,
  id: 'project-2',
  name: 'Restricted',
}

const source: Source = {
  created_at: '2026-06-22T00:00:00Z',
  external_id: 'notes.md',
  extra_metadata: null,
  id: 'source-1',
  project_id: project.id,
  source_type: 'markdown',
  tags: ['docs'],
  updated_at: '2026-06-22T00:00:00Z',
}

const user: User = {
  created_at: '2026-06-22T00:00:00Z',
  display_name: 'Viewer User',
  id: 'user-1',
  is_active: true,
  last_project_id: null,
  login: 'viewer@example.com',
  system_role: 'user',
  updated_at: '2026-06-22T00:00:00Z',
}

const membership: ProjectMembership = {
  created_at: '2026-06-22T00:00:00Z',
  id: 'membership-1',
  project_id: project.id,
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
  project_id: project.id,
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
  project_id: project.id,
  run_after: '2026-06-22T00:00:02Z',
  status: 'blocked',
  updated_at: '2026-06-22T00:00:00Z',
}

const ingestionRun: IngestionRunResponse = {
  created_document_version: null,
  document_id: null,
  document_version_id: null,
  error_message: null,
  job_id: null,
  project_id: project.id,
  source_id: null,
  status: 'idle',
  worker_id: 'frontend',
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
    activeSubmodule: 'projects',
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
    onCreateProject: vi.fn(noopSubmit),
    onCreateSource: vi.fn(noopSubmit),
    onCreateUser: vi.fn(noopSubmit),
    onDeactivateUser: vi.fn(),
    onDeleteMembership: vi.fn(),
    onDeleteProject: vi.fn(),
    onDeleteSource: vi.fn(),
    onEnqueueIngestion: vi.fn(),
    onMemberRoleChange: vi.fn(),
    onMemberUserIdChange: vi.fn(),
    onProjectIdChange: vi.fn(),
    onProjectNameChange: vi.fn(),
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
    onSaveProjectMembership: vi.fn(noopSubmit),
    onSelectProject: vi.fn(),
    onSourceContentChange: vi.fn(),
    onSourceExternalIdChange: vi.fn(),
    onSourceFileChange: vi.fn(),
    onSourceTagsChange: vi.fn(),
    onSourceTypeChange: vi.fn(),
    onUserAccessTokenChange: vi.fn(),
    onUserDisplayNameChange: vi.fn(),
    onUserLoginChange: vi.fn(),
    onUserSystemRoleChange: vi.fn(),
    projectError: null,
    projectId: project.id,
    projectName: '',
    projectState: 'idle',
    projects: [project, restrictedProject],
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
  test('primary Create buttons keep min-h and stable Creating labels', () => {
    const idle = renderAuthoringPanel({ activeSubmodule: 'projects' })
    const create = screen.getByRole('button', { name: 'Create project' })
    expect(create.className).toMatch(/min-h-9/)
    expect(create.textContent).toContain('Create project')
    idle.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'projects',
      projectState: 'loading',
    })
    const busy = screen.getByRole('button', { name: 'Creating…' })
    expect(busy.className).toMatch(/min-h-9/)
    expect(busy.textContent).toContain('Creating…')
  })

  test('projects submodule uses tokenized panels, controls, and data rows', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel()

    expect(screen.getByLabelText('Project name').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByRole('region', { name: 'Authoring projects' })).toBeTruthy()
    expect(screen.getByText('Ready').getAttribute('data-slot')).toBe('badge')
    expect(
      view.container.querySelector('[data-slot="panel"]'),
    ).toBeTruthy()
    expect(
      view.container.querySelectorAll('[data-slot="data-list-item"]').length,
    ).toBe(2)
    expectNoLegacyAuthoringClasses(view.container)

    await userDriver.click(screen.getByRole('button', { name: 'Select Demo' }))
    expect(props.onSelectProject).toHaveBeenCalledWith(project)
    expect(
      screen.getByRole('button', { name: 'Select Restricted' }).getAttribute(
        'disabled',
      ),
    ).not.toBeNull()
  })

  test('users submodule keeps form labels addressable and uses Radix selects', async () => {
    const userDriver = userEvent.setup()
    const { props, view } = renderAuthoringPanel({ activeSubmodule: 'users' })

    expect(screen.getByLabelText('User login').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Display name').getAttribute('data-slot')).toBe(
      'input',
    )
    const accessToken = screen.getByLabelText('Access token')
    expect(accessToken.getAttribute('data-slot')).toBe('input')
    expect(accessToken.getAttribute('type')).toBe('password')
    expect(accessToken.getAttribute('aria-describedby')).toBe(
      'authoring-user-access-token-help',
    )
    const tokenHelp = screen.getByText('Paste once; never shown after save.')
    expect(tokenHelp.getAttribute('data-slot')).toBe('field-help')
    expect(tokenHelp.id).toBe('authoring-user-access-token-help')
    expect(tokenHelp.closest('[data-slot="field-control"]')).toBeNull()
    expect(tokenHelp.closest('[data-slot="field"]')).toBeTruthy()
    expect(screen.getByLabelText('System role').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    expect(screen.getByLabelText('Project role').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    await chooseRadixSelectOption(
      userDriver,
      screen.getByLabelText('System role'),
      'superadmin',
    )
    await chooseRadixSelectOption(
      userDriver,
      screen.getByLabelText('Project role'),
      'admin',
    )
    expect(props.onUserSystemRoleChange).toHaveBeenCalledWith('superadmin')
    expect(props.onMemberRoleChange).toHaveBeenCalledWith('admin')
    expect(screen.getAllByText(user.id).length).toBeGreaterThanOrEqual(1)
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('project list shows loading instead of empty while busy', () => {
    const { view } = renderAuthoringPanel({
      activeSubmodule: 'projects',
      projectState: 'loading',
      projects: [],
    })

    expect(screen.queryByText('No projects yet.')).toBeNull()
    const loadingState = view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="loading"]',
    )
    expect(loadingState).toBeTruthy()
    expect(loadingState?.textContent).toContain('Loading projects')
    view.unmount()
  })

  test('knowledge submodule renders proposal actions through tokenized controls', () => {
    const { view } = renderAuthoringPanel({ activeSubmodule: 'knowledge' })

    expect(screen.getByLabelText('Refined text').getAttribute('data-slot')).toBe(
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

    expect(screen.getByLabelText('Project ID').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Source type').getAttribute('data-slot')).toBe(
      'select-trigger',
    )
    expect(screen.getByLabelText('Content').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(
      screen.getByRole('button', { name: 'Enqueue ingestion for notes.md' }),
    ).toBeTruthy()
    expect(screen.getByText('attempt 1/3')).toBeTruthy()
    expect(screen.getByText('No ingestion job was processed.')).toBeTruthy()
    const lastRun = view.container.querySelector(
      '[data-slot="ingestion-last-run"]',
    )
    expect(lastRun).toBeTruthy()
    expect(lastRun?.textContent).toMatch(/Last run/)
    expect(lastRun?.textContent).toMatch(/idle/)
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
      screen.getByLabelText('Source type'),
      'url',
    )
    expect(props.onSourceTypeChange).toHaveBeenCalledWith('url')
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('distinguishes loading lists from empty and canceled status', () => {
    const loading = renderAuthoringPanel({
      activeSubmodule: 'projects',
      projectState: 'loading',
      projects: [],
    })
    expect(screen.getByText('Loading projects…')).toBeTruthy()
    const loadingState = loading.view.container.querySelector(
      '[data-slot-state="loading"]',
    )
    expect(loadingState).toBeTruthy()
    expect(loadingState?.className).toMatch(/motion-safe:animate-pulse/)
    loading.view.unmount()

    renderAuthoringPanel({
      activeSubmodule: 'projects',
      projectState: 'canceled',
      projects: [project],
    })
    expect(screen.getByText('Canceled').getAttribute('data-tone')).toBe(
      'neutral',
    )
  })

  test('shows soft-deleted project timestamp and danger tone', () => {
    const deleted: Project = {
      ...project,
      deleted_at: '2026-06-22T12:00:00Z',
      id: 'project-deleted',
      name: 'Gone',
    }
    renderAuthoringPanel({ projects: [deleted] })
    expect(screen.getByText('Deleted').getAttribute('data-tone')).toBe('danger')
    expect(screen.getByText(/Soft-deleted/)).toBeTruthy()
  })

  test('shows per-column empties when users or memberships are missing', () => {
    renderAuthoringPanel({
      activeSubmodule: 'users',
      memberships: [],
      users: [user],
    })
    expect(screen.getByText('No project memberships yet.')).toBeTruthy()
    expect(screen.getByText(user.login)).toBeTruthy()
    cleanup()

    renderAuthoringPanel({
      activeSubmodule: 'users',
      memberships: [membership],
      users: [],
    })
    expect(screen.getByText('No users yet.')).toBeTruthy()
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
    expect(screen.getByText(/Soft-deleted/)).toBeTruthy()
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
    expect(screen.getAllByText(/run after/).length).toBeGreaterThan(0)
    expect(
      screen.getByRole('button', { name: 'Retry ingestion job job-1' }),
    ).toBeTruthy()
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
    expect(status?.textContent).toBe('No file selected.')
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
      screen.getByRole('button', { name: 'Clear selected file' }),
    )
    expect(onSourceFileChange).toHaveBeenCalledWith(null)
  })
})
