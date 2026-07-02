import {
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

export type NavSectionProps = Omit<HTMLAttributes<HTMLElement>, 'title'> & {
  title?: ReactNode
}

export const NavSection = forwardRef<HTMLElement, NavSectionProps>(
  ({ children, className, title, ...props }, ref) => (
    <section
      className={cn('flex flex-col gap-2', className)}
      ref={ref}
      {...props}
      data-slot="nav-section"
    >
      {title ? (
        <h2
          className="px-2 text-xs font-medium text-muted-foreground"
          data-slot="nav-section-title"
        >
          {title}
        </h2>
      ) : null}
      <div className="flex flex-col gap-1" data-slot="nav-section-content">
        {children}
      </div>
    </section>
  ),
)
NavSection.displayName = 'NavSection'

export type SidebarItemProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean
}

export const SidebarItem = forwardRef<HTMLButtonElement, SidebarItemProps>(
  ({ active = false, className, type = 'button', ...props }, ref) => (
    <button
      className={cn(
        [
          'inline-flex h-9 w-full items-center justify-start gap-2 rounded-md px-3 text-sm font-medium',
          'text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
          'data-[active]:bg-accent data-[active]:text-accent-foreground',
        ],
        className,
      )}
      ref={ref}
      type={type}
      {...props}
      aria-current={active ? 'page' : undefined}
      data-active={active ? '' : undefined}
      data-slot="sidebar-item"
    />
  ),
)
SidebarItem.displayName = 'SidebarItem'
