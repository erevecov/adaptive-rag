import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  useRef,
  useState,
} from 'react'
import { ChevronDown } from 'lucide-react'

import { Badge, StatusBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { Callout, EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldError, FieldHelp, FieldLabel } from '@/components/ui/field'
import { Panel, PanelBody, PanelDescription, PanelHeader } from '@/components/ui/panel'
import * as Popover from '@/components/ui/popover'
import { Select } from '@/components/ui/select'
import type {
  ChatModel,
  ChatRetrievalSettings,
  ProjectRuntimeSettings,
  ProviderConnection,
  ProviderConnectionCheckResponse,
  ProviderModel,
  RuntimeSlotDefault,
} from '@/lib/apiClient'
import { operatorSafeMessage } from '@/lib/operatorSafeMessage'
import {
  CHAT_RETRIEVAL_MAX_LIMIT,
  PROVIDER_CONNECTION_CAPABILITIES,
  RUNTIME_SLOTS,
  connectionOptionLabel,
  connectionTypeLabel,
  connectionsForCapability,
  missingSyncedModelMessage,
  normalizeChatRetrievalLimit,
  providerLabel,
  providerModelOptions,
  runtimeStatusLabel,
  slotLabel,
  titleCaseToken,
  type ProviderModelOption,
  type RequestState,
  type RuntimeSubmodule,
} from './runtimeUi'

export type RuntimeSettingsPanelProps = {
  activeSubmodule: RuntimeSubmodule
  chatConnectionId: string
  chatModelId: string
  chatModels: ChatModel[]
  chatRetrievalSettings: ChatRetrievalSettings | null
  checkingConnectionId: string | null
  connectionApiKey: string
  connectionBaseUrl: string
  connectionCheckResults: Record<string, ProviderConnectionCheckResponse>
  connectionCapabilities: string[]
  connectionProvider: string
  connectionType: string
  connections: ProviderConnection[]
  deleteConnectionConfirmation: string
  deleteConnectionId: string | null
  editingConnectionId: string | null
  error: string | null
  globalChatRerankCandidateLimit: number
  globalChatRerankEnabled: boolean
  globalChatRetrievalLimit: number
  globalSlot: string
  globalSlotConnectionId: string
  globalSlotModelId: string
  onChatConnectionIdChange(value: string): void
  onChatModelIdChange(value: string): void
  onConnectionApiKeyChange(value: string): void
  onConnectionBaseUrlChange(value: string): void
  onConnectionCapabilitiesChange(value: string[]): void
  onConnectionProviderChange(value: string): void
  onConnectionTypeChange(value: string): void
  onCancelDeleteConnection(): void
  onCancelEditConnection(): void
  onCheckConnection(connectionId: string): void
  onDeleteConnection(event: FormEvent<HTMLFormElement>): void
  onDeleteConnectionConfirmationChange(value: string): void
  onGlobalChatRerankCandidateLimitChange(value: number): void
  onGlobalChatRerankEnabledChange(value: boolean): void
  onGlobalChatRetrievalLimitChange(value: number): void
  onGlobalSlotChange(value: string): void
  onGlobalSlotConnectionIdChange(value: string): void
  onGlobalSlotModelIdChange(value: string): void
  onProjectChatRerankCandidateLimitChange(value: number): void
  onProjectChatRerankEnabledChange(value: boolean): void
  onProjectChatRetrievalLimitChange(value: number): void
  onProjectSlotChange(value: string): void
  onProjectSlotConnectionIdChange(value: string): void
  onProjectSlotModelIdChange(value: string): void
  onRefreshGlobalDefaults(): void
  onRefreshModelCatalog(): void
  onRefreshProjectOverrides(): void
  onResetProjectChatRetrieval(): void
  onResetProjectSlot(slot: string): void
  onRequestDeleteConnection(connectionId: string): void
  onRequestEditConnection(connectionId: string): void
  onSaveConnection(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatModel(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalSlot(event: FormEvent<HTMLFormElement>): void
  onSaveProjectChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveProjectOverride(event: FormEvent<HTMLFormElement>): void
  onSyncProviderModels(event: FormEvent<HTMLFormElement>): void
  onModelSyncConnectionIdChange(value: string): void
  modelSyncConnectionId: string
  providerModels: ProviderModel[]
  projectId: string
  projectChatRerankCandidateLimit: number
  projectChatRerankEnabled: boolean
  projectChatRetrievalLimit: number
  projectRuntimeSettings: ProjectRuntimeSettings | null
  projectSlot: string
  projectSlotConnectionId: string
  projectSlotModelId: string
  slots: RuntimeSlotDefault[]
  state: RequestState
}

export function RuntimeSettingsPanel({
  activeSubmodule,
  chatConnectionId,
  chatModelId,
  chatModels,
  chatRetrievalSettings,
  checkingConnectionId,
  connectionApiKey,
  connectionBaseUrl,
  connectionCheckResults,
  connectionCapabilities,
  connectionProvider,
  connectionType,
  connections,
  deleteConnectionConfirmation,
  deleteConnectionId,
  editingConnectionId,
  error,
  globalChatRerankCandidateLimit,
  globalChatRerankEnabled,
  globalChatRetrievalLimit,
  globalSlot,
  globalSlotConnectionId,
  globalSlotModelId,
  onChatConnectionIdChange,
  onChatModelIdChange,
  onConnectionApiKeyChange,
  onConnectionBaseUrlChange,
  onConnectionCapabilitiesChange,
  onConnectionProviderChange,
  onConnectionTypeChange,
  onCancelDeleteConnection,
  onCancelEditConnection,
  onCheckConnection,
  onDeleteConnection,
  onDeleteConnectionConfirmationChange,
  onGlobalChatRerankCandidateLimitChange,
  onGlobalChatRerankEnabledChange,
  onGlobalChatRetrievalLimitChange,
  onGlobalSlotChange,
  onGlobalSlotConnectionIdChange,
  onGlobalSlotModelIdChange,
  onProjectChatRerankCandidateLimitChange,
  onProjectChatRerankEnabledChange,
  onProjectChatRetrievalLimitChange,
  onProjectSlotChange,
  onProjectSlotConnectionIdChange,
  onProjectSlotModelIdChange,
  onRefreshGlobalDefaults,
  onRefreshModelCatalog,
  onRefreshProjectOverrides,
  onResetProjectChatRetrieval,
  onResetProjectSlot,
  onRequestDeleteConnection,
  onRequestEditConnection,
  onSaveConnection,
  onSaveGlobalChatModel,
  onSaveGlobalChatRetrieval,
  onSaveGlobalSlot,
  onSaveProjectChatRetrieval,
  onSaveProjectOverride,
  onSyncProviderModels,
  onModelSyncConnectionIdChange,
  modelSyncConnectionId,
  providerModels,
  projectId,
  projectChatRerankCandidateLimit,
  projectChatRerankEnabled,
  projectChatRetrievalLimit,
  projectRuntimeSettings,
  projectSlot,
  projectSlotConnectionId,
  projectSlotModelId,
  slots,
  state,
}: RuntimeSettingsPanelProps) {
  const globalSlotConnections = connectionsForCapability(connections, globalSlot)
  const globalSlotModelOptions = providerModelOptions({
    capability: globalSlot,
    connectionId: globalSlotConnectionId,
    providerModels,
    selectedModelId: globalSlotModelId,
  })
  const chatConnections = connectionsForCapability(connections, 'chat')
  const chatModelOptions = providerModelOptions({
    capability: 'chat',
    connectionId: chatConnectionId,
    configuredModels: chatModels,
    providerModels,
    selectedModelId: chatModelId,
  })
  const projectSlotConnections = connectionsForCapability(connections, projectSlot)
  const projectSlotModelOptions = providerModelOptions({
    capability: projectSlot,
    connectionId: projectSlotConnectionId,
    providerModels,
    selectedModelId: projectSlotModelId,
  })
  const globalSlotSyncMessage = missingSyncedModelMessage({
    connectionId: globalSlotConnectionId,
    modelOptions: globalSlotModelOptions,
    target: globalSlot,
  })
  const chatSyncMessage = missingSyncedModelMessage({
    connectionId: chatConnectionId,
    modelOptions: chatModelOptions,
    target: 'chat default',
  })
  const projectSlotSyncMessage = missingSyncedModelMessage({
    connectionId: projectSlotConnectionId,
    modelOptions: projectSlotModelOptions,
    target: projectSlot,
  })

  const activePanel =
    activeSubmodule === 'connections' ? (
      <RuntimeConnectionsPanel
        connectionApiKey={connectionApiKey}
        connectionBaseUrl={connectionBaseUrl}
        connectionCapabilities={connectionCapabilities}
        connectionProvider={connectionProvider}
        connectionType={connectionType}
        connections={connections}
        checkingConnectionId={checkingConnectionId}
        connectionCheckResults={connectionCheckResults}
        deleteConnectionConfirmation={deleteConnectionConfirmation}
        deleteConnectionId={deleteConnectionId}
        editingConnectionId={editingConnectionId}
        onCancelDeleteConnection={onCancelDeleteConnection}
        onCancelEditConnection={onCancelEditConnection}
        onCheckConnection={onCheckConnection}
        onConnectionApiKeyChange={onConnectionApiKeyChange}
        onConnectionBaseUrlChange={onConnectionBaseUrlChange}
        onConnectionCapabilitiesChange={onConnectionCapabilitiesChange}
        onConnectionProviderChange={onConnectionProviderChange}
        onConnectionTypeChange={onConnectionTypeChange}
        onDeleteConnection={onDeleteConnection}
        onDeleteConnectionConfirmationChange={
          onDeleteConnectionConfirmationChange
        }
        onRequestDeleteConnection={onRequestDeleteConnection}
        onRequestEditConnection={onRequestEditConnection}
        onSaveConnection={onSaveConnection}
        state={state}
      />
    ) : activeSubmodule === 'model_catalog' ? (
      <RuntimeModelCatalogPanel
        connections={connections}
        modelSyncConnectionId={modelSyncConnectionId}
        onEditConnection={onRequestEditConnection}
        onModelSyncConnectionIdChange={onModelSyncConnectionIdChange}
        onRefresh={onRefreshModelCatalog}
        onSyncProviderModels={onSyncProviderModels}
        providerModels={providerModels}
        state={state}
      />
    ) : activeSubmodule === 'global_defaults' ? (
      <RuntimeGlobalDefaultsPanel
        chatConnectionId={chatConnectionId}
        chatConnections={chatConnections}
        chatModelId={chatModelId}
        chatModelOptions={chatModelOptions}
        chatModels={chatModels}
        chatRetrievalSettings={chatRetrievalSettings}
        chatSyncMessage={chatSyncMessage}
        globalChatRerankCandidateLimit={globalChatRerankCandidateLimit}
        globalChatRerankEnabled={globalChatRerankEnabled}
        globalChatRetrievalLimit={globalChatRetrievalLimit}
        globalSlot={globalSlot}
        globalSlotConnectionId={globalSlotConnectionId}
        globalSlotConnections={globalSlotConnections}
        globalSlotModelId={globalSlotModelId}
        globalSlotModelOptions={globalSlotModelOptions}
        globalSlotSyncMessage={globalSlotSyncMessage}
        onChatConnectionIdChange={onChatConnectionIdChange}
        onChatModelIdChange={onChatModelIdChange}
        onGlobalChatRerankCandidateLimitChange={
          onGlobalChatRerankCandidateLimitChange
        }
        onGlobalChatRerankEnabledChange={onGlobalChatRerankEnabledChange}
        onGlobalChatRetrievalLimitChange={onGlobalChatRetrievalLimitChange}
        onGlobalSlotChange={onGlobalSlotChange}
        onGlobalSlotConnectionIdChange={onGlobalSlotConnectionIdChange}
        onGlobalSlotModelIdChange={onGlobalSlotModelIdChange}
        onRefresh={onRefreshGlobalDefaults}
        onSaveGlobalChatModel={onSaveGlobalChatModel}
        onSaveGlobalChatRetrieval={onSaveGlobalChatRetrieval}
        onSaveGlobalSlot={onSaveGlobalSlot}
        slots={slots}
        state={state}
      />
    ) : (
      <RuntimeProjectOverridesPanel
        onProjectChatRerankCandidateLimitChange={
          onProjectChatRerankCandidateLimitChange
        }
        onProjectChatRerankEnabledChange={onProjectChatRerankEnabledChange}
        onProjectChatRetrievalLimitChange={onProjectChatRetrievalLimitChange}
        onProjectSlotChange={onProjectSlotChange}
        onProjectSlotConnectionIdChange={onProjectSlotConnectionIdChange}
        onProjectSlotModelIdChange={onProjectSlotModelIdChange}
        onRefresh={onRefreshProjectOverrides}
        onResetProjectChatRetrieval={onResetProjectChatRetrieval}
        onResetProjectSlot={onResetProjectSlot}
        onSaveProjectChatRetrieval={onSaveProjectChatRetrieval}
        onSaveProjectOverride={onSaveProjectOverride}
        projectChatRerankCandidateLimit={projectChatRerankCandidateLimit}
        projectChatRerankEnabled={projectChatRerankEnabled}
        projectChatRetrievalLimit={projectChatRetrievalLimit}
        projectId={projectId}
        projectRuntimeSettings={projectRuntimeSettings}
        projectSlot={projectSlot}
        projectSlotConnectionId={projectSlotConnectionId}
        projectSlotConnections={projectSlotConnections}
        projectSlotModelId={projectSlotModelId}
        projectSlotModelOptions={projectSlotModelOptions}
        projectSlotSyncMessage={projectSlotSyncMessage}
        state={state}
      />
    )

  return (
    <div className="min-w-0 grid gap-4 max-[680px]:gap-0">
      {error ? (
        <Callout className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-3 max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm" role="alert" tone="danger">
          {operatorSafeMessage(error)}
        </Callout>
      ) : null}
      {activePanel}
    </div>
  )
}

function RuntimePanel({
  ariaLabel,
  children,
  description,
  id,
  status,
  title,
}: {
  ariaLabel?: string
  children: ReactNode
  description?: ReactNode
  id: string
  status: ReactNode
  title: string
}) {
  return (
    <Panel
      aria-label={ariaLabel}
      aria-labelledby={ariaLabel === undefined ? id : undefined}
      role="region"
    >
      <PanelHeader className="max-[680px]:text-left max-[680px]:isolate max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-x-auto max-[680px]:border-b max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary min-w-0 flex-col items-start justify-between gap-3 p-4 sm:flex-row max-[680px]:gap-0 max-[680px]:p-0">
        <div className="grid min-w-0 gap-1 max-[680px]:gap-0">
          <p className="max-[680px]:truncate text-xs font-medium uppercase tracking-normal text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:px-0">
            Runtime
          </p>
          <h2 id={id} className="max-[680px]:font-medium max-[680px]:truncate text-lg font-semibold leading-none tracking-tight max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">
            {title}
          </h2>
          {description ? (
            <PanelDescription className="max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{description}</PanelDescription>
          ) : null}
        </div>
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-start gap-2 sm:justify-end max-[680px]:gap-0">
          {status}
        </div>
      </PanelHeader>
      <PanelBody className="max-[680px]:text-left max-[680px]:isolate max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:overscroll-contain max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm max-[680px]:overflow-x-auto max-[680px]:border-t max-[680px]:border-primary grid gap-4 p-4 pt-0 max-[680px]:gap-0 max-[680px]:p-0 max-[680px]:pt-0">{children}</PanelBody>
    </Panel>
  )
}

function RuntimeStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      className="max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full break-all max-[680px]:truncate text-left max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      tone={runtimeStatusTone(state)}
    >
      {runtimeStatusLabel(state)}
    </StatusBadge>
  )
}

function runtimeStatusTone(
  state: RequestState,
): 'danger' | 'neutral' | 'success' | 'warning' {
  if (state === 'failed') return 'danger'
  if (state === 'succeeded') return 'success'
  if (state === 'loading') return 'warning'
  if (state === 'canceled') return 'neutral'
  return 'neutral'
}

function sourceLabel(source: string): string {
  if (source === 'overridden') {
    return 'Overridden'
  }
  if (source === 'inherited') {
    return 'Inherited'
  }
  if (source === 'global') {
    return 'Global'
  }
  if (source === 'project') {
    return 'Project'
  }
  if (source === 'default') {
    return 'Default'
  }
  return source.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function secretNameLabel(secretName: string): string {
  if (secretName === 'api_key') {
    return 'API Key'
  }
  return titleCaseToken(secretName)
}

function RuntimeField({
  children,
  className,
  error,
  help,
  id,
  label,
}: {
  children(id: string): ReactNode
  className?: string
  error?: ReactNode
  help?: ReactNode
  id: string
  label: string
}) {
  return (
    <Field className={className}>
      <FieldLabel className="max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
      {help ? <FieldHelp className="max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" id={`${id}-help`}>{help}</FieldHelp> : null}
      {error ? <FieldError className="max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{error}</FieldError> : null}
    </Field>
  )
}

export function RuntimeConnectionsPanel({
  checkingConnectionId,
  connectionApiKey,
  connectionBaseUrl,
  connectionCheckResults,
  connectionCapabilities,
  connectionProvider,
  connectionType,
  connections,
  deleteConnectionConfirmation,
  deleteConnectionId,
  editingConnectionId,
  onCancelDeleteConnection,
  onCancelEditConnection,
  onCheckConnection,
  onConnectionApiKeyChange,
  onConnectionBaseUrlChange,
  onConnectionCapabilitiesChange,
  onConnectionProviderChange,
  onConnectionTypeChange,
  onDeleteConnection,
  onDeleteConnectionConfirmationChange,
  onRequestDeleteConnection,
  onRequestEditConnection,
  onSaveConnection,
  state,
}: {
  checkingConnectionId: string | null
  connectionApiKey: string
  connectionBaseUrl: string
  connectionCheckResults: Record<string, ProviderConnectionCheckResponse>
  connectionCapabilities: string[]
  connectionProvider: string
  connectionType: string
  connections: ProviderConnection[]
  deleteConnectionConfirmation: string
  deleteConnectionId: string | null
  editingConnectionId: string | null
  onCancelDeleteConnection(): void
  onCancelEditConnection(): void
  onCheckConnection(connectionId: string): void
  onConnectionApiKeyChange(value: string): void
  onConnectionBaseUrlChange(value: string): void
  onConnectionCapabilitiesChange(value: string[]): void
  onConnectionProviderChange(value: string): void
  onConnectionTypeChange(value: string): void
  onDeleteConnection(event: FormEvent<HTMLFormElement>): void
  onDeleteConnectionConfirmationChange(value: string): void
  onRequestDeleteConnection(connectionId: string): void
  onRequestEditConnection(connectionId: string): void
  onSaveConnection(event: FormEvent<HTMLFormElement>): void
  state: RequestState
}) {
  const canSaveConnection = connectionCapabilities.length > 0 && state !== 'loading'
  const isEditingConnection = editingConnectionId !== null

  return (
    <RuntimePanel
      id="runtime-connections-title"
      status={<RuntimeStatus state={state} />}
      title="Connections"
    >
      <section aria-label="Provider Connections" className="grid gap-3 max-[680px]:gap-0">
        {state === 'loading' && connections.length === 0 ? (
          <EmptyState
            aria-busy="true"
            className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="loading"
            role="status"
          >
            Loading Connections…
          </EmptyState>
        ) : state === 'canceled' && connections.length === 0 ? (
          <EmptyState
            className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="canceled"
            role="status"
          >
            Connections Load Canceled.
          </EmptyState>
        ) : connections.length === 0 ? (
          <EmptyState className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
            No Connections Yet.
          </EmptyState>
        ) : (
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            {connections.map((connection) => {
              const isChecking =
                checkingConnectionId === connection.connection_id
              const checkResult =
                connectionCheckResults[connection.connection_id]
              return (
                <DataListItem
                  aria-busy={isChecking || undefined}
                  className="max-[680px]:text-left max-[680px]:touch-manipulation max-[680px]:overflow-hidden grid gap-3 max-[680px]:gap-0 max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary md:grid-cols-[minmax(0,1fr)_auto]"
                  key={connection.connection_id}
                >
                  <div className="grid min-w-0 gap-2 max-[680px]:gap-0">
                    <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
                      <strong className="max-[680px]:font-medium truncate font-mono text-xs font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                        {connection.connection_id}
                      </strong>
                      <div className="flex flex-wrap gap-2 max-[680px]:gap-0">
                        <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full truncate max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                          {providerLabel(connection.provider)} /{' '}
                          {connectionTypeLabel(connection.connection_type)}
                        </Badge>
                        <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full truncate max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">
                          {connection.capabilities
                            .map((capability) => slotLabel(capability))
                            .join(', ')}
                        </Badge>
                        {isChecking ? (
                          <StatusBadge
                            className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                            role="status"
                            tone="warning"
                          >
                            Checking…
                          </StatusBadge>
                        ) : null}
                      </div>
                      {connection.base_url ? (
                        <small className="max-[680px]:truncate break-all text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                          {connection.base_url}
                        </small>
                      ) : null}
                    </div>
                    <ConnectionSecretSummary connection={connection} />
                    <ConnectionCheckSummary
                      isChecking={isChecking}
                      result={checkResult}
                    />
                  </div>
                  <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap justify-start gap-2 md:justify-end max-[680px]:gap-0 max-[680px]:px-0">
                    <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                      aria-label={`Check ${connection.connection_id} Connection`}
                      disabled={state === 'loading' || isChecking}
                      onClick={() => onCheckConnection(connection.connection_id)}
                      size="sm"
                      variant="secondary"
                    >
                      {isChecking ? 'Checking…' : 'Check'}
                    </Button>
                    <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                      aria-label={`Edit ${connection.connection_id} Connection`}
                      disabled={state === 'loading'}
                      onClick={() =>
                        onRequestEditConnection(connection.connection_id)
                      }
                      size="sm"
                      variant="secondary"
                    >
                      Edit
                    </Button>
                    <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                      aria-label={`Delete ${connection.connection_id} Connection`}
                      disabled={state === 'loading'}
                      onClick={() =>
                        onRequestDeleteConnection(connection.connection_id)
                      }
                      size="sm"
                      variant="danger"
                    >
                      Delete
                    </Button>
                  </DataListItemActions>
                  {deleteConnectionId === connection.connection_id ? (
                    <form
                      aria-label={`Delete ${connection.connection_id} Connection`}
                      className="grid gap-3 max-[680px]:gap-0 rounded-md border border-destructive/30 bg-destructive/10 p-3 md:col-span-2 max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm"
                      onSubmit={onDeleteConnection}
                    >
                      <InlineFeedback className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="danger">
                        Type <strong className="max-[680px]:truncate break-all max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{connection.connection_id}</strong> to Confirm
                        Deletion.
                      </InlineFeedback>
                      <RuntimeField
                        id={`delete-${connection.connection_id}-confirmation`}
                        label="Confirm Connection ID"
                      >
                        {(fieldId) => (
                          <Input
                            className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                            autoComplete="off"
                            id={fieldId}
                            onChange={(event) =>
                              onDeleteConnectionConfirmationChange(
                                event.currentTarget.value,
                              )
                            }
                            value={deleteConnectionConfirmation}
                          />
                        )}
                      </RuntimeField>
                      <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap max-[680px]:gap-0 max-[680px]:px-0">
                        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                          disabled={state === 'loading'}
                          onClick={onCancelDeleteConnection}
                          size="sm"
                          variant="secondary"
                        >
                          Cancel
                        </Button>
                        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                          disabled={
                            state === 'loading' ||
                            deleteConnectionConfirmation.trim() !==
                              connection.connection_id
                          }
                          size="sm"
                          type="submit"
                          variant="danger"
                        >
                          Delete Connection
                        </Button>
                      </DataListItemActions>
                    </form>
                  ) : null}
                </DataListItem>
              )
            })}
          </DataList>
        )}
      </section>

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveConnection}>
        <div className="flex flex-wrap items-center justify-between gap-2 max-[680px]:gap-0">
          <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">
            {isEditingConnection
              ? `Edit Connection ${editingConnectionId}`
              : 'New Connection'}
          </h3>
          {isEditingConnection ? (
            <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
              disabled={state === 'loading'}
              onClick={onCancelEditConnection}
              size="sm"
              variant="secondary"
            >
              Cancel Edit
            </Button>
          ) : null}
        </div>
        <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-2">
          <RuntimeField id="runtime-connection-provider" label="Provider">
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                onValueChange={onConnectionProviderChange}
                options={[
                  { label: 'Qwen', value: 'qwen' },
                  {
                    label: 'Local OpenAI-compatible',
                    value: 'local_openai_compatible',
                  },
                  { label: 'Fake', value: 'fake' },
                ]}
                value={connectionProvider}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-connection-type"
            label="Connection Type"
          >
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                onValueChange={onConnectionTypeChange}
                options={[
                  { label: 'Hosted', value: 'hosted' },
                  { label: 'Local', value: 'local' },
                  { label: 'Fake', value: 'fake' },
                ]}
                value={connectionType}
              />
            )}
          </RuntimeField>
          <RuntimeField id="runtime-connection-base-url" label="Base URL">
            {(fieldId) => (
              <Input
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                onChange={(event) =>
                  onConnectionBaseUrlChange(event.currentTarget.value)
                }
                value={connectionBaseUrl}
              />
            )}
          </RuntimeField>
          <Field className="md:col-span-2 max-[680px]:gap-0">
            <FieldLabel
              className="max-[680px]:text-left max-[680px]:antialiased max-[680px]:select-none max-[680px]:ring-offset-0 max-[680px]:rounded-sm max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
              htmlFor="runtime-capability-filter"
              id="runtime-connection-capabilities-label"
            >
              Capabilities
            </FieldLabel>
            <FieldControl>
              <CapabilitySelector
                labelledBy="runtime-connection-capabilities-label"
                onChange={onConnectionCapabilitiesChange}
                options={PROVIDER_CONNECTION_CAPABILITIES}
                value={connectionCapabilities}
              />
            </FieldControl>
          </Field>
          <RuntimeField
            className="md:col-span-2"
            help={
              isEditingConnection
                ? 'Leave Blank to Keep the Existing Key. A New Value Replaces It.'
                : undefined
            }
            id="runtime-connection-api-key"
            label="API Key"
          >
            {(fieldId) => (
              <Input
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                aria-describedby={
                  isEditingConnection ? `${fieldId}-help` : undefined
                }
                autoComplete="new-password"
                id={fieldId}
                onChange={(event) =>
                  onConnectionApiKeyChange(event.currentTarget.value)
                }
                spellCheck={false}
                type="password"
                value={connectionApiKey}
              />
            )}
          </RuntimeField>
        </div>
        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={!canSaveConnection} type="submit">
          {isEditingConnection ? 'Update Connection' : 'Save Connection'}
        </Button>
      </form>
    </RuntimePanel>
  )
}

