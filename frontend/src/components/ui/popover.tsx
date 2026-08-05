import {
  type ComponentPropsWithoutRef,
  type ElementRef,
  forwardRef,
} from 'react'
import * as PopoverPrimitive from '@radix-ui/react-popover'

import { cn } from '@/lib/utils'

export type PopoverRootProps = ComponentPropsWithoutRef<
  typeof PopoverPrimitive.Root
>
export type PopoverPortalProps = ComponentPropsWithoutRef<
  typeof PopoverPrimitive.Portal
>
export type PopoverTriggerProps = ComponentPropsWithoutRef<
  typeof PopoverPrimitive.Trigger
>
export type PopoverAnchorProps = ComponentPropsWithoutRef<
  typeof PopoverPrimitive.Anchor
>
export type PopoverContentProps = ComponentPropsWithoutRef<
  typeof PopoverPrimitive.Content
> & {
  'data-slot'?: string
}

export function Root(props: PopoverRootProps) {
  return <PopoverPrimitive.Root {...props} />
}

export function Portal(props: PopoverPortalProps) {
  return <PopoverPrimitive.Portal {...props} />
}

export const Trigger = forwardRef<
  ElementRef<typeof PopoverPrimitive.Trigger>,
  PopoverTriggerProps
>((props, ref) => <PopoverPrimitive.Trigger ref={ref} {...props} />)
Trigger.displayName = PopoverPrimitive.Trigger.displayName

export const Anchor = forwardRef<
  ElementRef<typeof PopoverPrimitive.Anchor>,
  PopoverAnchorProps
>((props, ref) => <PopoverPrimitive.Anchor ref={ref} {...props} />)
Anchor.displayName = PopoverPrimitive.Anchor.displayName

export const Content = forwardRef<
  ElementRef<typeof PopoverPrimitive.Content>,
  PopoverContentProps
>(
  (
    {
      className,
      sideOffset = 4,
      'data-slot': dataSlot = 'popover-content',
      ...props
    },
    ref,
  ) => (
    <PopoverPrimitive.Content
      className={cn(
        [
          'z-50 rounded-md border border-border bg-popover text-popover-foreground shadow-md',
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
Content.displayName = PopoverPrimitive.Content.displayName
