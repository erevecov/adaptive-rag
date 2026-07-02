import { type FormEvent, type ReactNode } from 'react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, NativeSelect, Textarea } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldLabel } from '@/components/ui/field'
import {
  Panel,
  PanelBody,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from '@/components/ui/panel'
import type {
  IngestionJob,
  IngestionRunResponse,
  KnowledgeProposal,
  Project,
  ProjectMembership,
  Source,
  User,
} from '@/lib/apiClient'

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
}: AuthoringPanelProps) {
  const isProjectBusy = projectState === 'loading'
  const isSourceBusy = sourceState === 'loading'
  const isIngestionBusy = ingestionState === 'loading'
  const isAccessBusy = accessState === 'loading'
  const isKnowledgeReviewBusy = knowledgeReviewState === 'loading'

  return (
    <div className="grid gap-4">
      {activeSubmodule === 'projects' ? (
        <ProjectsPanel
          error={projectError}
          isBusy={isProjectBusy}
          onCreateProject={onCreateProject}
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
        <>
          <SourcesPanel
            error={sourceError}
            isBusy={isSourceBusy}
            onCreateSource={onCreateSource}
            onEnqueueIngestion={onEnqueueIngestion}
            onProjectIdChange={onProjectIdChange}
            onRefreshSources={onRefreshSources}
            onSourceContentChange={onSourceContentChange}
            onSourceExternalIdChange={onSourceExternalIdChange}
            onSourceTagsChange={onSourceTagsChange}
            onSourceTypeChange={onSourceTypeChange}
            projectId={projectId}
            sourceContent={sourceContent}
            sourceExternalId={sourceExternalId}
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
  ariaLabel,
  children,
  description,
  eyebrow,
  id,
  status,
  title,
}: {
  ariaLabel: string
  children: ReactNode
  description?: ReactNode
  eyebrow: string
  id: string
  status: ReactNode
  title: string
}) {
  return (
    <Panel aria-label={ariaLabel} role="region">
      <PanelHeader className="min-w-0 flex-col items-start justify-between gap-3 p-4 sm:flex-row">
        <div className="grid min-w-0 gap-1">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            {eyebrow}
          </p>
          <PanelTitle id={id}>{title}</PanelTitle>
          {description ? (
            <PanelDescription>{description}</PanelDescription>
          ) : null}
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 sm:justify-end">
          {status}
        </div>
      </PanelHeader>
      <PanelBody className="grid gap-4 p-4 pt-0">{children}</PanelBody>
    </Panel>
  )
}

function RequestStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      className="max-w-full break-all text-left"
      tone={requestStateTone(state)}
    >
      {authoringStatusLabel(state)}
    </StatusBadge>
  )
}

function IngestionStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      className="max-w-full break-all text-left"
      tone={requestStateTone(state)}
    >
      {ingestionStatusLabel(state)}
    </StatusBadge>
  )
}

function requestStateTone(
  state: RequestState,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (state === 'failed') return 'danger'
  if (state === 'succeeded') return 'success'
  if (state === 'loading' || state === 'canceled') return 'warning'
  return 'neutral'
}

function AuthoringField({
  children,
  className,
  id,
  label,
}: {
  children(id: string): ReactNode
  className?: string
  id: string
  label: string
}) {
  return (
    <Field className={className}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
    </Field>
  )
}