export function CapabilitySelector({
  labelledBy,
  onChange,
  options,
  value,
}: {
  labelledBy?: string
  onChange(value: string[]): void
  options: readonly string[]
  value: string[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement | null>(null)
  const listboxId = 'runtime-capability-options'
  const inputId = 'runtime-capability-filter'
  const selected = new Set(value)
  const normalizedQuery = query.trim().toLowerCase()
  const filteredOptions = options.filter((capability) => {
    if (selected.has(capability)) {
      return false
    }
    if (!normalizedQuery) {
      return true
    }
    return capability.toLowerCase().includes(normalizedQuery)
  })

  function toggleCapability(capability: string) {
    if (selected.has(capability)) {
      onChange(value.filter((item) => item !== capability))
      return
    }
    onChange([...value, capability])
    setQuery('')
  }

  function handleFilterKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault()
      if (filteredOptions.length > 0) {
        toggleCapability(filteredOptions[0])
      }
    } else if (event.key === 'Escape') {
      setIsOpen(false)
    } else if (
      event.key === 'Backspace' &&
      query.length === 0 &&
      value.length > 0
    ) {
      onChange(value.slice(0, -1))
    }
  }

  return (
    <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
      <div className="relative" data-slot="capability-selector">
        <Popover.Trigger asChild>
          <div
            className="max-[680px]:motion-reduce:transition-none flex min-h-9 w-full items-center gap-2 max-[680px]:gap-0 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground motion-safe:transition-colors focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background data-[state=open]:ring-2 data-[state=open]:ring-ring data-[state=open]:ring-offset-2 data-[state=open]:ring-offset-background max-[680px]:min-h-11 max-[680px]:focus-within:ring-offset-0 max-[680px]:data-[state=open]:ring-offset-0 max-[680px]:px-0 max-[680px]:text-base max-[680px]:leading-none max-[680px]:tracking-tighter max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary"            onClick={() => {
              setIsOpen(true)
              inputRef.current?.focus()
            }}
          >
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1 max-[680px]:gap-0 max-[680px]:overflow-hidden">
              {value.map((capability) => (
                <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate gap-1 pr-1 max-[680px]:gap-0 max-[680px]:pr-0 max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter max-[680px]:border-primary max-[680px]:bg-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm" key={capability} tone="primary">
                  <span>{slotLabel(capability)}</span>
                  <Button
                    aria-label={`Remove ${slotLabel(capability)} Capability`}
                    className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:basis-full max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:max-w-full h-5 px-1 text-xs max-[680px]:min-h-11 max-[680px]:h-auto max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none max-[680px]:py-0"
                    onClick={(event) => {
                      event.stopPropagation()
                      toggleCapability(capability)
                      inputRef.current?.focus()
                    }}
                    size="sm"
                    tabIndex={-1}
                    type="button"
                    variant="ghost"
                  >
                    ×
                  </Button>
                </Badge>
              ))}
              <Input
                aria-autocomplete="list"
                aria-controls={listboxId}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                aria-label={labelledBy === undefined ? 'Capabilities' : undefined}
                aria-labelledby={labelledBy}
                autoComplete="off"
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:overflow-hidden h-7 min-w-32 flex-1 border-0 bg-transparent px-0 py-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 max-[680px]:h-5 max-[680px]:min-w-20 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={inputId}
                onChange={(event) => {
                  setQuery(event.currentTarget.value)
                  setIsOpen(true)
                }}
                onClick={(event) => {
                  event.stopPropagation()
                  setIsOpen(true)
                }}
                onFocus={() => setIsOpen(true)}
                onKeyDown={handleFilterKeyDown}
                placeholder={value.length === 0 ? 'Select Capabilities' : ''}
                ref={inputRef}
                role="combobox"
                value={query}
              />
            </div>
            <ChevronDown
              aria-hidden="true"
              className="size-4 text-muted-foreground max-[680px]:size-3"
            />
          </div>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            aria-label="Capability Options"
            className="z-20 grid max-h-60 max-[680px]:min-w-0 w-[var(--radix-popover-trigger-width)] gap-1 max-[680px]:max-h-12 max-[680px]:overscroll-y-contain max-[680px]:gap-0 overflow-auto rounded-md border border-border bg-popover p-1 max-[680px]:p-0 text-popover-foreground shadow-[var(--shadow-popover)] max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:rounded-sm"
            id={listboxId}
            onOpenAutoFocus={(event) => {
              event.preventDefault()
              inputRef.current?.focus()
            }}
            role="listbox"
            side="bottom"
            sideOffset={2}
          >
            {filteredOptions.length === 0 ? (
              <p
                className="p-3 text-left text-sm text-muted-foreground max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                data-slot-state="empty"
                role="status"
              >
                No Capabilities Found.
              </p>
            ) : (
              filteredOptions.map((capability) => (
                <Button
                  aria-label={`Add ${slotLabel(capability)} Capability`}
                  aria-selected={false}
                  className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate justify-start max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none max-[680px]:py-0 max-[680px]:rounded-sm"
                  key={capability}
                  onClick={() => {
                    toggleCapability(capability)
                    inputRef.current?.focus()
                  }}
                  role="option"
                  type="button"
                  variant="ghost"
                >
                  <span>{slotLabel(capability)}</span>
                </Button>
              ))
            )}
          </Popover.Content>
        </Popover.Portal>
      </div>
    </Popover.Root>
  )
}

