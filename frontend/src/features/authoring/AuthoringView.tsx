import { type FormEvent, type ReactNode, useState } from 'react'

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
  Project,
  ProjectMembership,
  Source,
  User,
} from '@/lib/apiClient'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'

export type RequestState = 'idle' | 'loading' | 'succeeded' | 'failed' | 'canceled'
export type AuthoringSubmodule = 'projects' | 'users' | 'knowledge' | 'sources'

export type AuthoringPanelProps = {
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
  onDeactivateUser(user: User): void
  onDeleteMembership(membership: ProjectMembership): void
  onDeleteProject(project: Project): void
  onDeleteSource(source: Source): void
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
  onRevokeAccessToken(): void
  onRunNextIngestion(): void
  onSaveProjectMembership(event: FormEvent<HTMLFormElement>): void
  onSelectProject(project: Project): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceFileChange(file: File | null): void
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
  sourceFileName: string
  sourceState: RequestState
  sourceTags: string
  sourceType: string
  sources: Source[]
  userAccessToken: string
  userDisplayName: string
  userLogin: string
  userSystemRole: string
  users: User[]
}

export function AuthoringPanel({
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
  onDeactivateUser,
  onDeleteMembership,
  onDeleteProject,
  onDeleteSource,
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
  onRevokeAccessToken,
  onRunNextIngestion,
  onSaveProjectMembership,
  onSelectProject,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceFileChange,
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
  sourceFileName,
  sourceState,
  sourceTags,
  sourceType,
  sources,
  userAccessToken,
  userDisplayName,
  userLogin,
  userSystemRole,
  users,
}: AuthoringPanelProps) {
  const isProjectBusy = projectState === 'loading'
  const isSourceBusy = sourceState === 'loading'
  const isIngestionBusy = ingestionState === 'loading'
  const isAccessBusy = accessState === 'loading'
  const isKnowledgeReviewBusy = knowledgeReviewState === 'loading'

  return (
    <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5">
      {activeSubmodule === 'projects' ? (
        <ProjectsPanel
          error={projectError}
          isBusy={isProjectBusy}
          onCreateProject={onCreateProject}
          onDeleteProject={onDeleteProject}
          onProjectNameChange={onProjectNameChange}
          onSelectProject={onSelectProject}
          projectId={projectId}
          projectName={projectName}
          projects={projects}
          state={projectState}
        />
      ) : null}

      {activeSubmodule === 'users' ? (
        <ProjectAccessPanel
          error={accessError}
          isBusy={isAccessBusy}
          memberRole={memberRole}
          memberUserId={memberUserId}
          memberships={memberships}
          onCreateUser={onCreateUser}
          onDeactivateUser={onDeactivateUser}
          onDeleteMembership={onDeleteMembership}
          onMemberRoleChange={onMemberRoleChange}
          onMemberUserIdChange={onMemberUserIdChange}
          onRefresh={onRefreshAccess}
          onRevokeAccessToken={onRevokeAccessToken}
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
        <>
          <SourcesPanel
            error={sourceError}
            isBusy={isSourceBusy}
            onCreateSource={onCreateSource}
            onDeleteSource={onDeleteSource}
            onEnqueueIngestion={onEnqueueIngestion}
            onProjectIdChange={onProjectIdChange}
            onRefreshSources={onRefreshSources}
            onSourceContentChange={onSourceContentChange}
            onSourceExternalIdChange={onSourceExternalIdChange}
            onSourceFileChange={onSourceFileChange}
            onSourceTagsChange={onSourceTagsChange}
            onSourceTypeChange={onSourceTypeChange}
            projectId={projectId}
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
      <PanelHeader className="max-[680px]:border-b max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary min-w-0 flex-col items-start justify-between gap-3 p-4 sm:flex-row max-[680px]:gap-0.5 max-[680px]:p-0.5">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
          <p className="max-[680px]:truncate text-xs font-medium uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:px-0.5">
            {eyebrow}
          </p>
          <PanelTitle className="max-[680px]:truncate max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" id={id}>{title}</PanelTitle>
          {description ? (
            <PanelDescription className="max-[680px]:truncate max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{description}</PanelDescription>
          ) : null}
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 sm:justify-end max-[680px]:gap-0.5">
          {status}
        </div>
      </PanelHeader>
      <PanelBody className="max-[680px]:border-t max-[680px]:border-primary grid gap-4 p-4 pt-0 max-[680px]:gap-0.5 max-[680px]:p-0.5 max-[680px]:pt-0">{children}</PanelBody>
    </Panel>
  )
}

function RequestStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      aria-live="polite"
      className="max-[680px]:rounded-sm max-w-full break-all max-[680px]:truncate text-left max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
      className="max-[680px]:rounded-sm max-w-full min-w-[4.75rem] max-[680px]:min-w-[4rem] justify-center break-all max-[680px]:truncate text-left max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
      className="max-[680px]:rounded-sm max-w-full min-w-[4.75rem] max-[680px]:min-w-[4rem] justify-center break-all max-[680px]:truncate text-left max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
    <EmptyState
      aria-busy="true"
      aria-label={label}
      className="border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
      data-slot-state="loading"
      role="status"
    >
      <p aria-hidden="true" className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
        {label}
      </p>
    </EmptyState>
  )
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
      <FieldLabel className="max-[680px]:truncate max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
      {help ? <FieldHelp className="max-[680px]:truncate max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" id={`${id}-help`}>{help}</FieldHelp> : null}
    </Field>
  )
}

