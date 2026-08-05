import { type RefObject, useEffect } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function listFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  ).filter((el) => {
    if (el.closest('[inert]')) {
      return false
    }
    if (el.closest('[aria-hidden="true"]')) {
      return false
    }
    // Prefer computed style over getClientRects — jsdom often returns empty rects.
    const style = window.getComputedStyle(el)
    if (style.display === 'none' || style.visibility === 'hidden') {
      return false
    }
    return true
  })
}

/**
 * Traps Tab/Shift+Tab inside `containerRef` while `active`.
 * Restores focus to the previously focused element on deactivate.
 */
export function useFocusTrap(
  containerRef: RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    if (!active) {
      return
    }

    const container = containerRef.current
    if (container === null) {
      return
    }

    const previouslyFocused =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null

    const focusables = listFocusable(container)
    const initial = focusables[0] ?? container
    if (!container.contains(document.activeElement)) {
      initial.focus()
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Tab') {
        return
      }
      const node = containerRef.current
      if (node === null) {
        return
      }
      const items = listFocusable(node)
      if (items.length === 0) {
        event.preventDefault()
        node.focus()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      const current = document.activeElement
      if (event.shiftKey) {
        if (current === first || !node.contains(current)) {
          event.preventDefault()
          last.focus()
        }
        return
      }
      if (current === last || !node.contains(current)) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      if (
        previouslyFocused !== null &&
        previouslyFocused.isConnected &&
        typeof previouslyFocused.focus === 'function'
      ) {
        previouslyFocused.focus()
      }
    }
  }, [active, containerRef])
}