export function RuntimeModelCatalogPanel({
  connections,
  modelSyncConnectionId,
  onEditConnection,
  onModelSyncConnectionIdChange,
  onRefresh,
  onSyncProviderModels,
  providerModels,
  state,
}: {
  connections: ProviderConnection[]
  modelSyncConnectionId: string
  onEditConnection(connectionId: string): void
  onModelSyncConnectionIdChange(value: string): void
  onRefresh(): void
  onSyncProviderModels(event: FormEvent<HTMLFormElement>): void
  providerModels: ProviderModel[]
  state: RequestState
}) {
  const selectedConnection = connections.find(
    (connection) => connection.connection_id === modelSyncConnectionId.trim(),
  )

  return (
    <RuntimePanel
      id="runtime-model-catalog-title"
      status={<RuntimeStatus state={state} />}
      title="Model Catalog"
    >
      <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing…' : 'Refresh Catalog'}
      </Button>

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSyncProviderModels}>
        <RuntimeField
          id="runtime-model-sync-connection"
          label="Model Sync Connection"
        >
          {(fieldId) => (
            <ConnectionSelect
              connections={connections}
              id={fieldId}
              isLoading={state === 'loading'}
              onChange={onModelSyncConnectionIdChange}
              testId="model-sync-connection-select"
              value={modelSyncConnectionId}
            />
          )}
        </RuntimeField>
        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" type="submit">Sync Models</Button>
      </form>

      {selectedConnection ? (
        <section
          aria-label="Selected Model Sync Connection"
          className="grid gap-3 max-[680px]:gap-0"
        >
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            <DataListItem className="max-[680px]:text-left max-[680px]:touch-manipulation max-[680px]:overflow-hidden grid gap-3 max-[680px]:gap-0 max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary md:grid-cols-[minmax(0,1fr)_auto]">
              <div className="max-[680px]:overflow-hidden grid min-w-0 gap-2 max-[680px]:gap-0">
                <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
                  <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {connectionOptionLabel(selectedConnection)}
                  </strong>
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {selectedConnection.connection_id}
                  </small>
                  <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">
                    {selectedConnection.capabilities
                      .map((capability) => slotLabel(capability))
                      .join(', ')}
                  </Badge>
                  {selectedConnection.base_url ? (
                    <small className="max-[680px]:truncate break-all text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                      {selectedConnection.base_url}
                    </small>
                  ) : null}
                </div>
                <ConnectionSecretSummary connection={selectedConnection} />
              </div>
              <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap justify-start gap-2 md:justify-end max-[680px]:gap-0 max-[680px]:px-0">
                <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                  disabled={state === 'loading'}
                  onClick={() =>
                    onEditConnection(selectedConnection.connection_id)
                  }
                  size="sm"
                  variant="secondary"
                >
                  Edit Connection
                </Button>
              </DataListItemActions>
            </DataListItem>
          </DataList>
        </section>
      ) : null}

      <ProviderModelCatalogView
        isLoading={state === 'loading'}
        providerModels={providerModels}
      />
    </RuntimePanel>
  )
}