function ProjectsPanel({
  error,
  isBusy,
  onCreateProject,
  onDeleteProject,
  onProjectNameChange,
  onSelectProject,
  projectId,
  projectName,
  projects,
  state,
}: {
  error: string | null
  isBusy: boolean
  onCreateProject(event: FormEvent<HTMLFormElement>): void
  onDeleteProject(project: Project): void
  onProjectNameChange(value: string): void
  onSelectProject(project: Project): void
  projectId: string
  projectName: string
  projects: Project[]
  state: RequestState
}) {
  return (
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Projects"
      description="Create and Select the Project Used by Sources and Ingestion."
      eyebrow="Projects"
      id="projects-title"
      status={<RequestStatus state={state} />}
      title="Projects"
    >
      <form className="grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5" onSubmit={onCreateProject}>
        <AuthoringField id="authoring-project-name" label="Project Name">
          {(fieldId) => (
            <Input
              className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="project-name"
              onChange={(event) => onProjectNameChange(event.currentTarget.value)}
              placeholder="Demo"
              value={projectName}
            />
          )}
        </AuthoringField>
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
          <Button className="max-[680px]:truncate min-h-9 max-[680px]:min-h-0 max-[680px]:h-6 max-[680px]:w-full max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Creating…"
              idleLabel="Create Project"
            />
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      <ProjectList
        activeProjectId={projectId}
        isBusy={isBusy}
        onDeleteProject={onDeleteProject}
        onSelectProject={onSelectProject}
        projects={projects}
      />
    </AuthoringSectionPanel>
  )
}

