import { type FormEvent, type ReactNode, useState } from 'react'

import {
  AgentTaskList,
  ApprovalPrompt,
  ChangeTable,
  CommandSearch,
  FilteredTaskTable,
  LoadingGrid,
  RecommendationPanel,
  RecordsGrid,
  type AgentTaskStatus,
  type RecordsGridColumn,
} from '@/components/beautiful-ui'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button, ButtonLabel } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldHelp, FieldLabel } from '@/components/ui/field'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import { Select } from '@/components/ui/select'
import type {
  IngestionJob,
  IngestionRunResponse,
  KnowledgeProposal,
  Workspace,
  Source,
} from '@/lib/apiClient'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type AuthoringSubmodule = 'workspaces' | 'knowledge' | 'sources'

export type AuthoringPanelProps = {
  activeSubmodule: AuthoringSubmodule
  canCreateWorkspace: boolean
  canDeleteSource: boolean
  canDeleteWorkspace: boolean
  ingestionError: string | null
  ingestionJobs: IngestionJob[]
  ingestionRun: IngestionRunResponse | null
  ingestionState: RequestState
  knowledgeProposals: KnowledgeProposal[]
  knowledgeReviewError: string | null
  knowledgeReviewState: RequestState
  onCreateWorkspace(event: FormEvent<HTMLFormElement>): void
  onCreateSource(event: FormEvent<HTMLFormElement>): void
  onDeleteWorkspace(workspace: Workspace): void
  onDeleteSource(source: Source): void
  onEnqueueIngestion(source: Source): void
  onApproveKnowledgeProposal(proposal: KnowledgeProposal): void
  onWorkspaceIdChange(value: string): void
  onWorkspaceNameChange(value: string): void
  onProposalDraftChange(proposalId: string, value: string): void
  onProposalRejectReasonChange(proposalId: string, value: string): void
  onRefreshIngestionJobs(): void
  onRefreshKnowledgeProposals(): void
  onRefreshSources(): void
  onRefineKnowledgeProposal(proposal: KnowledgeProposal): void
  onRejectKnowledgeProposal(proposal: KnowledgeProposal): void
  onRetryIngestionJob(job: IngestionJob): void
  onRunNextIngestion(): void
  onSelectWorkspace(workspace: Workspace): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceFileChange(file: File | null): void
  onSourceTagsChange(value: string): void
  onSourceTypeChange(value: string): void
  workspaceError: string | null
  workspaceId: string
  workspaceName: string
  workspaceState: RequestState
  workspaces: Workspace[]
  proposalDrafts: Record<string, string>
  proposalRejectReasons: Record<string, string>
  sourceContent: string
  sourceError: string | null
  sourceExternalId: string
  sourceFileName: string
  sourceState: RequestState
  sourceTags: string
  sourceType: string
  sources: Source[]
}

export function AuthoringPanel({
  activeSubmodule,
  canCreateWorkspace,
  canDeleteSource,
  canDeleteWorkspace,
  ingestionError,
  ingestionJobs,
  ingestionRun,
  ingestionState,
  knowledgeProposals,
  knowledgeReviewError,
  knowledgeReviewState,
  onCreateWorkspace,
  onCreateSource,
  onDeleteWorkspace,
  onDeleteSource,
  onEnqueueIngestion,
  onApproveKnowledgeProposal,
  onWorkspaceIdChange,
  onWorkspaceNameChange,
  onProposalDraftChange,
  onProposalRejectReasonChange,
  onRefreshIngestionJobs,
  onRefreshKnowledgeProposals,
  onRefreshSources,
  onRefineKnowledgeProposal,
  onRejectKnowledgeProposal,
  onRetryIngestionJob,
  onRunNextIngestion,
  onSelectWorkspace,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceFileChange,
  onSourceTagsChange,
  onSourceTypeChange,
  workspaceError,
  workspaceId,
  workspaceName,
  workspaceState,
  workspaces,
  proposalDrafts,
  proposalRejectReasons,
  sourceContent,
  sourceError,
  sourceExternalId,
  sourceFileName,
  sourceState,
  sourceTags,
  sourceType,
  sources,
}: AuthoringPanelProps) {
  const isWorkspaceBusy = workspaceState === 'loading'
  const isSourceBusy = sourceState === 'loading'
  const isIngestionBusy = ingestionState === 'loading'
  const isKnowledgeReviewBusy = knowledgeReviewState === 'loading'

  return (
    <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0 max-[680px]:p-0">
      {activeSubmodule === 'workspaces' ? (
        <WorkspacesPanel
          canCreateWorkspace={canCreateWorkspace}
          canDeleteWorkspace={canDeleteWorkspace}
          error={workspaceError}
          isBusy={isWorkspaceBusy}
          onCreateWorkspace={onCreateWorkspace}
          onDeleteWorkspace={onDeleteWorkspace}
          onWorkspaceNameChange={onWorkspaceNameChange}
          onSelectWorkspace={onSelectWorkspace}
          workspaceId={workspaceId}
          workspaceName={workspaceName}
          workspaces={workspaces}
          state={workspaceState}
        />
      ) : null}

      {activeSubmodule === 'sources' ? (
        <>
          <SourcesPanel
            canDeleteSource={canDeleteSource}
            error={sourceError}
            isBusy={isSourceBusy}
            onCreateSource={onCreateSource}
            onDeleteSource={onDeleteSource}
            onEnqueueIngestion={onEnqueueIngestion}
            onWorkspaceIdChange={onWorkspaceIdChange}
            onRefreshSources={onRefreshSources}
            onSourceContentChange={onSourceContentChange}
            onSourceExternalIdChange={onSourceExternalIdChange}
            onSourceFileChange={onSourceFileChange}
            onSourceTagsChange={onSourceTagsChange}
            onSourceTypeChange={onSourceTypeChange}
            workspaceId={workspaceId}
            sourceContent={sourceContent}
            sourceExternalId={sourceExternalId}
            sourceFileName={sourceFileName}
            sourceState={sourceState}
            sourceTags={sourceTags}
            sourceType={sourceType}
            sources={sources}
          />
          <IngestionJobsPanel
            error={ingestionError}
            isBusy={isIngestionBusy}
            jobs={ingestionJobs}
            onRefresh={onRefreshIngestionJobs}
            onRetry={onRetryIngestionJob}
            onRunNext={onRunNextIngestion}
            run={ingestionRun}
            state={ingestionState}
          />
        </>
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

function AuthoringSectionPanel({
  ariaBusy,
  ariaLabel,
  children,
  description,
  eyebrow,
  id,
  status,
  title,
}: {
  ariaBusy?: boolean
  ariaLabel: string
  children: ReactNode
  description?: ReactNode
  eyebrow: string
  id: string
  status: ReactNode
  title: string
}) {
  return (
    <Panel
      aria-busy={ariaBusy || undefined}
      aria-label={ariaLabel}
      role="region"
    >
      <PanelHeader className="max-[680px]:justify-start max-[680px]:max-w-full max-[680px]:text-left max-[680px]:isolate max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-x-auto max-[680px]:border-b max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary min-w-0 flex-col items-start justify-between gap-3 p-4 sm:flex-row max-[680px]:gap-0 max-[680px]:p-0">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-0">
          <p className="max-[680px]:text-left max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:truncate text-xs font-medium uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:px-0">
            {eyebrow}
          </p>
          <PanelTitle className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" id={id}>{title}</PanelTitle>
          {description ? (
            <PanelDescription className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{description}</PanelDescription>
          ) : null}
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 sm:justify-end max-[680px]:gap-0">
          {status}
        </div>
      </PanelHeader>
      <PanelBody className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:isolate max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:overscroll-contain max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm max-[680px]:overflow-x-auto max-[680px]:border-t max-[680px]:border-primary grid gap-4 p-4 pt-0 max-[680px]:gap-0 max-[680px]:p-0 max-[680px]:pt-0">{children}</PanelBody>
    </Panel>
  )
}

function RequestStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      aria-live="polite"
      className="max-[680px]:min-w-0 max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full break-all max-[680px]:truncate text-left max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      role="status"
      tone={requestStateTone(state)}
    >
      {authoringStatusLabel(state)}
    </StatusBadge>
  )
}

function IngestionStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      aria-live="polite"
      className="max-[680px]:justify-start max-[680px]:min-w-0 max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full min-w-[4.75rem] max-[680px]:min-w-[4rem] justify-center break-all max-[680px]:truncate text-left max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      role="status"
      tone={requestStateTone(state)}
    >
      {ingestionStatusLabel(state)}
    </StatusBadge>
  )
}

function KnowledgeStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      aria-live="polite"
      className="max-[680px]:justify-start max-[680px]:min-w-0 max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full min-w-[4.75rem] max-[680px]:min-w-[4rem] justify-center break-all max-[680px]:truncate text-left max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      role="status"
      tone={requestStateTone(state)}
    >
      {knowledgeStatusLabel(state)}
    </StatusBadge>
  )
}

function requestStateTone(
  state: RequestState,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (state === 'failed') return 'danger'
  if (state === 'succeeded') return 'success'
  if (state === 'loading') return 'warning'
  if (state === 'canceled') return 'neutral'
  return 'neutral'
}

function LoadingListState({ label }: { label: string }) {
  return (
    <div aria-busy="true" data-slot-state="loading">
      <LoadingGrid label={label} variant="dots" />
    </div>
  )
}

function focusAuthoringRecord(kind: 'source' | 'user' | 'workspace', id: string) {
  document.getElementById(`authoring-${kind}-${id}`)?.focus()
}

function AuthoringField({
  children,
  className,
  help,
  id,
  label,
}: {
  children(id: string): ReactNode
  className?: string
  help?: ReactNode
  id: string
  label: string
}) {
  return (
    <Field className={className}>
      <FieldLabel className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
      {help ? <FieldHelp className="max-[680px]:opacity-80 max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" id={`${id}-help`}>{help}</FieldHelp> : null}
    </Field>
  )
}

