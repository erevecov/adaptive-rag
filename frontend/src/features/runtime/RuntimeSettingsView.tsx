import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'

import type {
  ChatModel,
  ChatRetrievalSettings,
  ProjectRuntimeSettings,
  ProviderConnection,
  ProviderConnectionCheckResponse,
  ProviderModel,
  RuntimeSlotDefault,
} from '@/lib/apiClient'
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
  statusClassName,
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
    <div className="runtime-grid runtime-grid-focused">
      {error ? (
        <p className="form-feedback form-feedback-error" role="alert">
          {error}
        </p>
      ) : null}
      {activePanel}
    </div>
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
    <section className="panel runtime-panel" aria-labelledby="runtime-connections-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-connections-title">Connections</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <section className="runtime-section" aria-label="Provider connections">
        <h3>Connections</h3>
        <ul className="authoring-list">
          {connections.length === 0 ? (
            <li className="authoring-row authoring-row-static">
              <span>No runtime connections loaded.</span>
            </li>
          ) : (
            connections.map((connection) => {
              const isChecking =
                checkingConnectionId === connection.connection_id
              const checkResult =
                connectionCheckResults[connection.connection_id]
              return (
                <li
                  className="authoring-row authoring-row-static connection-row"
                  key={connection.connection_id}
                >
                  <span>
                    <strong>{connection.connection_id}</strong>
                    <small>
                      {connection.provider} / {connection.connection_type}
                    </small>
                    <small>{connection.capabilities.join(', ')}</small>
                    {connection.base_url ? (
                      <small>{connection.base_url}</small>
                    ) : null}
                    <ConnectionSecretSummary connection={connection} />
                    <ConnectionCheckSummary result={checkResult} />
                  </span>
                  <div className="authoring-row-actions connection-row-actions">
                    <em>{connection.connection_type}</em>
                    <button
                      aria-label={`Check ${connection.connection_id} connection`}
                      className="secondary-button compact-button"
                      disabled={state === 'loading' || isChecking}
                      onClick={() => onCheckConnection(connection.connection_id)}
                      type="button"
                    >
                      {isChecking ? 'Checking...' : 'Check'}
                    </button>
                    <button
                      aria-label={`Edit ${connection.connection_id} connection`}
                      className="secondary-button compact-button"
                      disabled={state === 'loading'}
                      onClick={() =>
                        onRequestEditConnection(connection.connection_id)
                      }
                      type="button"
                    >
                      Edit
                    </button>
                    <button
                      aria-label={`Delete ${connection.connection_id} connection`}
                      className="secondary-button compact-button danger-button"
                      disabled={state === 'loading'}
                      onClick={() =>
                        onRequestDeleteConnection(connection.connection_id)
                      }
                      type="button"
                    >
                      Delete
                    </button>
                  </div>
                  {deleteConnectionId === connection.connection_id ? (
                    <form
                      aria-label={`Delete ${connection.connection_id} connection`}
                      className="connection-delete-confirm"
                      onSubmit={onDeleteConnection}
                    >
                      <p>
                        Type <strong>{connection.connection_id}</strong> to confirm
                        deletion.
                      </p>
                      <label className="field">
                        <span>Confirm connection ID</span>
                        <input
                          autoComplete="off"
                          onChange={(event) =>
                            onDeleteConnectionConfirmationChange(
                              event.currentTarget.value,
                            )
                          }
                          value={deleteConnectionConfirmation}
                        />
                      </label>
                      <div className="connection-delete-actions">
                        <button
                          className="secondary-button compact-button"
                          disabled={state === 'loading'}
                          onClick={onCancelDeleteConnection}
                          type="button"
                        >
                          Cancel
                        </button>
                        <button
                          className="compact-button danger-button danger-button-solid"
                          disabled={
                            state === 'loading' ||
                            deleteConnectionConfirmation.trim() !==
                              connection.connection_id
                          }
                          type="submit"
                        >
                          Delete connection
                        </button>
                      </div>
                    </form>
                  ) : null}
                </li>
              )
            })
          )}
        </ul>
      </section>

      <form className="authoring-form" onSubmit={onSaveConnection}>
        <div className="connection-form-heading">
          <h3>
            {isEditingConnection
              ? `Edit connection ${editingConnectionId}`
              : 'New connection'}
          </h3>
          {isEditingConnection ? (
            <button
              className="secondary-button compact-button"
              disabled={state === 'loading'}
              onClick={onCancelEditConnection}
              type="button"
            >
              Cancel edit
            </button>
          ) : null}
        </div>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Provider</span>
            <select
              onChange={(event) =>
                onConnectionProviderChange(event.currentTarget.value)
              }
              value={connectionProvider}
            >
              <option value="qwen">qwen</option>
              <option value="local_openai_compatible">
                local_openai_compatible
              </option>
              <option value="fake">fake</option>
            </select>
          </label>
          <label className="field">
            <span>Connection type</span>
            <select
              onChange={(event) => onConnectionTypeChange(event.currentTarget.value)}
              value={connectionType}
            >
              <option value="hosted">hosted</option>
              <option value="local">local</option>
              <option value="fake">fake</option>
            </select>
          </label>
          <label className="field">
            <span>Base URL</span>
            <input
              onChange={(event) =>
                onConnectionBaseUrlChange(event.currentTarget.value)
              }
              value={connectionBaseUrl}
            />
          </label>
          <label className="field runtime-field-wide">
            <span>Capabilities</span>
            <CapabilitySelector
              options={PROVIDER_CONNECTION_CAPABILITIES}
              onChange={onConnectionCapabilitiesChange}
              value={connectionCapabilities}
            />
          </label>
          <label className="field runtime-field-wide">
            <span>API key</span>
            <input
              autoComplete="off"
              onChange={(event) => onConnectionApiKeyChange(event.currentTarget.value)}
              type="password"
              value={connectionApiKey}
            />
          </label>
        </div>
        <button disabled={!canSaveConnection} type="submit">
          {isEditingConnection ? 'Update connection' : 'Save connection'}
        </button>
      </form>
    </section>
  )
}