function ProjectList({
  activeProjectId,
  isBusy,
  onDeleteProject,
  onSelectProject,
  projects,
}: {
  activeProjectId: string
  isBusy: boolean
  onDeleteProject(project: Project): void
  onSelectProject(project: Project): void
  projects: Project[]
}) {
  if (isBusy && projects.length === 0) {
    return <LoadingListState label="Loading Projects…" />
  }

  if (projects.length === 0) {
    return (
      <EmptyState
        className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="empty"
        role="status"
      >
        <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">No Projects Yet.</p>
        <p className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
          Create a project above to start indexing sources.
        </p>
      </EmptyState>
    )
  }

  return (
    <DataList aria-label="Projects" className="max-[680px]:gap-0.5 max-[680px]:overflow-x-auto">
      {projects.map((project) => {
        const canAccess = project.can_access !== false
        const isDeleted = Boolean(project.deleted_at)
        const roleLabel = isDeleted
          ? 'Deleted'
          : canAccess
            ? titleCaseStatus(project.access_role ?? project.embedding_mode)
            : 'No Access'
        return (
          <DataListItem
            className="max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary p-0 max-[680px]:gap-0.5"
            data-deleted={isDeleted ? '' : undefined}
            key={project.id}
          >
            <div className="flex items-stretch gap-1 p-1 max-[680px]:gap-0.5 max-[680px]:p-0.5">
            <Button
              aria-label={`Select ${project.name}`}
              aria-pressed={project.id === activeProjectId}
              className="max-[680px]:truncate max-[680px]:max-w-full h-auto min-w-0 flex-1 justify-between gap-3 max-[680px]:gap-0.5 whitespace-normal p-3 text-left max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary"
              disabled={!canAccess || isDeleted}
              onClick={() => onSelectProject(project)}
              variant="ghost"
            >
              <span className="max-[680px]:truncate grid min-w-0 gap-1 max-[680px]:gap-0.5">
                <strong
                  className={
                    isDeleted
                      ? 'break-words text-sm font-semibold text-muted-foreground line-through decoration-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter'
                      : 'break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter'
                  }
                >
                  {project.name}
                </strong>
                <small className="max-[680px]:truncate break-all font-mono text-[11px] text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {project.id}
                </small>
                {isDeleted ? (
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                    Deleted{' '}
                    {formatOperatorTimestamp(project.deleted_at ?? null)}
                  </small>
                ) : null}
              </span>
              <StatusBadge
                className="max-[680px]:truncate max-[680px]:rounded-sm shrink-0 max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                tone={isDeleted ? 'danger' : !canAccess ? 'warning' : 'neutral'}
              >
                {roleLabel}
              </StatusBadge>
            </Button>
            <Button
              aria-label={`Delete project ${project.name}`}
              className="max-[680px]:truncate shrink-0 self-center max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
              disabled={isBusy || !canAccess || isDeleted}
              onClick={() => onDeleteProject(project)}
              type="button"
              variant="danger"
            >
              Delete
            </Button>
            </div>
          </DataListItem>
        )
      })}
    </DataList>
  )
}