function WorkspacesPanel({
  canCreateWorkspace,
  canDeleteWorkspace,
  error,
  isBusy,
  onCreateWorkspace,
  onDeleteWorkspace,
  onWorkspaceNameChange,
  onSelectWorkspace,
  workspaceId,
  workspaceName,
  workspaces,
  state,
}: {
  canCreateWorkspace: boolean
  canDeleteWorkspace: boolean
  error: string | null
  isBusy: boolean
  onCreateWorkspace(event: FormEvent<HTMLFormElement>): void
  onDeleteWorkspace(workspace: Workspace): void
  onWorkspaceNameChange(value: string): void
  onSelectWorkspace(workspace: Workspace): void
  workspaceId: string
  workspaceName: string
  workspaces: Workspace[]
  state: RequestState
}) {
  return (
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Workspaces"
      description="Create and Select the Workspace Used by Sources and Ingestion."
      eyebrow="Workspaces"
      id="workspaces-title"
      status={<RequestStatus state={state} />}
      title="Workspaces"
    >
      {canCreateWorkspace ? (
        <form className="grid gap-4 tracking-tight max-[680px]:gap-0 max-[680px]:p-0" onSubmit={onCreateWorkspace}>
        <AuthoringField id="authoring-workspace-name" label="Workspace Name">
          {(fieldId) => (
            <Input
              className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="workspace-name"
              onChange={(event) => onWorkspaceNameChange(event.currentTarget.value)}
              placeholder="Demo"
              value={workspaceName}
            />
          )}
        </AuthoringField>
        <div className="max-[680px]:items-start flex flex-wrap items-center gap-2 max-[680px]:gap-0">
          <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate min-h-9 max-[680px]:min-h-0 max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Creating…"
              idleLabel="Create Workspace"
            />
          </Button>
        </div>
        </form>
      ) : null}

      {error ? <InlineFeedback className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      <WorkspaceList
        activeWorkspaceId={workspaceId}
        canDeleteWorkspace={canDeleteWorkspace}
        isBusy={isBusy}
        onDeleteWorkspace={onDeleteWorkspace}
        onSelectWorkspace={onSelectWorkspace}
        workspaces={workspaces}
      />
    </AuthoringSectionPanel>
  )
}

function workspaceAccessLabel(workspace: Workspace): string {
  if (workspace.deleted_at) return 'Deleted'
  if (workspace.can_access === false) return 'No Access'
  return titleCaseStatus(workspace.access_role ?? workspace.embedding_mode)
}

function WorkspaceList({
  activeWorkspaceId,
  canDeleteWorkspace,
  isBusy,
  onDeleteWorkspace,
  onSelectWorkspace,
  workspaces,
}: {
  activeWorkspaceId: string
  canDeleteWorkspace: boolean
  isBusy: boolean
  onDeleteWorkspace(workspace: Workspace): void
  onSelectWorkspace(workspace: Workspace): void
  workspaces: Workspace[]
}) {
  if (isBusy && workspaces.length === 0) {
    return <LoadingListState label="Loading Workspaces…" />
  }

  if (workspaces.length === 0) {
    return (
      <EmptyState data-slot-state="empty" role="status">
        <p className="font-medium text-foreground/90">No Workspaces Yet.</p>
        <p className="text-xs text-muted-foreground">
          Create a workspace above to start indexing sources.
        </p>
      </EmptyState>
    )
  }

  const columns: readonly RecordsGridColumn<Workspace>[] = [
    {
      header: 'Workspace',
      id: 'workspace',
      render: (workspace) => {
        const isDeleted = Boolean(workspace.deleted_at)
        return (
          <div
            data-deleted={isDeleted ? '' : undefined}
            id={`authoring-workspace-${workspace.id}`}
            tabIndex={-1}
          >
            <strong
              className={
                isDeleted
                  ? 'break-words text-sm font-semibold text-muted-foreground line-through'
                  : 'break-words text-sm font-semibold'
              }
            >
              {workspace.name}
            </strong>
            <p className="break-all font-mono text-[11px] text-muted-foreground">
              {workspace.id}
            </p>
            {isDeleted ? (
              <p className="text-xs text-muted-foreground">
                Deleted {formatOperatorTimestamp(workspace.deleted_at ?? null)}
              </p>
            ) : null}
          </div>
        )
      },
      sortValue: (workspace) => workspace.name,
    },
    {
      header: 'Access',
      id: 'access',
      render: (workspace) => {
        const canAccess = workspace.can_access !== false
        const isDeleted = Boolean(workspace.deleted_at)
        return (
          <StatusBadge tone={isDeleted ? 'danger' : !canAccess ? 'warning' : 'neutral'}>
            {workspaceAccessLabel(workspace)}
          </StatusBadge>
        )
      },
      sortValue: workspaceAccessLabel,
    },
    {
      header: 'Actions',
      id: 'actions',
      render: (workspace) => {
        const canAccess = workspace.can_access !== false
        const isDeleted = Boolean(workspace.deleted_at)
        return (
          <div className="flex min-w-[12rem] flex-wrap gap-2 max-[680px]:gap-1">
            <Button
              aria-label={`Select ${workspace.name}`}
              aria-pressed={workspace.id === activeWorkspaceId}
              disabled={!canAccess || isDeleted}
              onClick={() => onSelectWorkspace(workspace)}
              size="sm"
              type="button"
              variant="secondary"
            >
              Select
            </Button>
            {canDeleteWorkspace ? (
              <Button
                aria-label={`Delete workspace ${workspace.name}`}
                disabled={isBusy || !canAccess || isDeleted}
                onClick={() => onDeleteWorkspace(workspace)}
                size="sm"
                type="button"
                variant="danger"
              >
                Delete
              </Button>
            ) : null}
          </div>

        )
      },
    },
  ]

  return (
    <div className="grid gap-3">
      {workspaces.length >= 5 ? (
        <CommandSearch
          emptyLabel="No matching workspaces."
          items={workspaces.map((workspace) => ({
            id: workspace.id,
            label: workspace.name,
            meta: workspace.access_role
              ? titleCaseStatus(workspace.access_role)
              : workspace.can_access === false
                ? 'No Access'
                : undefined,
          }))}
          label="Find Workspaces"
          onSelect={(id) => {
            const selected = workspaces.find((workspace) => workspace.id === id)
            if (!selected) return
            if (selected.can_access !== false && !selected.deleted_at) {
              onSelectWorkspace(selected)
            } else {
              focusAuthoringRecord('workspace', selected.id)
            }
          }}
          placeholder="Search workspaces"
        />
      ) : null}
      <RecordsGrid
        columns={columns}
        emptyLabel="No Workspaces Yet."
        label="Workspaces"
        rows={workspaces}
      />
    </div>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function SourceFileField({
  fieldId,
  isBusy,
  onSourceFileChange,
  sourceFileName,
  sourceType,
}: {
  fieldId: string
  isBusy: boolean
  onSourceFileChange(file: File | null): void
  sourceFileName: string
  sourceType: string
}) {
  const [sizeBytes, setSizeBytes] = useState<number | null>(null)
  // Remount the file input when the parent clears the selection so we do not
  // need a setState-in-effect to reset the native value.
  const inputKey = sourceFileName.length === 0 ? 'empty' : sourceFileName
  const displaySizeBytes = sourceFileName.length === 0 ? null : sizeBytes

  return (
    <div className="min-w-0 grid gap-2 max-[680px]:gap-0">
      <Input
        key={inputKey}
        accept={
          sourceType === 'pdf'
            ? 'application/pdf,.pdf'
            : '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        aria-describedby={`${fieldId}-file-help`}
        className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden h-auto min-h-9 py-1.5 file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1 file:text-sm file:font-medium max-[680px]:min-h-11 max-[680px]:py-1 max-[680px]:file:mr-2 max-[680px]:file:px-2 max-[680px]:file:py-0.5 max-[680px]:file:rounded-sm max-[680px]:file:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
        disabled={isBusy}
        id={fieldId}
        name="source-file"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0] ?? null
          setSizeBytes(file?.size ?? null)
          onSourceFileChange(file)
        }}
        type="file"
      />
      {sourceFileName.length > 0 ? (
        <div className="max-[680px]:items-start flex flex-wrap items-center gap-2 max-[680px]:gap-0">
          <span
            className="max-[680px]:text-left text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
            data-slot="source-file-status"
            id={`${fieldId}-file-help`}
            role="status"
          >
            Selected: {sourceFileName}
            {displaySizeBytes !== null
              ? ` · ${formatFileSize(displaySizeBytes)}`
              : null}
          </span>
          <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
            aria-label="Clear Selected File"
            disabled={isBusy}
            onClick={() => {
              setSizeBytes(null)
              onSourceFileChange(null)
            }}
            size="sm"
            type="button"
            variant="ghost"
          >
            Clear
          </Button>
        </div>
      ) : (
        <span
          className="max-[680px]:text-left text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
          data-slot="source-file-status"
          id={`${fieldId}-file-help`}
          role="status"
        >
          No File Selected.
        </span>
      )}
    </div>
  )
}

function isBinarySourceType(sourceType: string): boolean {
  return sourceType === 'pdf' || sourceType === 'docx'
}

function isTextSourceType(sourceType: string): boolean {
  return sourceType === 'markdown' || sourceType === 'text' || sourceType === 'txt'
}

function SourcesPanel({
  canDeleteSource,
  error,
  isBusy,
  onCreateSource,
  onDeleteSource,
  onEnqueueIngestion,
  onWorkspaceIdChange,
  onRefreshSources,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceFileChange,
  onSourceTagsChange,
  onSourceTypeChange,
  workspaceId,
  sourceContent,
  sourceExternalId,
  sourceFileName,
  sourceState,
  sourceTags,
  sourceType,
  sources,
}: {
  canDeleteSource: boolean
  error: string | null
  isBusy: boolean
  onCreateSource(event: FormEvent<HTMLFormElement>): void
  onDeleteSource(source: Source): void
  onEnqueueIngestion(source: Source): void
  onWorkspaceIdChange(value: string): void
  onRefreshSources(): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceFileChange(file: File | null): void
  onSourceTagsChange(value: string): void
  onSourceTypeChange(value: string): void
  workspaceId: string
  sourceContent: string
  sourceExternalId: string
  sourceFileName: string
  sourceState: RequestState
  sourceTags: string
  sourceType: string
  sources: Source[]
}) {
  const binaryType = isBinarySourceType(sourceType)
  const textType = isTextSourceType(sourceType)
  return (
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Sources"
      description="Register Source Content Before Queueing Ingestion."
      eyebrow="Sources"
      id="sources-title"
      status={<RequestStatus state={sourceState} />}
      title="Content Registry"
    >
      <form className="grid gap-4 tracking-tight max-[680px]:gap-0 max-[680px]:p-0" onSubmit={onCreateSource}>
        <AuthoringField id="authoring-source-workspace-id" label="Workspace ID">
          {(fieldId) => (
            <Input
              className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="authoring-workspace-id"
              onChange={(event) => onWorkspaceIdChange(event.currentTarget.value)}
              placeholder="Workspace UUID"
              value={workspaceId}
            />
          )}
        </AuthoringField>
        <div className="max-[680px]:grid-cols-1 min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0 max-[680px]:p-0 md:grid-cols-2">
          <AuthoringField id="authoring-source-type" label="Source Type">
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                name="source-type"
                onValueChange={onSourceTypeChange}
                options={[
                  { label: 'Markdown', value: 'markdown' },
                  { label: 'Text', value: 'text' },
                  { label: 'Txt', value: 'txt' },
                  { label: 'URL', value: 'url' },
                  { label: 'PDF', value: 'pdf' },
                  { label: 'DOCX', value: 'docx' },
                ]}
                value={sourceType}
              />
            )}
          </AuthoringField>
          <AuthoringField id="authoring-source-external-id" label="External ID">
            {(fieldId) => (
              <Input
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                autoComplete="off"
                id={fieldId}
                name="source-external-id"
                onChange={(event) =>
                  onSourceExternalIdChange(event.currentTarget.value)
                }
                placeholder="Notes.md"
                value={sourceExternalId}
              />
            )}
          </AuthoringField>
        </div>
        {binaryType ? (
          <AuthoringField id="authoring-source-file" label="File">
            {(fieldId) => (
              <SourceFileField
                fieldId={fieldId}
                isBusy={isBusy}
                onSourceFileChange={onSourceFileChange}
                sourceFileName={sourceFileName}
                sourceType={sourceType}
              />
            )}
          </AuthoringField>
        ) : textType ? (
          <AuthoringField id="authoring-source-content" label="Content">
            {(fieldId) => (
              <Textarea
                className="max-[680px]:text-left max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:py-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                name="source-content"
                onChange={(event) => onSourceContentChange(event.currentTarget.value)}
                placeholder="# Notes"
                rows={5}
                value={sourceContent}
              />
            )}
          </AuthoringField>
        ) : (
          <p className="max-[680px]:text-left max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:truncate text-sm text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
            URL sources are fetched during ingestion; no content is required here.
          </p>
        )}
        <AuthoringField id="authoring-source-tags" label="Tags">
          {(fieldId) => (
            <Input
              className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="source-tags"
              onChange={(event) => onSourceTagsChange(event.currentTarget.value)}
              placeholder="Docs, Local"
              value={sourceTags}
            />
          )}
        </AuthoringField>
        <div className="max-[680px]:items-start flex flex-wrap items-center gap-2 max-[680px]:gap-0">
          <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate min-h-9 max-[680px]:min-h-0 max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Creating…"
              idleLabel="Create Source"
            />
          </Button>
          <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
            disabled={isBusy}
            onClick={onRefreshSources}
            type="button"
            variant="secondary"
          >
            <ButtonLabel
              busy={isBusy}
              busyLabel="Refreshing…"
              idleLabel="Refresh Sources"
            />
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      <SourceList
        canDeleteSource={canDeleteSource}
        isBusy={isBusy}
        onDeleteSource={onDeleteSource}
        onEnqueueIngestion={onEnqueueIngestion}
        sources={sources}
      />
    </AuthoringSectionPanel>
  )
}

