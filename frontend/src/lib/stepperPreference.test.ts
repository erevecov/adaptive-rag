/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, test } from 'vitest'

import {
  STEPPER_EXPANDED_STORAGE_KEY,
  readStepperExpandedPreference,
  writeStepperExpandedPreference,
} from './stepperPreference'

function installLocalStorage(setItemImpl?: (key: string, value: string) => void) {
  const entries = new Map<string, string>()
  const storage = {
    get length() {
      return entries.size
    },
    clear() {
      entries.clear()
    },
    getItem(key: string) {
      return entries.get(key) ?? null
    },
    key(index: number) {
      return Array.from(entries.keys())[index] ?? null
    },
    removeItem(key: string) {
      entries.delete(key)
    },
    setItem(key: string, value: string) {
      if (setItemImpl !== undefined) {
        setItemImpl(key, value)
        return
      }
      entries.set(key, value)
    },
  } satisfies Storage

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage,
  })
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: storage,
  })
}

describe('stepperPreference', () => {
  beforeEach(() => {
    installLocalStorage()
  })

  test('reads true by default and persists explicit toggles', () => {
    expect(readStepperExpandedPreference()).toBe(true)

    writeStepperExpandedPreference(false)

    expect(localStorage.getItem(STEPPER_EXPANDED_STORAGE_KEY)).toBe('false')
    expect(readStepperExpandedPreference()).toBe(false)
  })

  test('ignores storage failures', () => {
    installLocalStorage(() => {
      throw new Error('storage unavailable')
    })

    expect(() => writeStepperExpandedPreference(false)).not.toThrow()
  })
})
