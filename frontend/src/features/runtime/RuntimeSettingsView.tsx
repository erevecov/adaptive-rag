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
  connectionsForCapability,
  missingSyncedModelMessage,
  normalizeChatRetrievalLimit,
  providerModelOptions,
  runtimeStatusLabel,
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
    <div className="grid gap-4">
      {error ? (
        <Callout className="p-3" role="alert" tone="danger">
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
      <PanelHeader className="min-w-0 flex-col items-start justify-between gap-3 p-4 sm:flex-row">
        <div className="grid min-w-0 gap-1">
          <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
            Runtime
          </p>
          <h2 id={id} className="text-lg font-semibold leading-none">
            {title}
          </h2>
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

function RuntimeStatus({ state }: { state: RequestState }) {
  return (
    <StatusBadge
      className="max-w-full break-all text-left"
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
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <FieldControl>{children(id)}</FieldControl>
      {help ? <FieldHelp>{help}</FieldHelp> : null}
      {error ? <FieldError>{error}</FieldError> : null}
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
      <section aria-label="Provider connections" className="grid gap-3">
        {state === 'loading' && connections.length === 0 ? (
          <EmptyState
            aria-busy="true"
            className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
            data-slot-state="loading"
            role="status"
          >
            Loading connections…
          </EmptyState>
        ) : connections.length === 0 ? (
          <EmptyState className="p-4 text-left" data-slot-state="empty" role="status">
            No connections yet.
          </EmptyState>
        ) : (
          <DataList>
            {connections.map((connection) => {
              const isChecking =
                checkingConnectionId === connection.connection_id
              const checkResult =
                connectionCheckResults[connection.connection_id]
              return (
                <DataListItem
                  aria-busy={isChecking || undefined}
                  className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
                  key={connection.connection_id}
                >
                  <div className="grid min-w-0 gap-2">
                    <div className="grid gap-1">
                      <strong className="truncate font-mono text-xs font-semibold">
                        {connection.connection_id}
                      </strong>
                      <div className="flex flex-wrap gap-2">
                        <Badge className="max-w-full truncate">
                          {connection.provider} / {connection.connection_type}
                        </Badge>
                        <Badge className="max-w-full truncate" tone="neutral">
                          {connection.capabilities.join(', ')}
                        </Badge>
                        {isChecking ? (
                          <StatusBadge role="status" tone="warning">
                            Checking…
                          </StatusBadge>
                        ) : null}
                      </div>
                      {connection.base_url ? (
                        <small className="break-all text-xs text-muted-foreground">
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
                  <DataListItemActions className="justify-start md:justify-end">
                    <Button
                      aria-label={`Check ${connection.connection_id} connection`}
                      disabled={state === 'loading' || isChecking}
                      onClick={() => onCheckConnection(connection.connection_id)}
                      size="sm"
                      variant="secondary"
                    >
                      {isChecking ? 'Checking...' : 'Check'}
                    </Button>
                    <Button
                      aria-label={`Edit ${connection.connection_id} connection`}
                      disabled={state === 'loading'}
                      onClick={() =>
                        onRequestEditConnection(connection.connection_id)
                      }
                      size="sm"
                      variant="secondary"
                    >
                      Edit
                    </Button>
                    <Button
                      aria-label={`Delete ${connection.connection_id} connection`}
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
                      aria-label={`Delete ${connection.connection_id} connection`}
                      className="grid gap-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 md:col-span-2"
                      onSubmit={onDeleteConnection}
                    >
                      <InlineFeedback tone="danger">
                        Type <strong>{connection.connection_id}</strong> to confirm
                        deletion.
                      </InlineFeedback>
                      <RuntimeField
                        id={`delete-${connection.connection_id}-confirmation`}
                        label="Confirm connection ID"
                      >
                        {(fieldId) => (
                          <Input
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
                      <DataListItemActions>
                        <Button
                          disabled={state === 'loading'}
                          onClick={onCancelDeleteConnection}
                          size="sm"
                          variant="secondary"
                        >
                          Cancel
                        </Button>
                        <Button
                          disabled={
                            state === 'loading' ||
                            deleteConnectionConfirmation.trim() !==
                              connection.connection_id
                          }
                          size="sm"
                          type="submit"
                          variant="danger"
                        >
                          Delete connection
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

      <form className="grid gap-4" onSubmit={onSaveConnection}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-base font-semibold leading-none">
            {isEditingConnection
              ? `Edit connection ${editingConnectionId}`
              : 'New connection'}
          </h3>
          {isEditingConnection ? (
            <Button
              disabled={state === 'loading'}
              onClick={onCancelEditConnection}
              size="sm"
              variant="secondary"
            >
              Cancel edit
            </Button>
          ) : null}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <RuntimeField id="runtime-connection-provider" label="Provider">
            {(fieldId) => (
              <Select
                id={fieldId}
                onValueChange={onConnectionProviderChange}
                options={[
                  { label: 'qwen', value: 'qwen' },
                  {
                    label: 'local_openai_compatible',
                    value: 'local_openai_compatible',
                  },
                  { label: 'fake', value: 'fake' },
                ]}
                value={connectionProvider}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-connection-type"
            label="Connection type"
          >
            {(fieldId) => (
              <Select
                id={fieldId}
                onValueChange={onConnectionTypeChange}
                options={[
                  { label: 'hosted', value: 'hosted' },
                  { label: 'local', value: 'local' },
                  { label: 'fake', value: 'fake' },
                ]}
                value={connectionType}
              />
            )}
          </RuntimeField>
          <RuntimeField id="runtime-connection-base-url" label="Base URL">
            {(fieldId) => (
              <Input
                id={fieldId}
                onChange={(event) =>
                  onConnectionBaseUrlChange(event.currentTarget.value)
                }
                value={connectionBaseUrl}
              />
            )}
          </RuntimeField>
          <Field className="md:col-span-2">
            <FieldLabel
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
                ? 'Leave blank to keep the existing key. A new value replaces it.'
                : undefined
            }
            id="runtime-connection-api-key"
            label="API key"
          >
            {(fieldId) => (
              <Input
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
        <Button disabled={!canSaveConnection} type="submit">
          {isEditingConnection ? 'Update connection' : 'Save connection'}
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
            className="flex min-h-9 w-full items-center gap-2 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground motion-safe:transition-colors focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background data-[state=open]:ring-2 data-[state=open]:ring-ring data-[state=open]:ring-offset-2 data-[state=open]:ring-offset-background"
            onClick={() => {
              setIsOpen(true)
              inputRef.current?.focus()
            }}
          >
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
              {value.map((capability) => (
                <Badge className="gap-1 pr-1" key={capability} tone="primary">
                  <span>{capability}</span>
                  <Button
                    aria-label={`Remove ${capability} capability`}
                    className="h-5 px-1 text-xs"
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
                    x
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
                className="h-7 min-w-32 flex-1 border-0 bg-transparent px-0 py-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
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
                placeholder={value.length === 0 ? 'Select capabilities' : ''}
                ref={inputRef}
                role="combobox"
                value={query}
              />
            </div>
            <ChevronDown
              aria-hidden="true"
              className="size-4 text-muted-foreground"
            />
          </div>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            aria-label="Capability options"
            className="z-20 grid max-h-60 w-[var(--radix-popover-trigger-width)] gap-1 overflow-auto rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md"
            id={listboxId}
            onOpenAutoFocus={(event) => {
              event.preventDefault()
              inputRef.current?.focus()
            }}
            role="listbox"
            side="bottom"
            sideOffset={4}
          >
            {filteredOptions.length === 0 ? (
              <p className="p-3 text-left text-sm text-muted-foreground" role="status">
                No capabilities found
              </p>
            ) : (
              filteredOptions.map((capability) => (
                <Button
                  aria-label={`Add ${capability} capability`}
                  aria-selected={false}
                  className="justify-start"
                  key={capability}
                  onClick={() => {
                    toggleCapability(capability)
                    inputRef.current?.focus()
                  }}
                  role="option"
                  type="button"
                  variant="ghost"
                >
                  <span>{capability}</span>
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
      title="Model catalog"
    >
      <Button
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh catalog'}
      </Button>

      <form className="grid gap-4" onSubmit={onSyncProviderModels}>
        <RuntimeField
          id="runtime-model-sync-connection"
          label="Model sync connection"
        >
          {(fieldId) => (
            <ConnectionSelect
              connections={connections}
              id={fieldId}
              onChange={onModelSyncConnectionIdChange}
              testId="model-sync-connection-select"
              value={modelSyncConnectionId}
            />
          )}
        </RuntimeField>
        <Button type="submit">Sync models</Button>
      </form>

      {selectedConnection ? (
        <section
          aria-label="Selected model sync connection"
          className="grid gap-3"
        >
          <DataList>
            <DataListItem className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
              <div className="grid min-w-0 gap-2">
                <div className="grid gap-1">
                  <strong className="text-sm font-semibold">
                    {connectionOptionLabel(selectedConnection)}
                  </strong>
                  <small className="text-xs text-muted-foreground">
                    {selectedConnection.connection_id}
                  </small>
                  <Badge tone="neutral">
                    {selectedConnection.capabilities.join(', ')}
                  </Badge>
                  {selectedConnection.base_url ? (
                    <small className="break-all text-xs text-muted-foreground">
                      {selectedConnection.base_url}
                    </small>
                  ) : null}
                </div>
                <ConnectionSecretSummary connection={selectedConnection} />
              </div>
              <DataListItemActions className="justify-start md:justify-end">
                <Button
                  disabled={state === 'loading'}
                  onClick={() =>
                    onEditConnection(selectedConnection.connection_id)
                  }
                  size="sm"
                  variant="secondary"
                >
                  Edit connection
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
      title="Global defaults"
    >
      <Button
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload global defaults'}
      </Button>

      <RuntimeSlotList isLoading={state === 'loading'} slots={slots} />

      <form className="grid gap-4" onSubmit={onSaveGlobalSlot}>
        <div className="grid gap-4 md:grid-cols-3">
          <RuntimeField id="runtime-global-slot" label="Global slot">
            {(fieldId) => (
              <Select
                data-testid="global-slot-select"
                id={fieldId}
                onValueChange={onGlobalSlotChange}
                options={RUNTIME_SLOTS.map((slot) => ({
                  label: slot,
                  value: slot,
                }))}
                value={globalSlot}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-global-slot-connection"
            label="Global slot connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={globalSlotConnections}
                id={fieldId}
                onChange={onGlobalSlotConnectionIdChange}
                testId="global-slot-connection-select"
                value={globalSlotConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-global-slot-model"
            label="Global slot model"
          >
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                models={globalSlotModelOptions}
                onChange={onGlobalSlotModelIdChange}
                testId="global-slot-model-select"
                value={globalSlotModelId}
              />
            )}
          </RuntimeField>
        </div>
        {globalSlotSyncMessage ? (
          <InlineFeedback role="status" tone="warning">
            {globalSlotSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button disabled={globalSlotSyncMessage !== null} type="submit">
          Save global slot
        </Button>
      </form>

      <section aria-label="Global chat models" className="grid gap-3">
        <h3 className="text-base font-semibold leading-none">Chat models</h3>
        {state === 'loading' && chatModels.length === 0 ? (
          <EmptyState
            aria-busy="true"
            className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
            data-slot-state="loading"
            role="status"
          >
            Loading chat models…
          </EmptyState>
        ) : chatModels.length === 0 ? (
          <EmptyState className="p-4 text-left" data-slot-state="empty" role="status">
            No chat models yet.
          </EmptyState>
        ) : (
          <DataList>
            {chatModels.map((model) => (
              <DataListItem
                className="flex flex-wrap items-center justify-between gap-3"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <div className="grid gap-1">
                  <strong className="text-sm font-semibold">
                    {model.model_id}
                  </strong>
                  <small className="text-xs text-muted-foreground">
                    {model.connection_id}
                  </small>
                </div>
                <Badge tone={model.is_default ? 'primary' : 'neutral'}>
                  {model.is_default ? 'default' : 'enabled'}
                </Badge>
              </DataListItem>
            ))}
          </DataList>
        )}
      </section>

      <form className="grid gap-4" onSubmit={onSaveGlobalChatModel}>
        <div className="grid gap-4 md:grid-cols-2">
          <RuntimeField
            id="runtime-chat-connection"
            label="Chat connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={chatConnections}
                id={fieldId}
                onChange={onChatConnectionIdChange}
                testId="chat-connection-select"
                value={chatConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField id="runtime-chat-model" label="Chat model">
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                models={chatModelOptions}
                onChange={onChatModelIdChange}
                testId="chat-model-select"
                value={chatModelId}
              />
            )}
          </RuntimeField>
        </div>
        {chatSyncMessage ? (
          <InlineFeedback role="status" tone="warning">
            {chatSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button disabled={chatSyncMessage !== null} type="submit">
          Save chat default
        </Button>
      </form>

      <section aria-label="Global chat retrieval" className="grid gap-3">
        <h3 className="text-base font-semibold leading-none">Chat retrieval</h3>
        {state === 'loading' && chatRetrievalSettings === null ? (
          <EmptyState
            aria-busy="true"
            className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
            data-slot-state="loading"
            role="status"
          >
            Loading chat retrieval defaults…
          </EmptyState>
        ) : chatRetrievalSettings ? (
          <DataList>
            <DataListItem className="flex flex-wrap items-center justify-between gap-3">
              <div className="grid gap-1">
                <strong className="text-sm font-semibold">
                  global defaults
                </strong>
                <small className="text-xs text-muted-foreground">
                  limit {chatRetrievalSettings.retrieval_limit} / candidate{' '}
                  {chatRetrievalSettings.rerank_candidate_limit}
                </small>
              </div>
              <Badge tone="neutral">
                {chatRetrievalSettings.rerank_enabled
                  ? 'rerank on'
                  : 'rerank off'}
              </Badge>
            </DataListItem>
          </DataList>
        ) : (
          <EmptyState className="p-4 text-left" data-slot-state="empty" role="status">
            No chat retrieval defaults yet.
          </EmptyState>
        )}
        <form className="grid gap-4" onSubmit={onSaveGlobalChatRetrieval}>
          <div className="grid gap-4 md:grid-cols-3">
            <RuntimeField
              id="runtime-global-retrieval-limit"
              label="Retrieval limit"
            >
              {(fieldId) => (
                <Input
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
                  id={fieldId}
                  onValueChange={(nextValue) =>
                    onGlobalChatRerankEnabledChange(nextValue === 'true')
                  }
                  options={[
                    { label: 'on', value: 'true' },
                    { label: 'off', value: 'false' },
                  ]}
                  value={String(globalChatRerankEnabled)}
                />
              )}
            </RuntimeField>
            <RuntimeField
              id="runtime-global-candidate-limit"
              label="Candidate limit"
            >
              {(fieldId) => (
                <Input
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
          <Button type="submit">Save chat retrieval</Button>
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
      ariaLabel="Project runtime settings"
      id="runtime-project-overrides-title"
      status={
        <div className="flex max-w-full min-w-0 flex-wrap items-start justify-end gap-2">
          <RuntimeStatus state={state} />
          <StatusBadge className="max-w-full break-all text-left" tone="neutral">
            {projectId.trim() || 'No project'}
          </StatusBadge>
        </div>
      }
      title="Project overrides"
    >
      <Button
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
        variant="secondary"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload project settings'}
      </Button>

      <ProjectRuntimeSettingsView
        onResetProjectSlot={onResetProjectSlot}
        settings={projectRuntimeSettings}
        state={state}
      />

      <form className="grid gap-4" onSubmit={onSaveProjectChatRetrieval}>
        <div className="grid gap-4 md:grid-cols-3">
          <RuntimeField
            id="runtime-project-retrieval-limit"
            label="Retrieval limit"
          >
            {(fieldId) => (
              <Input
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
                id={fieldId}
                onValueChange={(nextValue) =>
                  onProjectChatRerankEnabledChange(nextValue === 'true')
                }
                options={[
                  { label: 'on', value: 'true' },
                  { label: 'off', value: 'false' },
                ]}
                value={String(projectChatRerankEnabled)}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-candidate-limit"
            label="Candidate limit"
          >
            {(fieldId) => (
              <Input
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
        <DataListItemActions>
          <Button type="submit">Save project retrieval override</Button>
          {projectRuntimeSettings?.chat_retrieval.source === 'project' ? (
            <Button
              onClick={onResetProjectChatRetrieval}
              type="button"
              variant="secondary"
            >
              Reset chat retrieval to global
            </Button>
          ) : null}
        </DataListItemActions>
      </form>

      <form className="grid gap-4" onSubmit={onSaveProjectOverride}>
        <div className="grid gap-4 md:grid-cols-3">
          <RuntimeField id="runtime-project-slot" label="Project slot">
            {(fieldId) => (
              <Select
                id={fieldId}
                onValueChange={onProjectSlotChange}
                options={RUNTIME_SLOTS.map((slot) => ({
                  label: slot,
                  value: slot,
                }))}
                value={projectSlot}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-slot-connection"
            label="Project slot connection"
          >
            {(fieldId) => (
              <ConnectionSelect
                connections={projectSlotConnections}
                id={fieldId}
                onChange={onProjectSlotConnectionIdChange}
                testId="project-slot-connection-select"
                value={projectSlotConnectionId}
              />
            )}
          </RuntimeField>
          <RuntimeField
            id="runtime-project-slot-model"
            label="Project slot model"
          >
            {(fieldId) => (
              <ProviderModelSelect
                id={fieldId}
                models={projectSlotModelOptions}
                onChange={onProjectSlotModelIdChange}
                testId="project-slot-model-select"
                value={projectSlotModelId}
              />
            )}
          </RuntimeField>
        </div>
        {projectSlotSyncMessage ? (
          <InlineFeedback role="status" tone="warning">
            {projectSlotSyncMessage}
          </InlineFeedback>
        ) : null}
        <Button disabled={projectSlotSyncMessage !== null} type="submit">
          Save project override
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
      <small className="text-xs text-muted-foreground">
        {connection.connection_type === 'fake'
          ? 'Secrets not required for this connection'
          : 'No API key on file'}
      </small>
    )
  }
  return (
    <div className="flex flex-wrap gap-2">
      {connection.secrets.map((secret) => (
        <Badge key={secret.secret_name} tone={secret.configured ? 'success' : 'neutral'}>
          {secret.secret_name}{' '}
          {secret.configured ? 'configured' : 'not configured'}
          {secret.last_four ? ` / last four ${secret.last_four}` : ''}
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
      <InlineFeedback aria-live="polite" role="status" tone="warning">
        Checking connection…
      </InlineFeedback>
    )
  }

  if (result === undefined) {
    return (
      <small className="text-xs text-muted-foreground">Not checked</small>
    )
  }

  if (result.ok) {
    return (
      <Callout
        aria-live="polite"
        className="p-2"
        role="status"
        tone="success"
      >
        Connection check passed: {result.model_count} provider models reachable.
      </Callout>
    )
  }

  return (
    <Callout className="p-2" role="alert" tone="danger">
      Connection check failed. Verify base URL, capabilities, and API key.
      {result.message.trim().length > 0 ? (
        <span className="mt-1 block text-xs opacity-90">
          {operatorSafeMessage(result.message, 'Provider rejected the check.')}
        </span>
      ) : null}
    </Callout>
  )
}

export function ConnectionSelect({
  connections,
  id,
  onChange,
  testId,
  value,
}: {
  connections: ProviderConnection[]
  id?: string
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <Select
      data-testid={testId}
      id={id}
      onValueChange={onChange}
      options={[
        {
          label:
            connections.length === 0
              ? 'No connections yet'
              : 'Select connection',
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
  models,
  onChange,
  testId,
  value,
}: {
  id?: string
  models: ProviderModelOption[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <Select
      data-testid={testId}
      disabled={models.length === 0}
      id={id}
      onValueChange={onChange}
      options={[
        {
          label: models.length === 0 ? 'No models yet' : 'Select model',
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
    <section aria-label="Provider model catalog" className="grid gap-3">
      <h3 className="text-base font-semibold leading-none">Model catalog</h3>
      {isLoading && providerModels.length === 0 ? (
        <EmptyState
          aria-busy="true"
          className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
          data-slot-state="loading"
          role="status"
        >
          Loading provider models…
        </EmptyState>
      ) : providerModels.length === 0 ? (
        <EmptyState className="p-4 text-left" data-slot-state="empty" role="status">
          No provider models yet.
        </EmptyState>
      ) : (
        <DataList>
          {providerModels.map((model) => (
            <DataListItem
              className="flex flex-wrap items-center justify-between gap-3"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <div className="grid gap-1">
                <strong className="text-sm font-semibold">
                  {model.model_id}
                </strong>
                <small className="text-xs text-muted-foreground">
                  {model.connection_id} / {model.capabilities.join(', ')}
                </small>
                {model.pricing ? (
                  <small className="text-xs text-muted-foreground">
                    pricing metadata saved
                  </small>
                ) : null}
              </div>
              <Badge tone={model.pricing ? 'primary' : 'neutral'}>
                {model.pricing ? 'pricing' : 'metadata'}
              </Badge>
            </DataListItem>
          ))}
        </DataList>
      )}
    </section>
  )
}

export function RuntimeSlotList({
  isLoading = false,
  slots,
}: {
  isLoading?: boolean
  slots: RuntimeSlotDefault[]
}) {
  if (isLoading && slots.length === 0) {
    return (
      <EmptyState
        aria-busy="true"
        className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
        data-slot-state="loading"
        role="status"
      >
        Loading global slots…
      </EmptyState>
    )
  }
  if (slots.length === 0) {
    return (
      <EmptyState
        className="p-4 text-left"
        data-slot-state="empty"
        role="status"
      >
        No global slot defaults yet. Save a global slot below.
      </EmptyState>
    )
  }
  return (
    <DataList aria-label="Global runtime slots">
      {slots.map((slot) => (
        <DataListItem
          className="flex flex-wrap items-center justify-between gap-3"
          key={slot.slot}
        >
          <div className="grid gap-1">
            <strong className="text-sm font-semibold">{slot.slot}</strong>
            <small className="text-xs text-muted-foreground">
              {slot.connection_id} / {slot.model_id}
            </small>
          </div>
          <Badge tone="neutral">global</Badge>
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
        className="border-border/60 bg-muted/20 p-4 text-left motion-safe:animate-pulse"
        data-slot-state="loading"
        role="status"
      >
        Loading project runtime settings…
      </EmptyState>
    )
  }
  if (settings === null) {
    return (
      <EmptyState className="p-4 text-left" data-slot-state="empty" role="status">
        No project runtime settings yet.
      </EmptyState>
    )
  }
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <section className="grid gap-3">
        <h3 className="text-base font-semibold leading-none">Effective slots</h3>
        <DataList>
          {settings.slots.map((slot) => (
            <DataListItem className="grid gap-3" key={slot.slot}>
              <div className="grid gap-1">
                <strong className="text-sm font-semibold">{slot.slot}</strong>
                <small className="text-xs text-muted-foreground">
                  {slot.connection_id} / {slot.model_id}
                </small>
              </div>
              <DataListItemActions>
                <Badge tone="neutral">{slot.source}</Badge>
                {slot.source === 'overridden' ? (
                  <Button
                    onClick={() => onResetProjectSlot(slot.slot)}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    Reset {slot.slot} to global
                  </Button>
                ) : null}
              </DataListItemActions>
            </DataListItem>
          ))}
        </DataList>
      </section>
      <section className="grid gap-3">
        <h3 className="text-base font-semibold leading-none">Chat pool</h3>
        {settings.chat_models.length === 0 ? (
          <EmptyState
            className="p-4 text-left"
            data-slot-state="empty"
            role="status"
          >
            No chat models in the project pool yet. Save a global chat default or
            sync models.
          </EmptyState>
        ) : (
          <DataList>
            {settings.chat_models.map((model) => (
              <DataListItem
                className="grid gap-3"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <div className="grid gap-1">
                  <strong className="text-sm font-semibold">
                    {model.model_id}
                  </strong>
                  <small className="text-xs text-muted-foreground">
                    {model.connection_id}
                  </small>
                </div>
                <DataListItemActions>
                  <Badge tone="neutral">{model.source}</Badge>
                  <Badge tone={model.is_default ? 'primary' : 'neutral'}>
                    {model.is_default ? 'default' : 'enabled'}
                  </Badge>
                </DataListItemActions>
              </DataListItem>
            ))}
          </DataList>
        )}
      </section>
      <section className="grid gap-3">
        <h3 className="text-base font-semibold leading-none">Chat retrieval</h3>
        <DataList>
          <DataListItem className="flex flex-wrap items-center justify-between gap-3">
            <div className="grid gap-1">
              <strong className="text-sm font-semibold">
                limit {settings.chat_retrieval.retrieval_limit}
              </strong>
              <small className="text-xs text-muted-foreground">
                candidate {settings.chat_retrieval.rerank_candidate_limit} /{' '}
                {settings.chat_retrieval.rerank_enabled ? 'rerank on' : 'rerank off'}
              </small>
            </div>
            <Badge tone="neutral">{settings.chat_retrieval.source}</Badge>
          </DataListItem>
        </DataList>
      </section>
    </div>
  )
}
