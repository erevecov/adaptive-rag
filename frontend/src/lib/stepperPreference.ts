export const STEPPER_EXPANDED_STORAGE_KEY =
  'adaptive-rag:chat-stepper-expanded'

export function readStepperExpandedPreference(): boolean {
  try {
    return localStorage.getItem(STEPPER_EXPANDED_STORAGE_KEY) !== 'false'
  } catch {
    return true
  }
}

export function writeStepperExpandedPreference(expanded: boolean): void {
  try {
    localStorage.setItem(STEPPER_EXPANDED_STORAGE_KEY, String(expanded))
  } catch {
    // Storage can be unavailable in private or embedded browser contexts.
  }
}