function ProjectAccessPanel({
  error,
  isBusy,
  memberRole,
  memberUserId,
  memberships,
  onCreateUser,
  onDeactivateUser,
  onDeleteMembership,
  onMemberRoleChange,
  onMemberUserIdChange,
  onRefresh,
  onRevokeAccessToken,
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
  onDeactivateUser(user: User): void
  onDeleteMembership(membership: ProjectMembership): void
  onMemberRoleChange(value: string): void
  onMemberUserIdChange(value: string): void
  onRefresh(): void
  onRevokeAccessToken(): void
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
    <AuthoringSectionPanel
      ariaBusy={isBusy}
      ariaLabel="Authoring Users"
      description="Create Users and Assign Project Membership."
      eyebrow="Users"
      id="project-access-title"
      status={<RequestStatus state={state} />}
      title="Users"
    >
      <form className="grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5" onSubmit={onCreateUser}>
        <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5 md:grid-cols-2">
          <AuthoringField id="authoring-user-login" label="User Login">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                autoComplete="off"
                id={fieldId}
                name="user-login"
                onChange={(event) => onUserLoginChange(event.currentTarget.value)}
                placeholder="viewer@example.com"
                value={userLogin}
              />
            )}
          </AuthoringField>
          <AuthoringField id="authoring-user-display-name" label="Display Name">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                autoComplete="off"
                id={fieldId}
                name="user-display-name"
                onChange={(event) =>
                  onUserDisplayNameChange(event.currentTarget.value)
                }
                placeholder="Viewer User"
                value={userDisplayName}
              />
            )}
          </AuthoringField>
        </div>
        <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5 md:grid-cols-2">
          <AuthoringField id="authoring-user-system-role" label="System Role">
            {(fieldId) => (
              <Select
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                id={fieldId}
                name="user-system-role"
                onValueChange={onUserSystemRoleChange}
                options={[
                  { label: 'User', value: 'user' },
                  { label: 'Superadmin', value: 'superadmin' },
                ]}
                value={userSystemRole}
              />
            )}
          </AuthoringField>
          <AuthoringField
            help="Paste Once; Never Shown After Save."
            id="authoring-user-access-token"
            label="Access Token"
          >
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                aria-describedby={`${fieldId}-help`}
                autoComplete="off"
                id={fieldId}
                name="user-access-token"
                onChange={(event) =>
                  onUserAccessTokenChange(event.currentTarget.value)
                }
                type="password"
                value={userAccessToken}
              />
            )}
          </AuthoringField>
        </div>
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
          <Button className="max-[680px]:truncate min-h-9 max-[680px]:min-h-0 max-[680px]:h-6 max-[680px]:w-full max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Creating…"
              idleLabel="Create User"
            />
          </Button>
          <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
            disabled={isBusy}
            onClick={onRefresh}
            type="button"
            variant="secondary"
          >
            <ButtonLabel
              busy={isBusy}
              busyLabel="Refreshing…"
              idleLabel="Refresh Access"
            />
          </Button>
          <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
            disabled={isBusy || userAccessToken.trim() === ''}
            onClick={onRevokeAccessToken}
            type="button"
            variant="secondary"
          >
            Revoke access token
          </Button>
        </div>
      </form>

      <div className="h-px bg-border" role="separator" />

      <form className="grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5" onSubmit={onSaveMembership}>
        <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5 md:grid-cols-2">
          <AuthoringField id="authoring-member-user-id" label="Member User ID">
            {(fieldId) => (
              <Input
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                autoComplete="off"
                id={fieldId}
                name="member-user-id"
                onChange={(event) => onMemberUserIdChange(event.currentTarget.value)}
                placeholder="User UUID"
                value={memberUserId}
              />
            )}
          </AuthoringField>
          <AuthoringField id="authoring-member-role" label="Project Role">
            {(fieldId) => (
              <Select
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                id={fieldId}
                name="member-role"
                onValueChange={onMemberRoleChange}
                options={[
                  { label: 'Viewer', value: 'viewer' },
                  { label: 'Contributor', value: 'contributor' },
                  { label: 'Admin', value: 'admin' },
                ]}
                value={memberRole}
              />
            )}
          </AuthoringField>
        </div>
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
          <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Saving…"
              idleLabel="Save Membership"
            />
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      <UserAccessLists
        isBusy={isBusy}
        memberships={memberships}
        onDeactivateUser={onDeactivateUser}
        onDeleteMembership={onDeleteMembership}
        users={users}
      />
    </AuthoringSectionPanel>
  )
}