function ProjectsPanel({
  error,
  isBusy,
  onCreateProject,
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
  onProjectNameChange(value: string): void
  onSelectProject(project: Project): void
  projectId: string
  projectName: string
  projects: Project[]
  state: RequestState
}) {
  return (
    <AuthoringSectionPanel
      ariaLabel="Authoring projects"
      description="Create projects and choose the active workspace."
      eyebrow="Projects"
      id="projects-title"
      status={<RequestStatus state={state} />}
      title="Authoring"
    >
      <form className="grid gap-3" onSubmit={onCreateProject}>
        <AuthoringField id="authoring-project-name" label="Project name">
          {(fieldId) => (
            <Input
              autoComplete="off"
              id={fieldId}
              name="project-name"
              onChange={(event) => onProjectNameChange(event.currentTarget.value)}
              placeholder="Demo"
              value={projectName}
            />
          )}
        </AuthoringField>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Creating...' : 'Create project'}
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      <ProjectList
        activeProjectId={projectId}
        onSelectProject={onSelectProject}
        projects={projects}
      />
    </AuthoringSectionPanel>
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
    return <EmptyState>No projects loaded.</EmptyState>
  }

  return (
    <DataList aria-label="Projects">
      {projects.map((project) => {
        const canAccess = project.can_access !== false
        const roleLabel = canAccess
          ? (project.access_role ?? project.embedding_mode)
          : 'no access'
        return (
          <DataListItem className="p-0" key={project.id}>
            <Button
              aria-label={`Select ${project.name}`}
              aria-pressed={project.id === activeProjectId}
              className="h-auto w-full justify-between gap-3 whitespace-normal p-3 text-left"
              disabled={!canAccess}
              onClick={() => onSelectProject(project)}
              variant="ghost"
            >
              <span className="grid min-w-0 gap-1">
                <strong className="break-words text-sm font-semibold">
                  {project.name}
                </strong>
                <small className="break-all text-xs text-muted-foreground">
                  {project.id}
                </small>
              </span>
              <Badge className="shrink-0" tone={canAccess ? 'neutral' : 'warning'}>
                {roleLabel}
              </Badge>
            </Button>
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
    <AuthoringSectionPanel
      ariaLabel="Authoring users"
      description="Create users and assign project membership."
      eyebrow="Users"
      id="project-access-title"
      status={<RequestStatus state={state} />}
      title="Users"
    >
      <form className="grid gap-3" onSubmit={onCreateUser}>
        <div className="grid gap-3 md:grid-cols-2">
          <AuthoringField id="authoring-user-login" label="User login">
            {(fieldId) => (
              <Input
                autoComplete="off"
                id={fieldId}
                name="user-login"
                onChange={(event) => onUserLoginChange(event.currentTarget.value)}
                placeholder="viewer@example.com"
                value={userLogin}
              />
            )}
          </AuthoringField>
          <AuthoringField id="authoring-user-display-name" label="Display name">
            {(fieldId) => (
              <Input
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
        <div className="grid gap-3 md:grid-cols-2">
          <AuthoringField id="authoring-user-system-role" label="System role">
            {(fieldId) => (
              <NativeSelect
                id={fieldId}
                name="user-system-role"
                onChange={(event) =>
                  onUserSystemRoleChange(event.currentTarget.value)
                }
                value={userSystemRole}
              >
                <option value="user">user</option>
                <option value="superadmin">superadmin</option>
              </NativeSelect>
            )}
          </AuthoringField>
          <AuthoringField id="authoring-user-access-token" label="Access token">
            {(fieldId) => (
              <Input
                autoComplete="off"
                id={fieldId}
                name="user-access-token"
                onChange={(event) =>
                  onUserAccessTokenChange(event.currentTarget.value)
                }
                placeholder="token"
                value={userAccessToken}
              />
            )}
          </AuthoringField>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Creating...' : 'Create user'}
          </Button>
          <Button
            disabled={isBusy}
            onClick={onRefresh}
            type="button"
            variant="secondary"
          >
            {isBusy ? 'Refreshing...' : 'Refresh access'}
          </Button>
        </div>
      </form>

      <form className="grid gap-3" onSubmit={onSaveMembership}>
        <div className="grid gap-3 md:grid-cols-2">
          <AuthoringField id="authoring-member-user-id" label="Member user ID">
            {(fieldId) => (
              <Input
                autoComplete="off"
                id={fieldId}
                name="member-user-id"
                onChange={(event) => onMemberUserIdChange(event.currentTarget.value)}
                placeholder="User UUID"
                value={memberUserId}
              />
            )}
          </AuthoringField>
          <AuthoringField id="authoring-member-role" label="Project role">
            {(fieldId) => (
              <NativeSelect
                id={fieldId}
                name="member-role"
                onChange={(event) => onMemberRoleChange(event.currentTarget.value)}
                value={memberRole}
              >
                <option value="viewer">viewer</option>
                <option value="contributor">contributor</option>
                <option value="admin">admin</option>
              </NativeSelect>
            )}
          </AuthoringField>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Saving...' : 'Save membership'}
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      <UserAccessLists memberships={memberships} users={users} />
    </AuthoringSectionPanel>
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
    return <EmptyState>No users or memberships loaded.</EmptyState>
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <DataList aria-label="Users">
        {users.map((user) => (
          <DataListItem className="grid gap-2" key={user.id}>
            <div className="grid min-w-0 gap-1">
              <strong className="break-words text-sm font-semibold">
                {user.login}
              </strong>
              <small className="break-words text-xs text-muted-foreground">
                {user.display_name}
              </small>
              <small className="break-all text-xs text-muted-foreground">
                {user.id}
              </small>
            </div>
            <Badge className="w-fit">{user.system_role}</Badge>
          </DataListItem>
        ))}
      </DataList>
      <DataList aria-label="Project memberships">
        {memberships.map((membership) => (
          <DataListItem className="grid gap-2" key={membership.id}>
            <div className="grid min-w-0 gap-1">
              <strong className="break-all text-sm font-semibold">
                {membership.user_id}
              </strong>
              <small className="break-all text-xs text-muted-foreground">
                {membership.project_id}
              </small>
            </div>
            <Badge className="w-fit">{membership.role}</Badge>
          </DataListItem>
        ))}
      </DataList>
    </div>
  )
}

function SourcesPanel({
  error,
  isBusy,
  onCreateSource,
  onEnqueueIngestion,
  onProjectIdChange,
  onRefreshSources,
  onSourceContentChange,
  onSourceExternalIdChange,
  onSourceTagsChange,
  onSourceTypeChange,
  projectId,
  sourceContent,
  sourceExternalId,
  sourceState,
  sourceTags,
  sourceType,
  sources,
}: {
  error: string | null
  isBusy: boolean
  onCreateSource(event: FormEvent<HTMLFormElement>): void
  onEnqueueIngestion(source: Source): void
  onProjectIdChange(value: string): void
  onRefreshSources(): void
  onSourceContentChange(value: string): void
  onSourceExternalIdChange(value: string): void
  onSourceTagsChange(value: string): void
  onSourceTypeChange(value: string): void
  projectId: string
  sourceContent: string
  sourceExternalId: string
  sourceState: RequestState
  sourceTags: string
  sourceType: string
  sources: Source[]
}) {
  return (
    <AuthoringSectionPanel
      ariaLabel="Authoring sources"
      description="Register source content before queueing ingestion."
      eyebrow="Sources"
      id="sources-title"
      status={<RequestStatus state={sourceState} />}
      title="Content registry"
    >
      <form className="grid gap-3" onSubmit={onCreateSource}>
        <AuthoringField id="authoring-source-project-id" label="Project ID">
          {(fieldId) => (
            <Input
              autoComplete="off"
              id={fieldId}
              name="authoring-project-id"
              onChange={(event) => onProjectIdChange(event.currentTarget.value)}
              placeholder="Project UUID"
              value={projectId}
            />
          )}
        </AuthoringField>
        <div className="grid gap-3 md:grid-cols-2">
          <AuthoringField id="authoring-source-type" label="Source type">
            {(fieldId) => (
              <NativeSelect
                id={fieldId}
                name="source-type"
                onChange={(event) => onSourceTypeChange(event.currentTarget.value)}
                value={sourceType}
              >
                <option value="markdown">markdown</option>
                <option value="text">text</option>
                <option value="txt">txt</option>
                <option value="url">url</option>
              </NativeSelect>
            )}
          </AuthoringField>
          <AuthoringField id="authoring-source-external-id" label="External ID">
            {(fieldId) => (
              <Input
                autoComplete="off"
                id={fieldId}
                name="source-external-id"
                onChange={(event) =>
                  onSourceExternalIdChange(event.currentTarget.value)
                }
                placeholder="notes.md"
                value={sourceExternalId}
              />
            )}
          </AuthoringField>
        </div>
        <AuthoringField id="authoring-source-content" label="Content">
          {(fieldId) => (
            <Textarea
              id={fieldId}
              name="source-content"
              onChange={(event) => onSourceContentChange(event.currentTarget.value)}
              placeholder="# Notes"
              rows={5}
              value={sourceContent}
            />
          )}
        </AuthoringField>
        <AuthoringField id="authoring-source-tags" label="Tags">
          {(fieldId) => (
            <Input
              autoComplete="off"
              id={fieldId}
              name="source-tags"
              onChange={(event) => onSourceTagsChange(event.currentTarget.value)}
              placeholder="docs, local"
              value={sourceTags}
            />
          )}
        </AuthoringField>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Creating...' : 'Create source'}
          </Button>
          <Button
            disabled={isBusy}
            onClick={onRefreshSources}
            type="button"
            variant="secondary"
          >
            {isBusy ? 'Refreshing...' : 'Refresh sources'}
          </Button>
        </div>
      </form>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      <SourceList onEnqueueIngestion={onEnqueueIngestion} sources={sources} />
    </AuthoringSectionPanel>
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
    return <EmptyState>No sources loaded.</EmptyState>
  }

  return (
    <DataList aria-label="Sources">
      {sources.map((source) => (
        <DataListItem
          className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
          key={source.id}
        >
          <div className="grid min-w-0 gap-1">
            <strong className="break-words text-sm font-semibold">
              {source.external_id}
            </strong>
            <small className="break-all text-xs text-muted-foreground">
              {source.id}
            </small>
            <small className="text-xs text-muted-foreground">
              Ready to queue ingestion
            </small>
            <small className="text-xs text-muted-foreground">
              Queue ingestion when this source should be indexed.
            </small>
          </div>
          <DataListItemActions className="justify-start md:justify-end">
            <Badge>{source.source_type}</Badge>
            <Button
              aria-label={`Enqueue ingestion for ${source.external_id}`}
              onClick={() => onEnqueueIngestion(source)}
              size="sm"
              type="button"
              variant="secondary"
            >
              Queue
            </Button>
          </DataListItemActions>
        </DataListItem>
      ))}
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
      ariaLabel="Authoring knowledge"
      description="Review and refine pending knowledge proposals."
      eyebrow="Knowledge"
      id="knowledge-review-title"
      status={<RequestStatus state={state} />}
      title="Pending proposals"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Button
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
          variant="secondary"
        >
          {isBusy ? 'Refreshing...' : 'Refresh proposals'}
        </Button>
      </div>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      {proposals.length === 0 ? (
        <EmptyState>No pending knowledge proposals loaded.</EmptyState>
      ) : (
        <DataList aria-label="Knowledge proposals">
          {proposals.map((proposal) => {
            const draft = proposalDraftText(drafts, proposal)
            return (
              <DataListItem className="grid gap-3" key={proposal.id}>
                <div className="grid min-w-0 gap-1">
                  <strong className="break-words text-sm font-semibold">
                    {proposal.proposed_text}
                  </strong>
                  <small className="break-all text-xs text-muted-foreground">
                    {proposal.id}
                  </small>
                  <Badge className="w-fit">{proposal.status}</Badge>
                </div>
                <div className="grid gap-3">
                  <AuthoringField
                    id={`proposal-refined-${proposal.id}`}
                    label="Refined text"
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
                  <AuthoringField
                    id={`proposal-reject-${proposal.id}`}
                    label="Reject reason"
                  >
                    {(fieldId) => (
                      <Input
                        autoComplete="off"
                        id={fieldId}
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
                    )}
                  </AuthoringField>
                  <DataListItemActions>
                    <Button
                      disabled={isBusy}
                      onClick={() => onRefine(proposal)}
                      type="button"
                      variant="secondary"
                    >
                      Refine proposal
                    </Button>
                    <Button
                      disabled={isBusy}
                      onClick={() => onApprove(proposal)}
                      type="button"
                    >
                      Approve proposal
                    </Button>
                    <Button
                      disabled={isBusy}
                      onClick={() => onReject(proposal)}
                      type="button"
                      variant="secondary"
                    >
                      Reject proposal
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
      ariaLabel="Authoring ingestion jobs"
      description="Run queued ingestion work and retry blocked jobs."
      eyebrow="Ingestion"
      id="ingestion-jobs-title"
      status={<IngestionStatus state={state} />}
      title="Jobs"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Button
          disabled={isBusy}
          onClick={onRefresh}
          type="button"
          variant="secondary"
        >
          Refresh jobs
        </Button>
        <Button disabled={isBusy} onClick={onRunNext} type="button">
          Run next job
        </Button>
      </div>

      {error ? <InlineFeedback tone="danger">{error}</InlineFeedback> : null}

      {run ? (
        <div className="grid gap-1 rounded-md border border-border bg-muted/40 p-3 text-sm">
          <span className="text-muted-foreground">{`Last run ${run.status}`}</span>
          <StatusBadge className="w-fit" tone={jobTone(run.status)}>
            {run.status}
          </StatusBadge>
          <span>{ingestionRunMessage(run)}</span>
          {run.error_message ? (
            <InlineFeedback tone="danger">{run.error_message}</InlineFeedback>
          ) : null}
        </div>
      ) : null}

      <IngestionJobList jobs={jobs} onRetry={onRetry} />
    </AuthoringSectionPanel>
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
    return <EmptyState>No ingestion jobs loaded.</EmptyState>
  }

  return (
    <DataList aria-label="Ingestion jobs">
      {jobs.map((job) => (
        <DataListItem
          className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
          key={job.id}
        >
          <div className="grid min-w-0 gap-1">
            <StatusBadge className="w-fit" tone={jobTone(job.status)}>
              {job.status}
            </StatusBadge>
            <small className="break-all text-xs text-muted-foreground">
              {job.id}
            </small>
            <small className="text-xs text-muted-foreground">
              {formatAttempts(job)}
            </small>
            <small className="break-words text-xs text-muted-foreground">
              {formatRunAfter(job)}
            </small>
            <small className="break-words text-xs text-muted-foreground">
              {formatLockState(job)}
            </small>
            {job.last_error ? (
              <InlineFeedback tone="danger">{job.last_error}</InlineFeedback>
            ) : null}
          </div>
          <DataListItemActions className="justify-start md:justify-end">
            <Badge>{job.job_type}</Badge>
            {isRetryableIngestionJob(job) ? (
              <Button
                aria-label={`Retry ingestion job ${job.id}`}
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
      ))}
    </DataList>
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

function jobTone(status: string): 'danger' | 'neutral' | 'success' | 'warning' {
  if (status === 'blocked' || status === 'dead_letter' || status === 'failed') {
    return 'danger'
  }
  if (status === 'processed' || status === 'succeeded' || status === 'queued') {
    return 'success'
  }
  if (status === 'running' || status === 'idle') {
    return 'warning'
  }
  return 'neutral'
}
