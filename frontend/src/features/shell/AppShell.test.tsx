/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { AppShell, AppSidebar } from './AppShell'
import appShellSource from './AppShell.tsx?raw'

afterEach(() => {
  cleanup()
})

describe('AppShell ≤680 density', () => {
  test('sidebar nav and menu toggle use denser hover/active wash', () => {
    expect(appShellSource).toContain('max-[680px]:hover:bg-primary/65')
    expect(appShellSource).toContain('max-[680px]:active:bg-primary/95')
    expect(appShellSource).toContain(
      'max-[680px]:[&_[data-slot=sidebar-item][data-active]]:bg-primary/45',
    )
    expect(appShellSource).toContain('max-[680px]:pl-1')
  })

  test('collapses the mobile sidebar host without changing desktop sizing', () => {
    const { container, rerender } = render(
      <AppShell
        isLeftSidebarOpen={false}
        isRightDockOpen={false}
        primaryView="chat"
        sidebar={<div>Sidebar</div>}
        topline={<div>Topline</div>}
      >
        <div>Workspace</div>
      </AppShell>,
    )

    const shell = screen.getByRole('main')
    const sidebarHost = container.querySelector(
      '[data-slot="app-shell-sidebar-host"]',
    )
    expect(sidebarHost?.className).toContain('h-full')
    expect(sidebarHost?.className).toContain(
      'w-[var(--left-sidebar-width)]',
    )
    expect(sidebarHost?.className).toContain('max-[680px]:w-0')
    expect(sidebarHost?.className).toContain('max-[680px]:h-0')
    expect(shell.style.getPropertyValue('--left-sidebar-width')).toBe('0px')

    rerender(
      <AppShell
        isLeftSidebarOpen
        isRightDockOpen={false}
        primaryView="chat"
        sidebar={<div>Sidebar</div>}
        topline={<div>Topline</div>}
      >
        <div>Workspace</div>
      </AppShell>,
    )

    expect(shell.style.getPropertyValue('--left-sidebar-width')).toBe('280px')
  })
})

describe('AppSidebar pattern adoption', () => {
  test('renders primary destinations through WorkspaceNavigation without changing selection callbacks', async () => {
    const user = userEvent.setup()
    const onPrimaryViewChange = vi.fn()

    render(
      <AppSidebar
        accountModule="appearance"
        authoringSubmodule="workspaces"
        canManageJobPlatform={false}
        canLoadMoreSessions={false}
        error={null}
        isOpen
        jobsSubmodule="jobs"
        observabilitySubmodule="summary"
        onAccountModuleChange={vi.fn()}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMoreSessions={vi.fn()}
        onPrimaryViewChange={onPrimaryViewChange}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onSettingsModuleChange={vi.fn()}
        onSettingsSubmoduleChange={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onToggle={vi.fn()}
        onUnarchiveSession={vi.fn()}
        onWorkspaceIdChange={vi.fn()}
        primaryView="chat"
        runtimeSubmodule="connections"
        selectedSessionId={null}
        sessions={[]}
        sessionState="succeeded"
        settingsModule="authoring"
        statusFilter="active"
        workspaceId="workspace-1"
        workspaces={[]}
        workspaceState="succeeded"
      />,
    )

    const navigations = screen.getAllByRole('navigation', {
      name: 'Primary Navigation',
    })
    expect(navigations).toHaveLength(1)
    expect(navigations[0]?.getAttribute('data-slot')).toBe(
      'workspace-navigation',
    )
    expect(
      screen.getByRole('button', { name: 'Chat' }).getAttribute('aria-current'),
    ).toBe('page')

    await user.click(screen.getByRole('button', { name: 'Settings' }))
    expect(onPrimaryViewChange).toHaveBeenCalledWith('settings')
  })

  test('keeps the open mobile sidebar within a usable 86vw and 280px bound', () => {
    render(
      <AppSidebar
        accountModule="appearance"
        authoringSubmodule="workspaces"
        canManageJobPlatform={false}
        canLoadMoreSessions={false}
        error={null}
        isOpen
        jobsSubmodule="jobs"
        observabilitySubmodule="summary"
        onAccountModuleChange={vi.fn()}
        onArchiveSession={vi.fn()}
        onDeleteSession={vi.fn()}
        onLoadMoreSessions={vi.fn()}
        onPrimaryViewChange={vi.fn()}
        onRenameSession={vi.fn()}
        onSelectSession={vi.fn()}
        onSettingsModuleChange={vi.fn()}
        onSettingsSubmoduleChange={vi.fn()}
        onStartNewSession={vi.fn()}
        onStatusFilterChange={vi.fn()}
        onToggle={vi.fn()}
        onUnarchiveSession={vi.fn()}
        onWorkspaceIdChange={vi.fn()}
        primaryView="chat"
        runtimeSubmodule="connections"
        selectedSessionId={null}
        sessions={[]}
        sessionState="succeeded"
        settingsModule="authoring"
        statusFilter="active"
        workspaceId="workspace-1"
        workspaces={[]}
        workspaceState="succeeded"
      />,
    )

    const sidebar = screen.getByRole('complementary', {
      name: 'Primary Sidebar',
    })
    expect(sidebar.className).toContain('w-[280px]')
    expect(sidebar.className).toContain(
      'max-[680px]:w-[min(86vw,280px)]',
    )
    expect(sidebar.className).not.toContain('max-[680px]:w-[min(86vw,2px)]')
  })

  test('does not retain obsolete chat radius attributes in shell-owned containers', () => {
    expect(appShellSource).not.toContain('data-chat-radius')
  })
})
