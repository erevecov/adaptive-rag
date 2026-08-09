/**
 * Exclusive open state for chat "Details" panels in the transcript.
 * Only one instance id may be open at a time; default is all closed.
 */
type Listener = () => void

let openInstanceId: string | null = null
const listeners = new Set<Listener>()

export function getOpenDetailsInstanceId(): string | null {
  return openInstanceId
}

export function setOpenDetailsInstanceId(instanceId: string | null): void {
  if (openInstanceId === instanceId) {
    return
  }
  openInstanceId = instanceId
  for (const listener of listeners) {
    listener()
  }
}

/** Open this id, or close it if it is already the open one. */
export function toggleOpenDetailsInstanceId(instanceId: string): void {
  setOpenDetailsInstanceId(
    openInstanceId === instanceId ? null : instanceId,
  )
}

export function subscribeOpenDetailsInstance(
  listener: Listener,
): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Test helper — clears exclusive open state. */
export function resetOpenDetailsInstanceIdForTests(): void {
  openInstanceId = null
  for (const listener of listeners) {
    listener()
  }
}
