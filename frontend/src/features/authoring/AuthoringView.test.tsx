/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

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
    onRunNextIngestion: vi.fn(),
    onSaveProjectMembership: vi.fn(noopSubmit),
    onSelectProject: vi.fn(),
    onSourceContentChange: vi.fn(),
    onSourceExternalIdChange: vi.fn(),
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

  test('users submodule keeps form labels addressable and uses selects', () => {
    const { view } = renderAuthoringPanel({ activeSubmodule: 'users' })

    expect(screen.getByLabelText('User login').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Display name').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('System role').getAttribute('data-slot')).toBe(
      'native-select',
    )
    expect(screen.getByLabelText('Project role').getAttribute('data-slot')).toBe(
      'native-select',
    )
    expect(screen.getAllByText(user.id).length).toBeGreaterThanOrEqual(1)
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('knowledge submodule renders proposal actions through tokenized controls', () => {
    const { view } = renderAuthoringPanel({ activeSubmodule: 'knowledge' })

    expect(screen.getByLabelText('Refined text').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(screen.getByDisplayValue('Existing refined text.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refine proposal' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Approve proposal' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reject proposal' })).toBeTruthy()
    expectNoLegacyAuthoringClasses(view.container)
  })

  test('sources submodule exposes ingestion operations and metadata', () => {
    const { view } = renderAuthoringPanel({ activeSubmodule: 'sources' })

    expect(screen.getByLabelText('Project ID').getAttribute('data-slot')).toBe(
      'input',
    )
    expect(screen.getByLabelText('Source type').getAttribute('data-slot')).toBe(
      'native-select',
    )
    expect(screen.getByLabelText('Content').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(
      screen.getByRole('button', { name: 'Enqueue ingestion for notes.md' }),
    ).toBeTruthy()
    expect(screen.getByText('attempt 1 of 3')).toBeTruthy()
    expect(screen.getByText('No ingestion job was processed.')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: 'Retry ingestion job job-1' }),
    ).toBeTruthy()
    expectNoLegacyAuthoringClasses(view.container)
  })
})
