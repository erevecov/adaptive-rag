/**
 * @vitest-environment jsdom
 */
import { describe, expect, test } from 'vitest'
import appShellSource from './AppShell.tsx?raw'
describe('AppShell ≤680 density', () => {
  test('sidebar nav and menu toggle use denser hover/active wash', () => {
    expect(appShellSource).toContain('max-[680px]:hover:bg-primary/65')
    expect(appShellSource).toContain('max-[680px]:active:bg-primary/95')
    expect(appShellSource).toContain('max-[680px]:bg-primary/45')
    expect(appShellSource).toContain('max-[680px]:pl-1')
  })
})
