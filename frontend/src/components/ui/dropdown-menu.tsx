import {
  type ComponentPropsWithoutRef,
  type ElementRef,
  forwardRef,
} from 'react'
import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'

import { cn } from '@/lib/utils'

export type DropdownMenuRootProps = ComponentPropsWithoutRef<
  typeof DropdownMenuPrimitive.Root
>
export type DropdownMenuPortalProps = ComponentPropsWithoutRef<
  typeof DropdownMenuPrimitive.Portal
>
export type DropdownMenuTriggerProps = ComponentPropsWithoutRef<
  typeof DropdownMenuPrimitive.Trigger
>
export type DropdownMenuContentProps = ComponentPropsWithoutRef<
  typeof DropdownMenuPrimitive.Content
> & {
  'data-slot'?: string
}

export function Root(props: DropdownMenuRootProps) {
  return <DropdownMenuPrimitive.Root {...props} />
}

export function Portal(props: DropdownMenuPortalProps) {
  return <DropdownMenuPrimitive.Portal {...props} />
}

export const Trigger = forwardRef<
  ElementRef<typeof DropdownMenuPrimitive.Trigger>,
  DropdownMenuTriggerProps
>(({ asChild, className, ...props }, ref) => (
  <DropdownMenuPrimitive.Trigger
    asChild={asChild}
    className={cn(
      // Bare triggers render a button — match Popover / DS focus-visible rings.
      !asChild &&
        'rounded-md max-[680px]:min-h-11 max-[680px]:rounded-sm max-[680px]:tracking-tighter motion-safe:transition-colors hover:bg-primary/15 active:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      className,
    )}
    ref={ref}
    {...props}
  />
))
Trigger.displayName = DropdownMenuPrimitive.Trigger.displayName

export const Content = forwardRef<
  ElementRef<typeof DropdownMenuPrimitive.Content>,
  DropdownMenuContentProps
>(
  (
    {
      className,
      sideOffset = 4,
      'data-slot': dataSlot = 'dropdown-menu-content',
      ...props
    },
    ref,
  ) => (
    <DropdownMenuPrimitive.Content
      className={cn(
        [
'z-50 grid min-w-36 max-[680px]:min-w-16 gap-1 rounded-md border border-border bg-popover p-1 text-sm tracking-tight text-popover-foreground shadow-[var(--shadow-popover)] motion-safe:transition-colors max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border-primary/85 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
          'outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        ],
        className,
      )}
      data-slot={dataSlot}
      ref={ref}
      sideOffset={sideOffset}
      {...props}
    />
  ),
)
Content.displayName = DropdownMenuPrimitive.Content.displayName

export type DropdownMenuItemProps = ComponentPropsWithoutRef<
  typeof DropdownMenuPrimitive.Item
> & {
  'data-slot'?: string
}

export const Item = forwardRef<
  ElementRef<typeof DropdownMenuPrimitive.Item>,
  DropdownMenuItemProps
>(
  (
    {
      className,
      'data-slot': dataSlot = 'dropdown-menu-item',
      ...props
    },
    ref,
  ) => (
    <DropdownMenuPrimitive.Item
      className={cn(
        [
          'flex min-h-8 max-[680px]:min-h-11 cursor-pointer items-center rounded-sm px-2 text-sm tracking-tight outline-none max-[680px]:rounded-sm max-[680px]:px-1 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
          'motion-safe:transition-colors hover:bg-primary/15 hover:text-foreground active:bg-primary/20',
          'data-[highlighted]:bg-primary/15 data-[highlighted]:text-foreground',
          'focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
          'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
        ],
        className,
      )}
      data-slot={dataSlot}
      ref={ref}
      {...props}
    />
  ),
)
Item.displayName = DropdownMenuPrimitive.Item.displayName