export function RuntimeGlobalDefaultsPanel({
  chatConnectionId,
  chatConnections,
  chatModelId,
  chatModelOptions,
  chatModels,
  chatRetrievalSettings,
  chatSyncMessage,
  globalChatRerankCandidateLimit,
  globalChatRerankEnabled,
  globalChatRetrievalLimit,
  globalSlot,
  globalSlotConnectionId,
  globalSlotConnections,
  globalSlotModelId,
  globalSlotModelOptions,
  globalSlotSyncMessage,
  onChatConnectionIdChange,
  onChatModelIdChange,
  onGlobalChatRerankCandidateLimitChange,
  onGlobalChatRerankEnabledChange,
  onGlobalChatRetrievalLimitChange,
  onGlobalSlotChange,
  onGlobalSlotConnectionIdChange,
  onGlobalSlotModelIdChange,
  onRefresh,
  onSaveGlobalChatModel,
  onSaveGlobalChatRetrieval,
  onSaveGlobalSlot,
  slots,
  state,
}: {
  chatConnectionId: string
  chatConnections: ProviderConnection[]
  chatModelId: string
  chatModelOptions: ProviderModelOption[]
  chatModels: ChatModel[]
  chatRetrievalSettings: ChatRetrievalSettings | null
  chatSyncMessage: string | null
  globalChatRerankCandidateLimit: number
  globalChatRerankEnabled: boolean
  globalChatRetrievalLimit: number
  globalSlot: string
  globalSlotConnectionId: string
  globalSlotConnections: ProviderConnection[]
  globalSlotModelId: string
  globalSlotModelOptions: ProviderModelOption[]
  globalSlotSyncMessage: string | null
  onChatConnectionIdChange(value: string): void
  onChatModelIdChange(value: string): void
  onGlobalChatRerankCandidateLimitChange(value: number): void
  onGlobalChatRerankEnabledChange(value: boolean): void
  onGlobalChatRetrievalLimitChange(value: number): void
  onGlobalSlotChange(value: string): void
  onGlobalSlotConnectionIdChange(value: string): void
  onGlobalSlotModelIdChange(value: string): void
  onRefresh(): void
  onSaveGlobalChatModel(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalSlot(event: FormEvent<HTMLFormElement>): void
  slots: RuntimeSlotDefault[]
  state: RequestState
}) {
  return (
    <RuntimePanel
      id="runtime-global-defaults-title"
      status={<RuntimeStatus state={state} />}
      title="Global Defaults"
    >
      <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing…' : 'Reload Global Defaults'}
      </Button>

      <RuntimeSlotList slots={slots} state={state} />

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveGlobalSlot}>
        <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-3">
          <RuntimeField id="runtime-global-slot" label="Global Slot">
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                data-testid="global-slot-select"
                id={fieldId}
                onValueChange={onGlobalSlotChange}
                options={RUNTIME_SLOTS.map((slot) => ({
                  label: slotLabel(slot),
                  value: slot,
                }))}
                value={globalSlot}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-global-slot-connection"
            label="Global Slot Connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={globalSlotConnections}
                id={fieldId}
                isLoading={state === 'loading'}
                onChange={onGlobalSlotConnectionIdChange}
                testId="global-slot-connection-select"
                value={globalSlotConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-global-slot-model"
            label="Global Slot Model"
          >
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                isLoading={state === 'loading'}
                models={globalSlotModelOptions}
                onChange={onGlobalSlotModelIdChange}
                testId="global-slot-model-select"
                value={globalSlotModelId}
              />
            )}
          </RuntimeField>
        </div>
        {globalSlotSyncMessage ? (
          <InlineFeedback className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" role="status" tone="warning">
            {globalSlotSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={globalSlotSyncMessage !== null} type="submit">
          Save Global Slot
        </Button>
      </form>

      <section aria-label="Global Chat Models" className="grid gap-3 max-[680px]:gap-0">
        <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Chat Models</h3>
        {state === 'loading' && chatModels.length === 0 ? (
          <EmptyState
            aria-busy="true"
            className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="loading"
            role="status"
          >
            Loading Chat Models…
          </EmptyState>
        ) : state === 'canceled' && chatModels.length === 0 ? (
          <EmptyState
            className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="canceled"
            role="status"
          >
            Chat Models Load Canceled.
          </EmptyState>
        ) : chatModels.length === 0 ? (
          <EmptyState className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
            No Chat Models Yet.
          </EmptyState>
        ) : (
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            {chatModels.map((model) => (
              <DataListItem
                className="max-[680px]:text-left max-[680px]:items-start max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
                  <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {model.model_id}
                  </strong>
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {model.connection_id}
                  </small>
                </div>
                <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone={model.is_default ? 'primary' : 'neutral'}>
                  {model.is_default ? 'Default' : 'Enabled'}
                </Badge>
              </DataListItem>
            ))}
          </DataList>
        )}
      </section>

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveGlobalChatModel}>
        <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-2">
          <RuntimeField
            id="runtime-chat-connection"
            label="Chat Connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={chatConnections}
                id={fieldId}
                isLoading={state === 'loading'}
                onChange={onChatConnectionIdChange}
                testId="chat-connection-select"
                value={chatConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField id="runtime-chat-model" label="Chat Model">
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                isLoading={state === 'loading'}
                models={chatModelOptions}
                onChange={onChatModelIdChange}
                testId="chat-model-select"
                value={chatModelId}
              />
            )}
          </RuntimeField>
        </div>
        {chatSyncMessage ? (
          <InlineFeedback className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" role="status" tone="warning">
            {chatSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={chatSyncMessage !== null} type="submit">
          Save Chat Default
        </Button>
      </form>

      <section aria-label="Global Chat Retrieval" className="grid gap-3 max-[680px]:gap-0">
        <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Chat Retrieval</h3>
        {state === 'loading' && chatRetrievalSettings === null ? (
          <EmptyState
            aria-busy="true"
            className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="loading"
            role="status"
          >
            Loading Chat Retrieval Defaults…
          </EmptyState>
        ) : state === 'canceled' && chatRetrievalSettings === null ? (
          <EmptyState
            className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="canceled"
            role="status"
          >
            Chat Retrieval Defaults Load Canceled.
          </EmptyState>
        ) : chatRetrievalSettings ? (
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            <DataListItem className="max-[680px]:text-left max-[680px]:items-start max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0">
              <div className="max-[680px]:overflow-hidden min-w-0 grid gap-1 max-[680px]:gap-0">
                <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                  Global Defaults
                </strong>
                <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                  Limit {chatRetrievalSettings.retrieval_limit} / candidate{' '}
                  {chatRetrievalSettings.rerank_candidate_limit}
                </small>
              </div>
              <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">
                {chatRetrievalSettings.rerank_enabled
                  ? 'Rerank On'
                  : 'Rerank Off'}
              </Badge>
            </DataListItem>
          </DataList>
        ) : (
          <EmptyState className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
            No Chat Retrieval Defaults Yet.
          </EmptyState>
        )}
        <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveGlobalChatRetrieval}>
          <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-3">
            <RuntimeField
              id="runtime-global-retrieval-limit"
              label="Retrieval Limit"
            >
              {(fieldId) => (
                <Input
                  className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                  id={fieldId}
                  max={CHAT_RETRIEVAL_MAX_LIMIT}
                  min={1}
                  onChange={(event) =>
                    onGlobalChatRetrievalLimitChange(
                      normalizeChatRetrievalLimit(event.currentTarget.value),
                    )
                  }
                  type="number"
                  value={globalChatRetrievalLimit}
                />
              )}
            </RuntimeField>
            <RuntimeField id="runtime-global-rerank" label="Rerank">
              {(fieldId) => (
                <Select
                  className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                  id={fieldId}
                  onValueChange={(nextValue) =>
                    onGlobalChatRerankEnabledChange(nextValue === 'true')
                  }
                  options={[
                    { label: 'On', value: 'true' },
                    { label: 'Off', value: 'false' },
                  ]}
                  value={String(globalChatRerankEnabled)}
                />
              )}
            </RuntimeField>
            <RuntimeField
              id="runtime-global-candidate-limit"
              label="Candidate Limit"
            >
              {(fieldId) => (
                <Input
                  className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                  id={fieldId}
                  max={CHAT_RETRIEVAL_MAX_LIMIT}
                  min={1}
                  onChange={(event) =>
                    onGlobalChatRerankCandidateLimitChange(
                      normalizeChatRetrievalLimit(event.currentTarget.value),
                    )
                  }
                  type="number"
                  value={globalChatRerankCandidateLimit}
                />
              )}
            </RuntimeField>
          </div>
          <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" type="submit">Save Chat Retrieval</Button>
        </form>
      </section>
    </RuntimePanel>
  )
}

export function RuntimeProjectOverridesPanel({
  onProjectChatRerankCandidateLimitChange,
  onProjectChatRerankEnabledChange,
  onProjectChatRetrievalLimitChange,
  onProjectSlotChange,
  onProjectSlotConnectionIdChange,
  onProjectSlotModelIdChange,
  onRefresh,
  onResetProjectChatRetrieval,
  onResetProjectSlot,
  onSaveProjectChatRetrieval,
  onSaveProjectOverride,
  projectChatRerankCandidateLimit,
  projectChatRerankEnabled,
  projectChatRetrievalLimit,
  projectId,
  projectRuntimeSettings,
  projectSlot,
  projectSlotConnectionId,
  projectSlotConnections,
  projectSlotModelId,
  projectSlotModelOptions,
  projectSlotSyncMessage,
  state,
}: {
  onProjectChatRerankCandidateLimitChange(value: number): void
  onProjectChatRerankEnabledChange(value: boolean): void
  onProjectChatRetrievalLimitChange(value: number): void
  onProjectSlotChange(value: string): void
  onProjectSlotConnectionIdChange(value: string): void
  onProjectSlotModelIdChange(value: string): void
  onRefresh(): void
  onResetProjectChatRetrieval(): void
  onResetProjectSlot(slot: string): void
  onSaveProjectChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveProjectOverride(event: FormEvent<HTMLFormElement>): void
  projectChatRerankCandidateLimit: number
  projectChatRerankEnabled: boolean
  projectChatRetrievalLimit: number
  projectId: string
  projectRuntimeSettings: ProjectRuntimeSettings | null
  projectSlot: string
  projectSlotConnectionId: string
  projectSlotConnections: ProviderConnection[]
  projectSlotModelId: string
  projectSlotModelOptions: ProviderModelOption[]
  projectSlotSyncMessage: string | null
  state: RequestState
}) {
  return (
    <RuntimePanel
      ariaLabel="Project Runtime Settings"
      id="runtime-project-overrides-title"
      status={
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-end gap-2 max-[680px]:gap-0">
          <RuntimeStatus state={state} />
          <StatusBadge className="max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:rounded-sm max-w-full break-all max-[680px]:truncate text-left max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">
            {projectId.trim() || 'No Project'}
          </StatusBadge>
        </div>
      }
      title="Project Overrides"
    >
      <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing…' : 'Reload Project Settings'}
      </Button>

      <ProjectRuntimeSettingsView
        onResetProjectSlot={onResetProjectSlot}
        settings={projectRuntimeSettings}
        state={state}
      />

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveProjectChatRetrieval}>
        <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-3">
          <RuntimeField
            id="runtime-project-retrieval-limit"
            label="Retrieval Limit"
          >
            {(fieldId) => (
              <Input
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                max={CHAT_RETRIEVAL_MAX_LIMIT}
                min={1}
                onChange={(event) =>
                  onProjectChatRetrievalLimitChange(
                    normalizeChatRetrievalLimit(event.currentTarget.value),
                  )
                }
                type="number"
                value={projectChatRetrievalLimit}
              />
            )}
          </RuntimeField>
          <RuntimeField id="runtime-project-rerank" label="Rerank">
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                onValueChange={(nextValue) =>
                  onProjectChatRerankEnabledChange(nextValue === 'true')
                }
                options={[
                  { label: 'On', value: 'true' },
                  { label: 'Off', value: 'false' },
                ]}
                value={String(projectChatRerankEnabled)}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-candidate-limit"
            label="Candidate Limit"
          >
            {(fieldId) => (
              <Input
                className="max-[680px]:text-left max-[680px]:accent-primary max-[680px]:caret-primary max-[680px]:outline-offset-0 max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                max={CHAT_RETRIEVAL_MAX_LIMIT}
                min={1}
                onChange={(event) =>
                  onProjectChatRerankCandidateLimitChange(
                    normalizeChatRetrievalLimit(event.currentTarget.value),
                  )
                }
                type="number"
                value={projectChatRerankCandidateLimit}
              />
            )}
          </RuntimeField>
        </div>
        <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap max-[680px]:gap-0 max-[680px]:px-0">
          <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" type="submit">Save Project Retrieval Override</Button>
          {projectRuntimeSettings?.chat_retrieval.source === 'project' ? (
            <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
              onClick={onResetProjectChatRetrieval}
              type="button"
              variant="secondary"
            >
              Reset Chat Retrieval to Global
            </Button>
          ) : null}
        </DataListItemActions>
      </form>

      <form className="grid gap-4 max-[680px]:gap-0" onSubmit={onSaveProjectOverride}>
        <div className="min-w-0 grid gap-4 max-[680px]:gap-0 md:grid-cols-3">
          <RuntimeField id="runtime-project-slot" label="Project Slot">
            {(fieldId) => (
              <Select
                className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
                id={fieldId}
                onValueChange={onProjectSlotChange}
                options={RUNTIME_SLOTS.map((slot) => ({
                  label: slotLabel(slot),
                  value: slot,
                }))}
                value={projectSlot}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-slot-connection"
            label="Project Slot Connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={projectSlotConnections}
                id={fieldId}
                isLoading={state === 'loading'}
                onChange={onProjectSlotConnectionIdChange}
                testId="project-slot-connection-select"
                value={projectSlotConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-slot-model"
            label="Project Slot Model"
          >
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                isLoading={state === 'loading'}
                models={projectSlotModelOptions}
                onChange={onProjectSlotModelIdChange}
                testId="project-slot-model-select"
                value={projectSlotModelId}
              />
            )}
          </RuntimeField>
        </div>
        {projectSlotSyncMessage ? (
          <InlineFeedback className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" role="status" tone="warning">
            {projectSlotSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none" disabled={projectSlotSyncMessage !== null} type="submit">
          Save Project Override
        </Button>
      </form>
    </RuntimePanel>
  )
}

export function ConnectionSecretSummary({
  connection,
}: {
  connection: ProviderConnection
}) {
  if (connection.secrets.length === 0) {
    return (
      <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
        {connection.connection_type === 'fake'
          ? 'Secrets Not Required for This Connection'
          : 'No API Key on File'}
      </small>
    )
  }
  return (
    <div className="flex flex-wrap gap-2 max-[680px]:gap-0">
      {connection.secrets.map((secret) => (
        <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" key={secret.secret_name} tone={secret.configured ? 'success' : 'neutral'}>
          {secretNameLabel(secret.secret_name)}{' '}
          {secret.configured ? 'Configured' : 'Not Configured'}
          {secret.last_four ? ` / Last Four ${secret.last_four}` : ''}
        </Badge>
      ))}
    </div>
  )
}

export function ConnectionCheckSummary({
  isChecking = false,
  result,
}: {
  isChecking?: boolean
  result: ProviderConnectionCheckResponse | undefined
}) {
  if (isChecking) {
    return (
      <InlineFeedback className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-destructive max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" aria-live="polite" role="status" tone="warning">
        Checking Connection…
      </InlineFeedback>
    )
  }

  if (result === undefined) {
    return (
      <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">Not Checked</small>
    )
  }

  if (result.ok) {
    return (
      <Callout
        aria-live="polite"
        className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden p-2 max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        role="status"
        tone="success"
      >
        Connection Check Passed: {result.model_count} Provider Models Reachable.
      </Callout>
    )
  }

  return (
    <Callout className="max-[680px]:text-left max-[680px]:items-start max-[680px]:antialiased max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-2 max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-destructive max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-destructive max-[680px]:tracking-tighter max-[680px]:rounded-sm" role="alert" tone="danger">
      Connection Check Failed. Verify Base URL, Capabilities, and API Key.
      {result.message.trim().length > 0 ? (
        <span className="max-[680px]:truncate mt-1 block text-xs opacity-90 max-[680px]:mt-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
          {operatorSafeMessage(result.message, 'Provider Rejected the Check.')}
        </span>
      ) : null}
    </Callout>
  )
}

export function ConnectionSelect({
  connections,
  id,
  isLoading = false,
  onChange,
  testId,
  value,
}: {
  connections: ProviderConnection[]
  id?: string
  isLoading?: boolean
  onChange(value: string): void
  testId?: string
  value: string
}) {
  const emptyLabel = isLoading ? 'Loading Connections…' : 'No Connections Yet'
  return (
    <Select
      className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      data-testid={testId}
      disabled={isLoading && connections.length === 0}
      id={id}
      onValueChange={onChange}
      options={[
        {
          label:
            connections.length === 0 ? emptyLabel : 'Select Connection',
          value: '',
        },
        ...connections.map((connection) => ({
          label: connectionOptionLabel(connection),
          value: connection.connection_id,
        })),
      ]}
      value={value}
    />
  )
}

export function ProviderModelSelect({
  id,
  isLoading = false,
  models,
  onChange,
  testId,
  value,
}: {
  id?: string
  isLoading?: boolean
  models: ProviderModelOption[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  const emptyLabel = isLoading ? 'Loading Models…' : 'No Models Yet'
  return (
    <Select
      className="max-[680px]:text-left max-[680px]:outline-offset-0 max-[680px]:appearance-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border-primary max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter"
      data-testid={testId}
      disabled={models.length === 0}
      id={id}
      onValueChange={onChange}
      options={[
        {
          label: models.length === 0 ? emptyLabel : 'Select Model',
          value: '',
        },
        ...models.map((model) => ({
          label: model.model_id,
          value: model.model_id,
        })),
      ]}
      value={value}
    />
  )
}

export function ProviderModelCatalogView({
  isLoading = false,
  providerModels,
}: {
  isLoading?: boolean
  providerModels: ProviderModel[]
}) {
  return (
    <section aria-label="Provider Model Catalog" className="grid gap-3 max-[680px]:gap-0">
      <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Model Catalog</h3>
      {isLoading && providerModels.length === 0 ? (
        <EmptyState
          aria-busy="true"
          className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
          data-slot-state="loading"
          role="status"
        >
          Loading Provider Models…
        </EmptyState>
      ) : providerModels.length === 0 ? (
        <EmptyState className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
          No Provider Models Yet.
        </EmptyState>
      ) : (
        <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
          {providerModels.map((model) => (
            <DataListItem
              className="max-[680px]:text-left max-[680px]:items-start max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
                <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                  {model.model_id}
                </strong>
                <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                  {model.connection_id} /{' '}
                  {model.capabilities
                    .map((capability) => slotLabel(capability))
                    .join(', ')}
                </small>
                {model.pricing ? (
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    Pricing metadata saved
                  </small>
                ) : null}
              </div>
              <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone={model.pricing ? 'primary' : 'neutral'}>
                {model.pricing ? 'Pricing' : 'Metadata'}
              </Badge>
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  )
}

export function RuntimeSlotList({
  slots,
  state = 'idle',
}: {
  slots: RuntimeSlotDefault[]
  state?: RequestState
}) {
  if (state === 'loading' && slots.length === 0) {
    return (
      <EmptyState
        aria-busy="true"
        className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="loading"
        role="status"
      >
        Loading Global Slots…
      </EmptyState>
    )
  }
  if (state === 'canceled' && slots.length === 0) {
    return (
      <EmptyState
        className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="canceled"
        role="status"
      >
        Global Slots Load Canceled.
      </EmptyState>
    )
  }
  if (slots.length === 0) {
    return (
      <EmptyState
        className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="empty"
        role="status"
      >
        No Global Slot Defaults Yet. Save a Global Slot Below.
      </EmptyState>
    )
  }
  return (
    <DataList aria-label="Global Runtime Slots" className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0 max-[680px]:overflow-x-auto">
      {slots.map((slot) => (
        <DataListItem
          className="max-[680px]:text-left max-[680px]:items-start max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0"
          key={slot.slot}
        >
          <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
            <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{slotLabel(slot.slot)}</strong>
            <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
              {slot.connection_id} / {slot.model_id}
            </small>
          </div>
          <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">{sourceLabel('global')}</Badge>
        </DataListItem>
      ))}
    </DataList>
  )
}

export function ProjectRuntimeSettingsView({
  onResetProjectSlot,
  settings,
  state = 'idle',
}: {
  onResetProjectSlot(slot: string): void
  settings: ProjectRuntimeSettings | null
  state?: RequestState
}) {
  if (state === 'loading' && settings === null) {
    return (
      <EmptyState
        aria-busy="true"
        className="max-[680px]:items-start max-[680px]:motion-reduce:animate-none max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight motion-safe:animate-pulse max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="loading"
        role="status"
      >
        Loading Project Runtime Settings…
      </EmptyState>
    )
  }
  if (state === 'canceled' && settings === null) {
    return (
      <EmptyState
        className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate border-border/60 bg-muted/20 p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
        data-slot-state="canceled"
        role="status"
      >
        Project Runtime Settings Load Canceled.
      </EmptyState>
    )
  }
  if (settings === null) {
    return (
      <EmptyState className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm" data-slot-state="empty" role="status">
        No Project Runtime Settings Yet.
      </EmptyState>
    )
  }
  return (
    <div className="min-w-0 grid gap-4 max-[680px]:gap-0 xl:grid-cols-3">
      <section className="grid gap-3 max-[680px]:gap-0">
        <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Effective Slots</h3>
        {settings.slots.length === 0 ? (
          <EmptyState
            className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="empty"
            role="status"
          >
            No Effective Slots Yet.
          </EmptyState>
        ) : (
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            {settings.slots.map((slot) => (
              <DataListItem className="max-[680px]:text-left max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary grid gap-3 max-[680px]:gap-0" key={slot.slot}>
                <div className="max-[680px]:overflow-hidden min-w-0 grid gap-1 max-[680px]:gap-0">
                  <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">{slotLabel(slot.slot)}</strong>
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {slot.connection_id} / {slot.model_id}
                  </small>
                </div>
                <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap max-[680px]:gap-0 max-[680px]:px-0">
                  <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">{sourceLabel(slot.source)}</Badge>
                  {slot.source === 'overridden' ? (
                    <Button className="max-[680px]:text-left max-[680px]:justify-start max-[680px]:outline-offset-0 max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate max-[680px]:h-5 max-[680px]:w-full max-[680px]:basis-full max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:tracking-tighter max-[680px]:leading-none"
                      onClick={() => onResetProjectSlot(slot.slot)}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      Reset {slotLabel(slot.slot)} to Global
                    </Button>
                  ) : null}
                </DataListItemActions>
              </DataListItem>
            ))}
          </DataList>
        )}
      </section>
      <section className="grid gap-3 max-[680px]:gap-0">
        <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Chat Pool</h3>
        {settings.chat_models.length === 0 ? (
          <EmptyState
            className="max-[680px]:items-start max-[680px]:isolate max-[680px]:antialiased max-[680px]:touch-manipulation max-[680px]:min-w-0 max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:truncate p-4 text-left tracking-tight max-[680px]:p-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:border-primary/95 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:tracking-tighter max-[680px]:rounded-sm"
            data-slot-state="empty"
            role="status"
          >
            No Chat Models in the Project Pool Yet. Save a Global Chat Default or
            Sync Models.
          </EmptyState>
        ) : (
          <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
            {settings.chat_models.map((model) => (
              <DataListItem
                className="max-[680px]:text-left max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary grid gap-3 max-[680px]:gap-0"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <div className="min-w-0 grid gap-1 max-[680px]:gap-0">
                  <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {model.model_id}
                  </strong>
                  <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                    {model.connection_id}
                  </small>
                </div>
                <DataListItemActions className="max-[680px]:flex-col max-[680px]:items-stretch max-[680px]:touch-manipulation max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:flex-wrap max-[680px]:gap-0 max-[680px]:px-0">
                  <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">{sourceLabel(model.source)}</Badge>
                  <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone={model.is_default ? 'primary' : 'neutral'}>
                    {model.is_default ? 'Default' : 'Enabled'}
                  </Badge>
                </DataListItemActions>
              </DataListItem>
            ))}
          </DataList>
        )}
      </section>
      <section className="grid gap-3 max-[680px]:gap-0">
        <h3 className="max-[680px]:font-medium max-[680px]:truncate text-base font-semibold leading-none max-[680px]:text-[0.5rem] max-[680px]:leading-tight max-[680px]:tracking-tighter">Chat Retrieval</h3>
        <DataList className="max-[680px]:text-left max-[680px]:items-start max-[680px]:scroll-smooth max-[680px]:touch-manipulation max-[680px]:select-none max-[680px]:overscroll-contain max-[680px]:border max-[680px]:border-primary max-[680px]:rounded-sm max-[680px]:ring-offset-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary max-[680px]:overflow-hidden max-[680px]:gap-0">
          <DataListItem className="max-[680px]:text-left max-[680px]:items-start max-[680px]:touch-manipulation max-[680px]:overflow-hidden max-[680px]:rounded-sm max-[680px]:border max-[680px]:border-primary max-[680px]:p-0 max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary flex flex-wrap items-center justify-between gap-3 max-[680px]:gap-0">
            <div className="max-[680px]:overflow-hidden min-w-0 grid gap-1 max-[680px]:gap-0">
              <strong className="max-[680px]:font-medium max-[680px]:truncate text-sm font-semibold max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                Limit {settings.chat_retrieval.retrieval_limit}
              </strong>
              <small className="max-[680px]:truncate text-xs text-muted-foreground max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter">
                Candidate {settings.chat_retrieval.rerank_candidate_limit} /{' '}
                {settings.chat_retrieval.rerank_enabled ? 'Rerank On' : 'Rerank Off'}
              </small>
            </div>
            <Badge className="max-[680px]:text-left max-[680px]:self-start max-[680px]:tabular-nums max-[680px]:select-none max-[680px]:touch-manipulation max-[680px]:ring-offset-0 max-[680px]:overflow-hidden max-[680px]:shrink max-[680px]:truncate max-[680px]:rounded-sm max-[680px]:px-0 max-[680px]:text-[0.5rem] max-[680px]:leading-none max-[680px]:tracking-tighter" tone="neutral">
              {sourceLabel(settings.chat_retrieval.source)}
            </Badge>
          </DataListItem>
        </DataList>
      </section>
    </div>
  )
}
