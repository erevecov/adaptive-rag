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
      className={cn('flex flex-col gap-2 max-[680px]:gap-0.5', className)}
      ref={ref}
      {...props}
      data-slot="nav-section"
    >
      {title ? (
        <h2
          className="px-2 text-[0.6875rem] font-semibold uppercase tracking-wide text-muted-foreground max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter"
          data-slot="nav-section-title"
        >
          {title}
        </h2>
      ) : null}
      <div className="flex flex-col gap-1 max-[680px]:gap-0.5" data-slot="nav-section-content">
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
          'inline-flex h-9 w-full items-center justify-start gap-2 rounded-md px-3 text-sm font-medium tracking-tight max-[680px]:min-h-11 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
          'text-muted-foreground motion-safe:transition-colors hover:bg-primary/15 max-[680px]:hover:bg-primary/80 hover:text-foreground active:bg-primary/20 max-[680px]:active:bg-primary/95',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
          // Primary tint reads clearer than accent wash on purple/dark sidebars.
          'data-[active]:bg-primary/15 data-[active]:font-semibold data-[active]:text-foreground max-[680px]:data-[active]:bg-primary/45',
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
