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
  Workspace,
  Source,
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

function noopSubmit(event: React.FormEvent<HTMLFormElement>) {
  event.preventDefault()
}

function renderAuthoringPanel(
  overrides: Partial<React.ComponentProps<typeof AuthoringPanel>> = {},
) {
  const props: React.ComponentProps<typeof AuthoringPanel> = {
    activeSubmodule: 'workspaces',
    canCreateWorkspace: true,
    canDeleteSource: true,
    canDeleteWorkspace: true,
    ingestionError: null,
    ingestionJobs: [ingestionJob],
    ingestionRun,
    ingestionState: 'idle',
    knowledgeProposals: [proposal],
    knowledgeReviewError: null,
    knowledgeReviewState: 'idle',
    onApproveKnowledgeProposal: vi.fn(),
    onCreateWorkspace: vi.fn(noopSubmit),
    onCreateSource: vi.fn(noopSubmit),
    onDeleteWorkspace: vi.fn(),
    onDeleteSource: vi.fn(),
    onEnqueueIngestion: vi.fn(),
    onWorkspaceIdChange: vi.fn(),
    onWorkspaceNameChange: vi.fn(),
    onProposalDraftChange: vi.fn(),
    onProposalRejectReasonChange: vi.fn(),
    onRefreshIngestionJobs: vi.fn(),
    onRefreshKnowledgeProposals: vi.fn(),
    onRefreshSources: vi.fn(),
    onRefineKnowledgeProposal: vi.fn(),
    onRejectKnowledgeProposal: vi.fn(),
    onRetryIngestionJob: vi.fn(),
    onRunNextIngestion: vi.fn(),
    onSelectWorkspace: vi.fn(),
    onSourceContentChange: vi.fn(),
    onSourceExternalIdChange: vi.fn(),
    onSourceFileChange: vi.fn(),
    onSourceTagsChange: vi.fn(),
    onSourceTypeChange: vi.fn(),
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
      view.container.querySelectorAll('[data-slot="data-list-item"]').length,
    ).toBe(2)
    expectNoLegacyAuthoringClasses(view.container)

    await userDriver.click(screen.getByRole('button', { name: 'Select Demo' }))
    expect(props.onSelectWorkspace).toHaveBeenCalledWith(workspace)
    expect(
      screen.getByRole('button', { name: 'Select Restricted' }).getAttribute(
        'disabled',
      ),
    ).not.toBeNull()
  })

  test('workspace list shows loading instead of empty while busy', () => {
    const { view } = renderAuthoringPanel({
      activeSubmodule: 'workspaces',
      workspaceState: 'loading',
      workspaces: [],
    })

    expect(screen.queryByText('No Workspaces Yet.')).toBeNull()
    const loadingState = view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="loading"]',
    )
    expect(loadingState).toBeTruthy()
    expect(loadingState?.textContent).toContain('Loading Workspaces')
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
    expect(loadingState?.className).toMatch(/motion-safe:animate-pulse/)
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

  test('Title Case soft-delete badges keep full contrast', () => {
    const deletedSource: Source = {
      ...source,
      deleted_at: '2026-06-22T12:00:00Z',
      external_id: 'gone-source',
      id: 'source-deleted',
    }
    renderAuthoringPanel({
      activeSubmodule: 'sources',
      sources: [deletedSource],
    })
    expect(screen.getByText('Deleted').getAttribute('data-tone')).toBe('danger')
    expect(screen.getByText(/Deleted /)).toBeTruthy()
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
