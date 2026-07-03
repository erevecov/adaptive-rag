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
>((props, ref) => <DropdownMenuPrimitive.Trigger ref={ref} {...props} />)
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
          'z-50 grid min-w-36 gap-1 rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
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
          'flex min-h-8 cursor-pointer items-center rounded-sm px-2 text-sm outline-none',
          'hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground',
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
