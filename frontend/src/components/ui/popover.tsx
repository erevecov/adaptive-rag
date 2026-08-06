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
>(({ asChild, className, ...props }, ref) => (
  <PopoverPrimitive.Trigger
    asChild={asChild}
    className={cn(
      // Bare triggers render a button — match DS focus-visible rings.
      !asChild &&
        'rounded-md max-[680px]:min-h-11 max-[680px]:rounded-sm max-[680px]:tracking-tighter motion-safe:transition-colors hover:bg-primary/15 active:bg-primary/20 max-[680px]:active:bg-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      className,
    )}
    ref={ref}
    {...props}
  />
))
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
          'z-50 rounded-md border border-border bg-popover p-1 text-sm tracking-tight text-popover-foreground shadow-[var(--shadow-popover)] motion-safe:transition-colors max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95',
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