function UserAccessLists({
  isBusy,
  memberships,
  onDeactivateUser,
  onDeleteMembership,
  users,
}: {
  isBusy: boolean
  memberships: ProjectMembership[]
  onDeactivateUser(user: User): void
  onDeleteMembership(membership: ProjectMembership): void
  users: User[]
}) {
  if (isBusy && users.length === 0 && memberships.length === 0) {
    return <LoadingListState label="Loading Users…" />
  }

  if (users.length === 0 && memberships.length === 0) {
    return (
      <EmptyState
        className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="empty"
        role="status"
      >
        No Users or Memberships Yet.
      </EmptyState>
    )
  }

  return (
    <div className="min-w-0 grid gap-3 max-[680px]:gap-0.5 lg:grid-cols-2">
      {users.length === 0 ? (
        <EmptyState
          className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="empty"
          role="status"
        >
          No Users Yet.
        </EmptyState>
      ) : (
        <DataList aria-label="Users" className="max-[680px]:gap-0.5 max-[680px]:overflow-x-auto">
          {users.map((user) => (
            <DataListItem
              className="max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary grid gap-2 max-[680px]:gap-0.5"
              data-inactive={!user.is_active ? '' : undefined}
              key={user.id}
            >
              <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                <strong
                  className={
                    user.is_active
                      ? 'break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug'
                      : 'break-words text-sm font-semibold text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter'
                  }
                >
                  {user.login}
                </strong>
                <small className="max-[680px]:truncate break-words text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {user.display_name}
                </small>
                <small className="max-[680px]:truncate break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {user.id}
                </small>
              </div>
              <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
                <Badge className="max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{titleCaseStatus(user.system_role)}</Badge>
                {!user.is_active ? (
                  <StatusBadge className="max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="warning">
                    Inactive
                  </StatusBadge>
                ) : null}
                <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                  aria-label={`Deactivate user ${user.login}`}
                  disabled={isBusy || !user.is_active}
                  onClick={() => onDeactivateUser(user)}
                  type="button"
                  variant="danger"
                >
                  Deactivate
                </Button>
              </div>
            </DataListItem>
          ))}
        </DataList>
      )}
      {memberships.length === 0 ? (
        <EmptyState
          className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="empty"
          role="status"
        >
          No Project Memberships Yet.
        </EmptyState>
      ) : (
        <DataList aria-label="Project Memberships" className="max-[680px]:gap-0.5 max-[680px]:overflow-x-auto">
          {memberships.map((membership) => (
            <DataListItem className="max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary grid gap-2 max-[680px]:gap-0.5" key={membership.id}>
              <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                <strong className="break-all text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {membership.user_id}
                </strong>
                <small className="max-[680px]:truncate break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                  {membership.project_id}
                </small>
              </div>
              <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
                <Badge className="max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{titleCaseStatus(membership.role)}</Badge>
                <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                  aria-label={`Remove membership ${membership.user_id}`}
                  disabled={isBusy}
                  onClick={() => onDeleteMembership(membership)}
                  type="button"
                  variant="danger"
                >
                  Remove
                </Button>
              </div>
            </DataListItem>
          ))}
        </DataList>
      )}
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
    <div className="min-w-0 grid gap-2 max-[680px]:gap-0.5">
      <Input
        key={inputKey}
        accept={
          sourceType === 'pdf'
            ? 'application/pdf,.pdf'
            : '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        aria-describedby={`${fieldId}-file-help`}
        className="h-auto min-h-9 py-1.5 file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1 file:text-sm file:font-medium max-[680px]:min-h-11 max-[680px]:py-1 max-[680px]:file:mr-2 max-[680px]:file:px-2 max-[680px]:file:py-0.5 max-[680px]:file:rounded-sm max-[680px]:file:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
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
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
          <span
            className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
            data-slot="source-file-status"
            id={`${fieldId}-file-help`}
            role="status"
          >
            Selected: {sourceFileName}
            {displaySizeBytes !== null
              ? ` · ${formatFileSize(displaySizeBytes)}`
              : null}
          </span>
          <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
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
          className="text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
  error,
  isBusy,
  onCreateSource,
  onDeleteSource,
  onEnqueueIngestion,
  onProjectIdChange,
  onRefreshSources,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceFileChange,
  onSourceTagsChange,
  onSourceTypeChange,
  projectId,
  sourceContent,
  sourceExternalId,
  sourceFileName,
  sourceState,
  sourceTags,
  sourceType,
  sources,
}: {
  error: string | null
  isBusy: boolean
  onCreateSource(event: FormEvent<HTMLFormElement>): void
  onDeleteSource(source: Source): void
  onEnqueueIngestion(source: Source): void
  onProjectIdChange(value: string): void
  onRefreshSources(): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceFileChange(file: File | null): void
  onSourceTagsChange(value: string): void
  onSourceTypeChange(value: string): void
  projectId: string
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
      <form className="grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5" onSubmit={onCreateSource}>
        <AuthoringField id="authoring-source-project-id" label="Project ID">
          {(fieldId) => (
            <Input
              className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="authoring-project-id"
              onChange={(event) => onProjectIdChange(event.currentTarget.value)}
              placeholder="Project UUID"
              value={projectId}
            />
          )}
        </AuthoringField>
        <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5 md:grid-cols-2">
          <AuthoringField id="authoring-source-type" label="Source Type">
            {(fieldId) => (
              <Select
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
                className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:py-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
          <p className="max-[680px]:truncate text-sm text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            URL sources are fetched during ingestion; no content is required here.
          </p>
        )}
        <AuthoringField id="authoring-source-tags" label="Tags">
          {(fieldId) => (
            <Input
              className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
              autoComplete="off"
              id={fieldId}
              name="source-tags"
              onChange={(event) => onSourceTagsChange(event.currentTarget.value)}
              placeholder="Docs, Local"
              value={sourceTags}
            />
          )}
        </AuthoringField>
        <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
          <Button className="max-[680px]:truncate min-h-9 max-[680px]:min-h-0 max-[680px]:h-6 max-[680px]:w-full max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isBusy} type="submit">
            <ButtonLabel
              busy={isBusy}
              busyLabel="Creating…"
              idleLabel="Create Source"
            />
          </Button>
          <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
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

      {error ? <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      <SourceList
        isBusy={isBusy}
        onDeleteSource={onDeleteSource}
        onEnqueueIngestion={onEnqueueIngestion}
        sources={sources}
      />
    </AuthoringSectionPanel>
  )
}

function SourceList({
  isBusy,
  onDeleteSource,
  onEnqueueIngestion,
  sources,
}: {
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
      <EmptyState
        className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="empty"
        role="status"
      >
        <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">No Sources Yet.</p>
        <p className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
          Create a source above, then queue ingestion.
        </p>
      </EmptyState>
    )
  }

  return (
    <DataList aria-label="Sources" className="max-[680px]:gap-0.5 max-[680px]:overflow-x-auto">
      {sources.map((source) => {
        const isDeleted = Boolean(source.deleted_at)
        const tags =
          Array.isArray(source.tags) && source.tags.length > 0
            ? source.tags.join(', ')
            : 'No Tags'
        return (
          <DataListItem
            className="grid gap-3 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary md:grid-cols-[minmax(0,1fr)_auto]"
            data-deleted={isDeleted ? '' : undefined}
            key={source.id}
          >
            <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
              <div className="flex min-w-0 flex-wrap items-center gap-2 max-[680px]:gap-0.5">
                <strong
                  className={
                    isDeleted
                      ? 'break-words text-sm font-semibold text-muted-foreground line-through decoration-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter'
                      : 'break-words text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter'
                  }
                >
                  {source.external_id}
                </strong>
                {isDeleted ? (
                  <StatusBadge className="max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">
                    Deleted
                  </StatusBadge>
                ) : null}
              </div>
              <small className="max-[680px]:truncate break-all font-mono text-[11px] text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                {source.id}
              </small>
              <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                {isDeleted
                  ? `Deleted ${formatOperatorTimestamp(source.deleted_at ?? null)}`
                  : `${sourceTypeLabel(source.source_type)} · ${tags}`}
              </small>
            </div>
            <DataListItemActions className="justify-start gap-2 md:justify-end max-[680px]:gap-0.5 max-[680px]:px-0.5">
              <Badge className="max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">{sourceTypeLabel(source.source_type)}</Badge>
              <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                aria-label={`Enqueue ingestion for ${source.external_id}`}
                disabled={isBusy || isDeleted}
                onClick={() => onEnqueueIngestion(source)}
                size="sm"
                type="button"
                variant="secondary"
              >
                Queue
              </Button>
              <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                aria-label={`Delete source ${source.external_id}`}
                disabled={isBusy || isDeleted}
                onClick={() => onDeleteSource(source)}
                size="sm"
                type="button"
                variant="danger"
              >
                Delete
              </Button>
            </DataListItemActions>
          </DataListItem>
        )
      })}
    </DataList>
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
      <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
        <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
          variant="secondary"
        >
          <ButtonLabel
            busy={isBusy}
            busyLabel="Refreshing…"
            idleLabel="Refresh Proposals"
          />
        </Button>
      </div>

      {error ? <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      {isBusy && proposals.length === 0 ? (
        <LoadingListState label="Loading Proposals…" />
      ) : state === 'canceled' && proposals.length === 0 ? (
        <EmptyState
          aria-label="Proposals Load Canceled"
          className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="canceled"
          role="status"
        >
          <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">Proposals Load Canceled.</p>
          <p className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            Refresh Again When Ready to Review Knowledge Drafts.
          </p>
        </EmptyState>
      ) : proposals.length === 0 ? (
        <EmptyState
          aria-label="No Pending Proposals"
          className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="empty"
          role="status"
        >
          <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">No Pending Proposals.</p>
          <p className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
            Refresh After Chat Surfaces a Knowledge Draft for This Project.
          </p>
        </EmptyState>
      ) : (
        <DataList aria-label="Knowledge Proposals" className="max-[680px]:gap-0.5 max-[680px]:overflow-x-auto">
          {proposals.map((proposal) => {
            const draft = proposalDraftText(drafts, proposal)
            const rejectReason = rejectReasons[proposal.id] ?? ''
            const canReject = rejectReason.trim().length > 0
            return (
              <DataListItem className="grid gap-3 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary" key={proposal.id}>
                <div className="grid min-w-0 gap-1 max-[680px]:gap-0.5">
                  <strong className="break-words max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                    {proposal.proposed_text}
                  </strong>
                  <small
                    className="break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                    title={proposal.id}
                  >
                    {proposal.id}
                  </small>
                  <Badge className="max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                    {titleCaseStatus(proposal.status)}
                  </Badge>
                </div>
                <div className="min-w-0 grid gap-4 tracking-tight max-[680px]:gap-0.5 max-[680px]:p-0.5">
                  <AuthoringField
                    id={`proposal-refined-${proposal.id}`}
                    label="Refined Text"
                  >
                    {(fieldId) => (
                      <Textarea
                        className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:py-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
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
                  <AuthoringField
                    id={`proposal-reject-${proposal.id}`}
                    label="Reject Reason"
                  >
                    {(fieldId) => (
                      <Input
                        className="max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                        autoComplete="off"
                        id={fieldId}
                        name={`proposal-reject-${proposal.id}`}
                        onChange={(event) =>
                          onRejectReasonChange(
                            proposal.id,
                            event.currentTarget.value,
                          )
                        }
                        placeholder="Reject Reason"
                        value={rejectReason}
                      />
                    )}
                  </AuthoringField>
                  <DataListItemActions className="max-[680px]:gap-0.5 max-[680px]:px-0.5">
                    <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                      aria-label={proposalActionLabel('Refine', proposal)}
                      disabled={isBusy}
                      onClick={() => onRefine(proposal)}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      Refine
                    </Button>
                    <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                      aria-label={proposalActionLabel('Approve', proposal)}
                      disabled={isBusy}
                      onClick={() => onApprove(proposal)}
                      size="sm"
                      type="button"
                    >
                      Approve
                    </Button>
                    <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
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
                  </DataListItemActions>
                </div>
              </DataListItem>
            )
          })}
        </DataList>
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
      <div className="flex flex-wrap items-center gap-2 max-[680px]:gap-0.5">
        <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
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
        <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug" disabled={isBusy} onClick={onRunNext} type="button">
          <ButtonLabel
            busy={isBusy}
            busyLabel="Running…"
            idleLabel="Run Next Job"
          />
        </Button>
      </div>

      {error ? <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">{error}</InlineFeedback> : null}

      {run ? (
        <div
          className="grid gap-1 rounded-md border border-border/70 bg-muted/30 px-2.5 py-2 text-xs leading-snug max-[680px]:gap-0.5 max-[680px]:border-primary max-[680px]:px-0.5 max-[680px]:py-0.5 max-[680px]:text-[0.5625rem] max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot="ingestion-last-run"
        >
          <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 max-[680px]:gap-x-1 max-[680px]:gap-y-0.5">
            <span className="max-[680px]:truncate font-medium text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">Last Run</span>
            <StatusBadge
              className="max-[680px]:truncate w-fit px-1.5 py-0 text-[10px] tabular-nums tracking-wide max-[680px]:px-0.5 max-[680px]:py-0 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter max-[680px]:rounded-sm"
              tone={jobTone(run.status)}
            >
              {jobStatusLabel(run.status)}
            </StatusBadge>
          </div>
          <p className="text-sm leading-snug text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter">
            {ingestionRunMessage(run)}
          </p>
          {run.error_message ? (
            <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0.5 text-xs max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">
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
  if (isBusy && jobs.length === 0) {
    return <LoadingListState label="Loading Ingestion Jobs…" />
  }

  if (jobs.length === 0) {
    return (
      <EmptyState
        className="max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="empty"
        role="status"
      >
        <p className="font-medium text-foreground/90 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">No Ingestion Jobs Yet.</p>
        <p className="max-[680px]:truncate text-xs leading-relaxed text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
          Enqueue a source from the content registry, then run the next job.
        </p>
      </EmptyState>
    )
  }

  const groups = groupJobsByStatus(jobs)

  return (
    <div className="min-w-0 grid gap-3 max-[680px]:gap-0.5" data-slot="ingestion-job-groups">
      {groups.map((group) => (
        <div className="min-w-0 grid gap-2 max-[680px]:gap-0.5" key={group.status}>
          <p className="max-[680px]:truncate text-xs font-medium uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:px-0.5">
            {jobStatusLabel(group.status)}
            <span className="max-[680px]:truncate ml-1 tabular-nums max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter">({group.jobs.length})</span>
          </p>
          <DataList aria-label={`Ingestion Jobs ${jobStatusLabel(group.status)}`} className="max-[680px]:gap-0.5">
            {group.jobs.map((job) => {
              const isRunning = job.status === 'running'
              const sourceId = ingestionJobSourceId(job)
              const statusLabel = jobStatusLabel(job.status)
              const runAfter = formatRelativeOperatorTimestamp(job.run_after)
              return (
                <DataListItem
                  aria-label={
                    sourceId
                      ? `Ingestion Job ${statusLabel} for Source ${sourceId}`
                      : `Ingestion Job ${statusLabel}`
                  }
                  className="grid gap-3 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0.5 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary md:grid-cols-[minmax(0,1fr)_auto]"
                  data-job-status={job.status}
                  key={job.id}
                >
                  <div className="grid min-w-0 gap-1.5 max-[680px]:gap-0.5">
                    <div className="flex min-w-0 flex-wrap items-center gap-2 max-[680px]:gap-0.5">
                      {isRunning ? (
                        <span
                          aria-hidden="true"
                          className="size-1.5 shrink-0 rounded-full bg-amber-500 motion-safe:animate-pulse"
                          data-slot="ingestion-job-pulse"
                        />
                      ) : null}
                      <StatusBadge className="max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone={jobTone(job.status)}>
                        {statusLabel}
                      </StatusBadge>
                      <Badge className="max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm w-fit max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter">
                        {titleCaseStatus(job.job_type)}
                      </Badge>
                    </div>
                    {sourceId ? (
                      <small
                        className="break-all text-xs text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                        title="Source ID From Job Payload"
                      >
                        Source {sourceId}
                      </small>
                    ) : null}
                    <small
                      className="truncate font-mono text-[11px] text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter"
                      title={job.id}
                    >
                      {truncateId(job.id)}
                    </small>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs tabular-nums text-muted-foreground max-[680px]:gap-x-2 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter">
                      <span>{formatAttempts(job)}</span>
                      <span title={runAfter.absolute}>
                        Run after {runAfter.relative}
                      </span>
                      <span>{formatLockState(job)}</span>
                    </div>
                    {job.last_error ? (
                      <InlineFeedback className="max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0.5 text-xs max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter" tone="danger">
                        {operatorSafeMessage(job.last_error)}
                      </InlineFeedback>
                    ) : null}
                  </div>
                  <DataListItemActions className="justify-start gap-2 md:justify-end max-[680px]:gap-0.5 max-[680px]:px-0.5">
                    {isRetryableIngestionJob(job) ? (
                      <Button className="max-[680px]:truncate max-[680px]:h-6 max-[680px]:w-full max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:leading-snug"
                        aria-label={`Retry ingestion job ${job.id}`}
                        disabled={isBusy}
                        onClick={() => onRetry(job)}
                        size="sm"
                        type="button"
                        variant="secondary"
                      >
                        Retry
                      </Button>
                    ) : null}
                  </DataListItemActions>
                </DataListItem>
              )
            })}
          </DataList>
        </div>
      ))}
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

function truncateId(value: string): string {
  if (value.length <= 12) {
    return value
  }
  return `…${value.slice(-8)}`
}

const JOB_STATUS_ORDER = [
  'running',
  'queued',
  'blocked',
  'dead_letter',
  'failed',
  'processed',
  'idle',
] as const

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