export function CapabilitySelector({
  onChange,
  options,
  value,
}: {
  onChange(value: string[]): void
  options: readonly string[]
  value: string[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement | null>(null)
  const rootRef = useRef<HTMLDivElement | null>(null)
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

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (
        rootRef.current !== null &&
        event.target instanceof Node &&
        !rootRef.current.contains(event.target)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
    }
  }, [isOpen])

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
    <div className="capability-selector" ref={rootRef}>
      <div
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Capabilities"
        className="capability-token-input"
        onClick={() => {
          setIsOpen(true)
          inputRef.current?.focus()
        }}
        role="combobox"
      >
        <div className="capability-token-wrap">
          {value.map((capability) => (
            <span className="capability-token" key={capability}>
              <span>{capability}</span>
              <button
                aria-label={`Remove ${capability} capability`}
                className="capability-token-remove"
                onClick={(event) => {
                  event.stopPropagation()
                  toggleCapability(capability)
                  inputRef.current?.focus()
                }}
                type="button"
              >
                x
              </button>
            </span>
          ))}
          <input
            aria-label="Filter capabilities"
            autoComplete="off"
            className="capability-filter-input"
            onChange={(event) => {
              setQuery(event.currentTarget.value)
              setIsOpen(true)
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleFilterKeyDown}
            placeholder={value.length === 0 ? 'Select capabilities' : ''}
            ref={inputRef}
            value={query}
          />
        </div>
        <span aria-hidden="true" className="capability-caret">
          v
        </span>
      </div>
      {isOpen ? (
        <div
          aria-label="Capability options"
          className="capability-menu"
          role="listbox"
        >
          {filteredOptions.length === 0 ? (
            <div className="capability-option-empty">No capabilities found</div>
          ) : (
            filteredOptions.map((capability) => (
              <button
                aria-label={`Add ${capability} capability`}
                className="capability-option"
                key={capability}
                onClick={() => {
                  toggleCapability(capability)
                  inputRef.current?.focus()
                }}
                role="option"
                type="button"
              >
                <span>{capability}</span>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
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
    <section className="panel runtime-panel" aria-labelledby="runtime-model-catalog-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-model-catalog-title">Model catalog</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh catalog'}
      </button>

      <form className="authoring-form" onSubmit={onSyncProviderModels}>
        <div className="runtime-form-grid">
          <label className="field runtime-field-wide">
            <span>Model sync connection</span>
            <ConnectionSelect
              connections={connections}
              onChange={onModelSyncConnectionIdChange}
              testId="model-sync-connection-select"
              value={modelSyncConnectionId}
            />
          </label>
        </div>
        <button type="submit">Sync models</button>
      </form>

      {selectedConnection ? (
        <section
          className="runtime-section"
          aria-label="Selected model sync connection"
        >
          <ul className="authoring-list">
            <li className="authoring-row authoring-row-static connection-row">
              <span>
                <strong>{connectionOptionLabel(selectedConnection)}</strong>
                <small>{selectedConnection.connection_id}</small>
                <small>{selectedConnection.capabilities.join(', ')}</small>
                {selectedConnection.base_url ? (
                  <small>{selectedConnection.base_url}</small>
                ) : null}
                <ConnectionSecretSummary connection={selectedConnection} />
              </span>
              <div className="authoring-row-actions connection-row-actions">
                <button
                  className="secondary-button compact-button"
                  disabled={state === 'loading'}
                  onClick={() =>
                    onEditConnection(selectedConnection.connection_id)
                  }
                  type="button"
                >
                  Edit connection
                </button>
              </div>
            </li>
          </ul>
        </section>
      ) : null}

      <ProviderModelCatalogView providerModels={providerModels} />
    </section>
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
    <section className="panel runtime-panel" aria-labelledby="runtime-global-defaults-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-global-defaults-title">Global defaults</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload global defaults'}
      </button>

      <RuntimeSlotList slots={slots} />

      <form className="authoring-form" onSubmit={onSaveGlobalSlot}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Global slot</span>
            <select
              data-testid="global-slot-select"
              onChange={(event) => onGlobalSlotChange(event.currentTarget.value)}
              value={globalSlot}
            >
              {RUNTIME_SLOTS.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Global slot connection</span>
            <ConnectionSelect
              connections={globalSlotConnections}
              onChange={onGlobalSlotConnectionIdChange}
              testId="global-slot-connection-select"
              value={globalSlotConnectionId}
            />
          </label>
          <label className="field">
            <span>Global slot model</span>
            <ProviderModelSelect
              models={globalSlotModelOptions}
              onChange={onGlobalSlotModelIdChange}
              testId="global-slot-model-select"
              value={globalSlotModelId}
            />
          </label>
        </div>
        {globalSlotSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">
            {globalSlotSyncMessage}
          </p>
        ) : null}
        <button disabled={globalSlotSyncMessage !== null} type="submit">
          Save global slot
        </button>
      </form>

      <section className="runtime-section" aria-label="Global chat models">
        <h3>Chat models</h3>
        <ul className="authoring-list">
          {chatModels.length === 0 ? (
            <li className="authoring-row authoring-row-static">
              <span>No chat models loaded.</span>
            </li>
          ) : (
            chatModels.map((model) => (
              <li
                className="authoring-row authoring-row-static"
                key={`${model.connection_id}-${model.model_id}`}
              >
                <span>
                  <strong>{model.model_id}</strong>
                  <small>{model.connection_id}</small>
                </span>
                <em>{model.is_default ? 'default' : 'enabled'}</em>
              </li>
            ))
          )}
        </ul>
      </section>

      <form className="authoring-form" onSubmit={onSaveGlobalChatModel}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Chat connection</span>
            <ConnectionSelect
              connections={chatConnections}
              onChange={onChatConnectionIdChange}
              testId="chat-connection-select"
              value={chatConnectionId}
            />
          </label>
          <label className="field">
            <span>Chat model</span>
            <ProviderModelSelect
              models={chatModelOptions}
              onChange={onChatModelIdChange}
              testId="chat-model-select"
              value={chatModelId}
            />
          </label>
        </div>
        {chatSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">{chatSyncMessage}</p>
        ) : null}
        <button disabled={chatSyncMessage !== null} type="submit">
          Save chat default
        </button>
      </form>

      <section className="runtime-section" aria-label="Global chat retrieval">
        <h3>Chat retrieval</h3>
        {chatRetrievalSettings ? (
          <ul className="authoring-list">
            <li className="authoring-row authoring-row-static">
              <span>
                <strong>global defaults</strong>
                <small>
                  limit {chatRetrievalSettings.retrieval_limit} / candidate{' '}
                  {chatRetrievalSettings.rerank_candidate_limit}
                </small>
              </span>
              <em>{chatRetrievalSettings.rerank_enabled ? 'rerank on' : 'rerank off'}</em>
            </li>
          </ul>
        ) : (
          <p className="empty-copy">No chat retrieval defaults loaded.</p>
        )}
        <form className="authoring-form" onSubmit={onSaveGlobalChatRetrieval}>
          <div className="runtime-form-grid">
            <label className="field">
              <span>Retrieval limit</span>
              <input
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
            </label>
            <label className="field">
              <span>Rerank</span>
              <select
                onChange={(event) =>
                  onGlobalChatRerankEnabledChange(
                    event.currentTarget.value === 'true',
                  )
                }
                value={String(globalChatRerankEnabled)}
              >
                <option value="true">on</option>
                <option value="false">off</option>
              </select>
            </label>
            <label className="field">
              <span>Candidate limit</span>
              <input
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
            </label>
          </div>
          <button type="submit">Save chat retrieval</button>
        </form>
      </section>
    </section>
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
    <section
      className="panel runtime-panel runtime-panel-wide"
      aria-label="Project runtime settings"
    >
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-project-overrides-title">Project overrides</h2>
        </div>
        <span className="status">{projectId.trim() || 'No project'}</span>
      </div>

      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload project settings'}
      </button>

      <ProjectRuntimeSettingsView
        onResetProjectSlot={onResetProjectSlot}
        settings={projectRuntimeSettings}
      />

      <form className="authoring-form" onSubmit={onSaveProjectChatRetrieval}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Retrieval limit</span>
            <input
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
          </label>
          <label className="field">
            <span>Rerank</span>
            <select
              onChange={(event) =>
                onProjectChatRerankEnabledChange(
                  event.currentTarget.value === 'true',
                )
              }
              value={String(projectChatRerankEnabled)}
            >
              <option value="true">on</option>
              <option value="false">off</option>
            </select>
          </label>
          <label className="field">
            <span>Candidate limit</span>
            <input
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
          </label>
        </div>
        <div className="authoring-row-actions">
          <button type="submit">Save project retrieval override</button>
          {projectRuntimeSettings?.chat_retrieval.source === 'project' ? (
            <button
              className="secondary-button"
              onClick={onResetProjectChatRetrieval}
              type="button"
            >
              Reset chat retrieval to global
            </button>
          ) : null}
        </div>
      </form>

      <form className="authoring-form" onSubmit={onSaveProjectOverride}>
        <div className="runtime-form-grid">
          <label className="field">
            <span>Project slot</span>
            <select
              onChange={(event) => onProjectSlotChange(event.currentTarget.value)}
              value={projectSlot}
            >
              {RUNTIME_SLOTS.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Project slot connection</span>
            <ConnectionSelect
              connections={projectSlotConnections}
              onChange={onProjectSlotConnectionIdChange}
              testId="project-slot-connection-select"
              value={projectSlotConnectionId}
            />
          </label>
          <label className="field">
            <span>Project slot model</span>
            <ProviderModelSelect
              models={projectSlotModelOptions}
              onChange={onProjectSlotModelIdChange}
              testId="project-slot-model-select"
              value={projectSlotModelId}
            />
          </label>
        </div>
        {projectSlotSyncMessage ? (
          <p className="form-feedback runtime-sync-hint">
            {projectSlotSyncMessage}
          </p>
        ) : null}
        <button disabled={projectSlotSyncMessage !== null} type="submit">
          Save project override
        </button>
      </form>
    </section>
  )
}

export function ConnectionSecretSummary({
  connection,
}: {
  connection: ProviderConnection
}) {
  if (connection.secrets.length === 0) {
    return <small>No secret status</small>
  }
  return (
    <>
      {connection.secrets.map((secret) => (
        <small key={secret.secret_name}>
          {secret.secret_name}{' '}
          {secret.configured ? 'configured' : 'not configured'}
          {secret.last_four ? ` / last four ${secret.last_four}` : ''}
        </small>
      ))}
    </>
  )
}

export function ConnectionCheckSummary({
  result,
}: {
  result: ProviderConnectionCheckResponse | undefined
}) {
  if (result === undefined) {
    return null
  }

  return (
    <small
      className={
        result.ok
          ? 'connection-check-result connection-check-result-ok'
          : 'connection-check-result connection-check-result-error'
      }
    >
      {result.ok
        ? `Connection check passed: ${result.model_count} provider models reachable.`
        : `Connection check failed: ${result.message}`}
    </small>
  )
}

export function ConnectionSelect({
  connections,
  onChange,
  testId,
  value,
}: {
  connections: ProviderConnection[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <select
      data-testid={testId}
      onChange={(event) => onChange(event.currentTarget.value)}
      value={value}
    >
      <option value="">
        {connections.length === 0 ? 'No connections loaded' : 'Select connection'}
      </option>
      {connections.map((connection) => (
        <option key={connection.connection_id} value={connection.connection_id}>
          {connectionOptionLabel(connection)}
        </option>
      ))}
    </select>
  )
}

export function ProviderModelSelect({
  models,
  onChange,
  testId,
  value,
}: {
  models: ProviderModelOption[]
  onChange(value: string): void
  testId?: string
  value: string
}) {
  return (
    <select
      data-testid={testId}
      disabled={models.length === 0}
      onChange={(event) => onChange(event.currentTarget.value)}
      value={value}
    >
      <option value="">
        {models.length === 0 ? 'No models loaded' : 'Select model'}
      </option>
      {models.map((model) => (
        <option key={`${model.connection_id}-${model.model_id}`} value={model.model_id}>
          {model.model_id}
        </option>
      ))}
    </select>
  )
}

export function ProviderModelCatalogView({
  providerModels,
}: {
  providerModels: ProviderModel[]
}) {
  return (
    <section className="runtime-section" aria-label="Provider model catalog">
      <h3>Model catalog</h3>
      <ul className="authoring-list">
        {providerModels.length === 0 ? (
          <li className="authoring-row authoring-row-static">
            <span>No provider models loaded.</span>
          </li>
        ) : (
          providerModels.map((model) => (
            <li
              className="authoring-row authoring-row-static"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <span>
                <strong>{model.model_id}</strong>
                <small>
                  {model.connection_id} / {model.capabilities.join(', ')}
                </small>
                {model.pricing ? <small>pricing metadata saved</small> : null}
              </span>
              <em>{model.pricing ? 'pricing' : 'metadata'}</em>
            </li>
          ))
        )}
      </ul>
    </section>
  )
}

export function RuntimeSlotList({ slots }: { slots: RuntimeSlotDefault[] }) {
  return (
    <ul className="authoring-list" aria-label="Global runtime slots">
      {slots.length === 0 ? (
        <li className="authoring-row authoring-row-static">
          <span>No global slot defaults loaded.</span>
        </li>
      ) : (
        slots.map((slot) => (
          <li className="authoring-row authoring-row-static" key={slot.slot}>
            <span>
              <strong>{slot.slot}</strong>
              <small>
                {slot.connection_id} / {slot.model_id}
              </small>
            </span>
            <em>global</em>
          </li>
        ))
      )}
    </ul>
  )
}

export function ProjectRuntimeSettingsView({
  onResetProjectSlot,
  settings,
}: {
  onResetProjectSlot(slot: string): void
  settings: ProjectRuntimeSettings | null
}) {
  if (settings === null) {
    return <p className="empty-copy">No project runtime settings loaded.</p>
  }
  return (
    <div className="project-runtime-grid">
      <section className="runtime-section">
        <h3>Effective slots</h3>
        <ul className="authoring-list">
          {settings.slots.map((slot) => (
            <li className="authoring-row authoring-row-static" key={slot.slot}>
              <span>
                <strong>{slot.slot}</strong>
                <small>
                  {slot.connection_id} / {slot.model_id}
                </small>
              </span>
              <div className="authoring-row-actions">
                <em>{slot.source}</em>
                {slot.source === 'overridden' ? (
                  <button
                    className="compact-button"
                    onClick={() => onResetProjectSlot(slot.slot)}
                    type="button"
                  >
                    Reset {slot.slot} to global
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="runtime-section">
        <h3>Chat pool</h3>
        <ul className="authoring-list">
          {settings.chat_models.map((model) => (
            <li
              className="authoring-row authoring-row-static"
              key={`${model.connection_id}-${model.model_id}`}
            >
              <span>
                <strong>{model.model_id}</strong>
                <small>{model.connection_id}</small>
              </span>
              <div className="authoring-row-actions">
                <em>{model.source}</em>
                <em>{model.is_default ? 'default' : 'enabled'}</em>
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="runtime-section">
        <h3>Chat retrieval</h3>
        <ul className="authoring-list">
          <li className="authoring-row authoring-row-static">
            <span>
              <strong>
                limit {settings.chat_retrieval.retrieval_limit}
              </strong>
              <small>
                candidate {settings.chat_retrieval.rerank_candidate_limit} /{' '}
                {settings.chat_retrieval.rerank_enabled ? 'rerank on' : 'rerank off'}
              </small>
            </span>
            <em>{settings.chat_retrieval.source}</em>
          </li>
        </ul>
      </section>
    </div>
  )
}