function SourceList({
  canDeleteSource,
  isBusy,
  onDeleteSource,
  onEnqueueIngestion,
  sources,
}: {
  canDeleteSource: boolean
  isBusy: boolean
  onDeleteSource(source: Source): void
  onEnqueueIngestion(source: Source): void
  sources: Source[]
}) {
  if (isBusy && sources.length === 0) {
    return <LoadingListState label="Loading Sources…" />
  }

  if (sources.length === 0) {
    return (
      <EmptyState data-slot-state="empty" role="status">
        <p className="font-medium text-foreground/90">No Sources Yet.</p>
        <p className="text-xs text-muted-foreground">
          Create a source above, then queue ingestion.
        </p>
      </EmptyState>
    )
  }

  const columns: readonly RecordsGridColumn<Source>[] = [
    {
      header: 'Source',
      id: 'source',
      render: (source) => {
        const isDeleted = Boolean(source.deleted_at)
        return (
          <div
            data-deleted={isDeleted ? '' : undefined}
            id={`authoring-source-${source.id}`}
            tabIndex={-1}
          >
            <div className="flex flex-wrap items-center gap-2">
              <strong
                className={
                  isDeleted
                    ? 'break-words text-sm font-semibold text-muted-foreground line-through'
                    : 'break-words text-sm font-semibold'
                }
              >
                {source.external_id}
              </strong>
              {isDeleted ? <StatusBadge tone="danger">Deleted</StatusBadge> : null}
            </div>
            <p className="break-all font-mono text-[11px] text-muted-foreground">
              {source.id}
            </p>
            {isDeleted ? (
              <p className="text-xs text-muted-foreground">
                Deleted {formatOperatorTimestamp(source.deleted_at ?? null)}
              </p>
            ) : null}
          </div>
        )
      },
      sortValue: (source) => source.external_id,
    },
    {
      header: 'Type and Tags',
      id: 'metadata',
      render: (source) => {
        const tags =
          Array.isArray(source.tags) && source.tags.length > 0
            ? source.tags.join(', ')
            : 'No Tags'
        return (
          <span className="text-xs text-muted-foreground">
            {sourceTypeLabel(source.source_type)} · {tags}
          </span>

        )
      },
      sortValue: (source) => source.source_type,
    },
    {
      header: 'Actions',
      id: 'actions',
      render: (source) => {
        const isDeleted = Boolean(source.deleted_at)
        return (
          <div className="flex min-w-[10rem] flex-wrap gap-2 max-[680px]:gap-1">
            <Button
              aria-label={`Enqueue ingestion for ${source.external_id}`}
              disabled={isBusy || isDeleted}
              onClick={() => onEnqueueIngestion(source)}
              size="sm"
              type="button"
              variant="secondary"
            >
              Queue
            </Button>
            <Button
              aria-label={`Delete source ${source.external_id}`}
              disabled={isBusy || isDeleted}
              onClick={() => onDeleteSource(source)}
              size="sm"
              type="button"
              variant="danger"
            >
              Delete
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <div className="grid gap-3">
      {sources.length >= 5 ? (
        <CommandSearch
          emptyLabel="No matching sources."
          items={sources.map((source) => ({
            id: source.id,
            label: source.external_id,
            meta: sourceTypeLabel(source.source_type),
          }))}
          label="Find Sources"
          onSelect={(id) => focusAuthoringRecord('source', id)}
          placeholder="Search sources"
        />
      ) : null}
      <RecordsGrid
        columns={columns}
        emptyLabel="No Sources Yet."
        label="Sources"
        rows={sources}
      />
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
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Knowledge"
      description="Review and Refine Pending Knowledge Proposals."
      eyebrow="Knowledge"
      id="knowledge-review-title"
      status={<KnowledgeStatus state={state} />}
      title="Pending Proposals"
    >
      <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-1">
        <Button disabled={isBusy} onClick={onRefresh} type="button" variant="secondary">
          <ButtonLabel
            busy={isBusy}
            busyLabel="Refreshing…"
            idleLabel="Refresh Proposals"
          />
        </Button>
      </div>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      {isBusy && proposals.length === 0 ? (
        <LoadingListState label="Loading Proposals…" />
      ) : state === 'canceled' && proposals.length === 0 ? (
        <EmptyState
          aria-label="Proposals Load Canceled"
          data-slot-state="canceled"
          role="status"
        >
          <p className="font-medium text-foreground/90">Proposals Load Canceled.</p>
          <p className="text-xs text-muted-foreground">
            Refresh Again When Ready to Review Knowledge Drafts.
          </p>
        </EmptyState>
      ) : proposals.length === 0 ? (
        <EmptyState
          aria-label="No Pending Proposals"
          data-slot-state="empty"
          role="status"
        >
          <p className="font-medium text-foreground/90">No Pending Proposals.</p>
          <p className="text-xs text-muted-foreground">
            Refresh After Chat Surfaces a Knowledge Draft for This Workspace.
          </p>
        </EmptyState>
      ) : (
        <div aria-label="Knowledge Proposals" className="grid gap-3">
          {proposals.map((proposal) => {
            const draft = proposalDraftText(drafts, proposal)
            const rejectReason = rejectReasons[proposal.id] ?? ''
            const canReject = rejectReason.trim().length > 0
            const hasChangeComparison =
              proposal.proposed_text.trim().length > 0 && draft.trim().length > 0
            return (
              <div className="grid gap-3" key={proposal.id}>
                <RecommendationPanel
                  acceptLabel={proposalActionLabel('Approve', proposal)}
                  busy={isBusy}
                  description={
                    <div className="grid gap-1">
                      <strong className="break-words text-foreground">
                        {proposal.proposed_text}
                      </strong>
                      <span className="break-all font-mono text-[11px]">
                        {proposal.id}
                      </span>
                      <Badge className="w-fit">
                        {titleCaseStatus(proposal.status)}
                      </Badge>
                    </div>
                  }
                  onAccept={() => onApprove(proposal)}
                  title={`Knowledge Proposal ${proposal.id}`}
                />

                {hasChangeComparison ? (
                  <ChangeTable
                    label={`Changes for Knowledge Proposal ${proposal.id}`}
                    rows={[
                      {
                        field: 'Knowledge text',
                        id: `knowledge-text-${proposal.id}`,
                        original: proposal.proposed_text,
                        proposed: draft,
                      },
                    ]}
                  />
                ) : null}

                <div className="grid gap-4 max-[680px]:gap-2">
                  <AuthoringField
                    id={`proposal-refined-${proposal.id}`}
                    label="Refined Text"
                  >
                    {(fieldId) => (
                      <Textarea
                        id={fieldId}
                        name={`proposal-refined-${proposal.id}`}
                        onChange={(event) =>
                          onDraftChange(proposal.id, event.currentTarget.value)
                        }
                        rows={3}
                        value={draft}
                      />
                    )}
                  </AuthoringField>

                  <ApprovalPrompt
                    busy={isBusy}
                    choices={[
                      {
                        id: 'refine',
                        label: proposalActionLabel('Refine', proposal),
                      },
                    ]}
                    onChoose={(choiceId) => {
                      if (choiceId === 'refine') onRefine(proposal)
                    }}
                    question={`Review Knowledge Proposal ${proposal.id}`}
                  />

                  <AuthoringField
                    id={`proposal-reject-${proposal.id}`}
                    label="Reject Reason"
                  >
                    {(fieldId) => (
                      <Input
                        autoComplete="off"
                        id={fieldId}
                        name={`proposal-reject-${proposal.id}`}
                        onChange={(event) =>
                          onRejectReasonChange(proposal.id, event.currentTarget.value)
                        }
                        placeholder="Reject Reason"
                        value={rejectReason}
                      />
                    )}
                  </AuthoringField>
                  <div>
                    <Button
                      aria-describedby={`proposal-reject-${proposal.id}`}
                      aria-label={proposalActionLabel('Reject', proposal)}
                      disabled={isBusy || !canReject}
                      onClick={() => onReject(proposal)}
                      size="sm"
                      type="button"
                      variant="danger"
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AuthoringSectionPanel>
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
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Ingestion Jobs"
      description="Run Queued Ingestion Work and Retry Blocked Jobs."
      eyebrow="Ingestion"
      id="ingestion-jobs-title"
      status={<IngestionStatus state={state} />}
      title="Jobs"
    >
      <div className="max-[680px]:items-start flex flex-wrap items-center gap-2 max-[680px]:gap-0">
        <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
          variant="secondary"
        >
          <ButtonLabel
            busy={isBusy}
            busyLabel="Refreshing…"
            idleLabel="Refresh Jobs"
          />
        </Button>
        <Button className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={isBusy} onClick={onRunNext} type="button">
          <ButtonLabel
            busy={isBusy}
            busyLabel="Running…"
            idleLabel="Run Next Job"
          />
        </Button>
      </div>

      {error ? <InlineFeedback className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      {run ? (
        <div
          className="grid gap-1 rounded-md border border-border/70 bg-muted/30 px-2.5 py-2 text-xs leading-snug max-[680px]:gap-0 max-[680px]:border-primary max-[680px]:px-0 max-[680px]:py-0 max-[680px]:text-[0.5rem] max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot="ingestion-last-run"
        >
          <div className="max-[680px]:items-start max-[680px]:justify-start flex flex-wrap items-center justify-between gap-x-2 gap-y-1 max-[680px]:gap-x-1 max-[680px]:gap-y-0.5">
            <span className="max-[680px]:text-left max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:truncate font-medium text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">Last Run</span>
            <StatusBadge
              className="max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:self-start max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate w-fit px-1.5 py-0 text-[10px] tabular-nums tracking-wide max-[680px]:px-0 max-[680px]:py-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter max-[680px]:rounded-sm"
              tone={jobTone(run.status)}
            >
              {jobStatusLabel(run.status)}
            </StatusBadge>
          </div>
          <p className="max-[680px]:text-left text-sm leading-snug text-foreground/90 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter">
            {ingestionRunMessage(run)}
          </p>
          {run.error_message ? (
            <InlineFeedback className="max-[680px]:hyphens-none max-[680px]:min-w-0 max-[680px]:max-w-full max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 text-xs max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="danger">
              {operatorSafeMessage(run.error_message)}
            </InlineFeedback>
          ) : null}
        </div>
      ) : null}

      <IngestionJobList isBusy={isBusy} jobs={jobs} onRetry={onRetry} />
    </AuthoringSectionPanel>
  )
}

function IngestionJobList({
  isBusy,
  jobs,
  onRetry,
}: {
  isBusy: boolean
  jobs: IngestionJob[]
  onRetry(job: IngestionJob): void
}) {
  const groups = groupJobsByStatus(jobs)
  const availableStatusKey = [...new Set(jobs.map((job) => job.status))]
    .sort()
    .join('\u0000')
  const [filterState, setFilterState] = useState(() => ({
    activeFilter: 'all',
    availableStatusKey,
  }))
  const activeFilter =
    filterState.availableStatusKey === availableStatusKey ||
    filterState.activeFilter === 'all' ||
    jobs.some((job) => job.status === filterState.activeFilter)
      ? filterState.activeFilter
      : 'all'

  if (filterState.availableStatusKey !== availableStatusKey) {
    setFilterState({ activeFilter, availableStatusKey })
  }

  if (isBusy && jobs.length === 0) {
    return <LoadingListState label="Loading Ingestion Jobs…" />
  }

  if (jobs.length === 0) {
    return (
      <EmptyState data-slot-state="empty" role="status">
        <p className="font-medium text-foreground/90">No Ingestion Jobs Yet.</p>
        <p className="text-xs text-muted-foreground">
          Enqueue a source from the content registry, then run the next job.
        </p>
      </EmptyState>
    )
  }

  const filteredJobs =
    activeFilter === 'all'
      ? jobs
      : jobs.filter((job) => job.status === activeFilter)
  const filters = [
    { id: 'all', label: 'All' },
    ...groups.map((group) => ({
      id: group.status,
      label: jobStatusLabel(group.status),
    })),
  ]
  const columns: readonly RecordsGridColumn<IngestionJob>[] = [
    {
      header: 'Status',
      id: 'status',
      render: (job) => (
        <div data-job-status={job.status}>
          <StatusBadge tone={jobTone(job.status)}>
            {jobStatusLabel(job.status)}
          </StatusBadge>
        </div>
      ),
      sortValue: (job) => job.status,
    },
    {
      header: 'Job',
      id: 'job',
      render: (job) => {
        const sourceId = ingestionJobSourceId(job)
        return (
          <div className="grid min-w-[12rem] gap-1">
            <Badge className="w-fit">{titleCaseStatus(job.job_type)}</Badge>
            {sourceId ? (
              <span className="break-all text-xs text-muted-foreground">
                Source {sourceId}
              </span>
            ) : null}
            <span className="break-all font-mono text-[11px] text-muted-foreground">
              {job.id}
            </span>
          </div>
        )
      },
      sortValue: (job) => job.job_type,
    },
    {
      header: 'Schedule',
      id: 'schedule',
      render: (job) => {
        const runAfter = formatRelativeOperatorTimestamp(job.run_after)
        return (
          <div className="grid min-w-[10rem] gap-1 text-xs text-muted-foreground">
            <span>{formatAttempts(job)}</span>
            <span title={runAfter.absolute}>Run after {runAfter.relative}</span>
            <span>{formatLockState(job)}</span>
          </div>
        )
      },
      sortValue: (job) => job.run_after,
    },
    {
      header: 'Result',
      id: 'result',
      render: (job) =>
        job.last_error ? (
          <InlineFeedback tone="danger">
            {operatorSafeMessage(job.last_error)}
          </InlineFeedback>
        ) : (
          <span className="text-xs text-muted-foreground">No Error</span>
        ),
    },
    {
      header: 'Actions',
      id: 'actions',
      render: (job) =>
        isRetryableIngestionJob(job) ? (
          <Button
            aria-label={`Retry ingestion job ${job.id}`}
            disabled={isBusy}
            onClick={() => onRetry(job)}
            size="sm"
            type="button"
            variant="secondary"
          >
            Retry
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">No Actions</span>
        ),
    },
  ]
  const summaryJobs = groups
    .flatMap((group) => group.jobs)
    .filter(isActiveOrAttentionIngestionJob)
    .slice(0, INGESTION_TASK_SUMMARY_LIMIT)

  return (
    <div className="grid gap-4" data-slot="ingestion-job-groups">
      <AgentTaskList
        emptyLabel="No active or attention ingestion jobs."
        label="Active and Attention Ingestion Jobs"
        tasks={summaryJobs.map((job) => {
          const runAfter = formatRelativeOperatorTimestamp(job.run_after)
          return {
            detail: (
              <div className="grid gap-1">
                <span>
                  {formatAttempts(job)} · Run after {runAfter.relative} ·{' '}
                  {formatLockState(job)}
                </span>
              </div>
            ),
            id: job.id,
            label: titleCaseStatus(job.job_type),
            meta: job.id,
            status: job.status,
            statusLabel: jobStatusLabel(job.status),
          }
        })}
      />
      <FilteredTaskTable
        activeFilter={activeFilter}
        columns={columns}
        emptyLabel="No ingestion jobs match this status."
        filters={filters}
        label="Ingestion Job Details"
        onFilterChange={(nextFilter) =>
          setFilterState({ activeFilter: nextFilter, availableStatusKey })
        }
        rows={filteredJobs}
      />
    </div>
  )
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
  if (state === 'canceled') {
    return 'Canceled'
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
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Ready'
}

function knowledgeStatusLabel(state: RequestState): string {
  if (state === 'loading') {
    return 'Working'
  }
  if (state === 'failed') {
    return 'Error'
  }
  if (state === 'succeeded') {
    return 'Updated'
  }
  if (state === 'canceled') {
    return 'Canceled'
  }
  return 'Ready'
}

function proposalActionLabel(
  action: string,
  proposal: KnowledgeProposal,
): string {
  const snippet = proposal.proposed_text.trim().slice(0, 40)
  const ellipsis = proposal.proposed_text.trim().length > 40 ? '…' : ''
  return `${action} ${snippet}${ellipsis}`
}

function proposalDraftText(
  drafts: Record<string, string>,
  proposal: KnowledgeProposal,
): string {
  return drafts[proposal.id] ?? proposal.refined_text ?? ''
}

function isRetryableIngestionJob(job: IngestionJob): boolean {
  return job.status === 'blocked' || job.status === 'dead_letter'
}

function formatAttempts(job: IngestionJob): string {
  return `Attempt ${job.attempts}/${job.max_attempts}`
}

function formatLockState(job: IngestionJob): string {
  if (job.locked_by === null && job.locked_until === null) {
    return 'Unlocked'
  }
  const until = formatRelativeOperatorTimestamp(job.locked_until)
  if (job.locked_by !== null && job.locked_until !== null) {
    return `Locked by ${job.locked_by} until ${until.relative}`
  }
  if (job.locked_by !== null) {
    return `Locked by ${job.locked_by}`
  }
  return `Locked until ${until.relative}`
}

const JOB_STATUS_ORDER = [
  'running',
  'queued',
  'blocked',
  'dead_letter',
  'failed',
  'succeeded',
  'processed',
  'idle',
] as const

// Keep the operational overview small; the adjacent filtered table owns full history.
const INGESTION_TASK_SUMMARY_LIMIT = 5
const ACTIVE_OR_ATTENTION_INGESTION_STATUSES = new Set<AgentTaskStatus>([
  'blocked',
  'dead_letter',
  'failed',
  'queued',
  'running',
])

function isActiveOrAttentionIngestionJob(
  job: IngestionJob,
): job is IngestionJob & { status: AgentTaskStatus } {
  return ACTIVE_OR_ATTENTION_INGESTION_STATUSES.has(job.status as AgentTaskStatus)
}

function groupJobsByStatus(
  jobs: IngestionJob[],
): { jobs: IngestionJob[]; status: string }[] {
  const buckets = new Map<string, IngestionJob[]>()
  for (const job of jobs) {
    const list = buckets.get(job.status) ?? []
    list.push(job)
    buckets.set(job.status, list)
  }
  const ordered: { jobs: IngestionJob[]; status: string }[] = []
  for (const status of JOB_STATUS_ORDER) {
    const group = buckets.get(status)
    if (group !== undefined && group.length > 0) {
      ordered.push({ jobs: group, status })
      buckets.delete(status)
    }
  }
  for (const [status, group] of buckets) {
    ordered.push({ jobs: group, status })
  }
  return ordered
}

function formatOperatorTimestamp(value: string | null): string {
  if (value === null || value.length === 0) {
    return 'Unknown'
  }
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(parsed))
}

function formatRelativeOperatorTimestamp(value: string | null): {
  absolute: string
  relative: string
} {
  const absolute = formatOperatorTimestamp(value)
  if (value === null || value.length === 0) {
    return { absolute, relative: absolute }
  }
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return { absolute, relative: absolute }
  }
  const deltaMs = parsed - Date.now()
  const absMs = Math.abs(deltaMs)
  const minute = 60_000
  const hour = 60 * minute
  const day = 24 * hour
  let relative: string
  if (absMs < minute) {
    relative = deltaMs >= 0 ? 'Now' : 'Just Now'
  } else if (absMs < hour) {
    const n = Math.round(absMs / minute)
    relative = deltaMs >= 0 ? `in ${n}m` : `${n}m ago`
  } else if (absMs < day) {
    const n = Math.round(absMs / hour)
    relative = deltaMs >= 0 ? `in ${n}h` : `${n}h ago`
  } else {
    const n = Math.round(absMs / day)
    relative = deltaMs >= 0 ? `in ${n}d` : `${n}d ago`
  }
  return { absolute, relative }
}

function jobStatusLabel(status: string): string {
  switch (status) {
    case 'queued':
      return 'Queued'
    case 'running':
      return 'Running'
    case 'processed':
      return 'Processed'
    case 'blocked':
      return 'Blocked'
    case 'dead_letter':
      return 'Dead Letter'
    case 'failed':
      return 'Failed'
    case 'idle':
      return 'Idle'
    default:
      return titleCaseStatus(status)
  }
}

function titleCaseStatus(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function sourceTypeLabel(sourceType: string): string {
  switch (sourceType) {
    case 'markdown':
      return 'Markdown'
    case 'text':
      return 'Text'
    case 'txt':
      return 'Txt'
    case 'url':
      return 'URL'
    case 'pdf':
      return 'PDF'
    case 'docx':
      return 'DOCX'
    default:
      return titleCaseStatus(sourceType)
  }
}

function ingestionJobSourceId(job: IngestionJob): string | null {
  const payload = job.payload_json
  if (payload === null || typeof payload !== 'object') {
    return null
  }
  const sourceId = payload.source_id
  return typeof sourceId === 'string' && sourceId.length > 0 ? sourceId : null
}

function ingestionRunMessage(run: IngestionRunResponse): string {
  if (run.status === 'idle') {
    return 'No Ingestion Job Was Processed.'
  }
  if (run.status === 'blocked') {
    return 'The Backend Blocked the Job Before Indexing Completed.'
  }
  if (run.status === 'processed') {
    return run.created_document_version
      ? 'Document Version Was Created.'
      : 'Job Completed Without a New Document Version.'
  }
  return 'Run Result Reported by the Backend.'
}

function jobTone(status: string): 'danger' | 'neutral' | 'success' | 'warning' {
  if (status === 'blocked' || status === 'dead_letter' || status === 'failed') {
    return 'danger'
  }
  if (status === 'processed' || status === 'succeeded') {
    return 'success'
  }
  if (status === 'queued' || status === 'running') {
    return 'warning'
  }
  if (status === 'idle') {
    return 'neutral'
  }
  return 'neutral'
}
