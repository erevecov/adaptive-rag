import {
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

export type SegmentedControlProps = HTMLAttributes<HTMLDivElement>

export const SegmentedControl = forwardRef<
  HTMLDivElement,
  SegmentedControlProps
>(({ className, role = 'group', ...props }, ref) => (
  <div
    className={cn(
      'inline-flex items-center gap-1 rounded-md border border-border bg-muted p-1',
      className,
    )}
    ref={ref}
    role={role}
    {...props}
    data-slot="segmented-control"
  />
))
SegmentedControl.displayName = 'SegmentedControl'

export type SegmentedControlItemProps =
  ButtonHTMLAttributes<HTMLButtonElement> & {
    active?: boolean
  }

export const SegmentedControlItem = forwardRef<
  HTMLButtonElement,
  SegmentedControlItemProps
>(({ active = false, className, type = 'button', ...props }, ref) => (
  <button
    className={cn(
      [
        'inline-flex h-8 items-center justify-center rounded-sm px-3 text-sm font-medium',
        'text-muted-foreground transition-colors hover:bg-background hover:text-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
        'data-[active]:bg-background data-[active]:text-foreground data-[active]:shadow-sm',
      ],
      className,
    )}
    ref={ref}
    type={type}
    {...props}
    aria-pressed={active}
    data-active={active ? '' : undefined}
    data-slot="segmented-control-item"
  />
))
SegmentedControlItem.displayName = 'SegmentedControlItem'
