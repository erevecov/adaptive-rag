import { NavSection, SidebarItem } from '@/components/ui/nav'

export type WorkspaceNavigationItem = {
  active?: boolean
  badge?: string | number
  id: string
  label: string
}

export type WorkspaceNavigationSection = {
  id: string
  items: readonly WorkspaceNavigationItem[]
  label: string
}

export type WorkspaceNavigationProps = {
  label: string
  onNavigate(id: string): void
  sections: readonly WorkspaceNavigationSection[]
}

export function WorkspaceNavigation({ label, onNavigate, sections }: WorkspaceNavigationProps) {
  return (
    <nav aria-label={label} className="grid gap-4 max-[680px]:gap-2" data-slot="workspace-navigation">
      {sections.map((section) => (
        <NavSection key={section.id} title={section.label}>
          {section.items.map((item) => (
            <SidebarItem active={item.active} key={item.id} onClick={() => onNavigate(item.id)}>
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
              {item.badge !== undefined ? (
                <span className="text-xs tabular-nums text-muted-foreground">{item.badge}</span>
              ) : null}
            </SidebarItem>
          ))}
        </NavSection>
      ))}
    </nav>
  )
}
