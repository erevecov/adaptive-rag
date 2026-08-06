import {
  Children,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  cloneElement,
  forwardRef,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

export type SegmentedControlProps = HTMLAttributes<HTMLDivElement> & {
  children?: ReactNode
  onValueChange?(value: string): void
  value?: string
}

export const SegmentedControl = forwardRef<
  HTMLDivElement,
  SegmentedControlProps
>(
  (
    {
      children,
      className,
      onValueChange,
      role = 'group',
      value: valueProp,
      ...props
    },
    ref,
  ) => {
  const controlClassName = cn(
    'inline-flex w-full min-w-0 items-center gap-1 rounded-md border border-border bg-muted/40 p-1 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border-primary/70 max-[680px]:p-0.5',
    'motion-safe:transition-colors',
    className,
  )

  if (role === 'tablist') {
    const tabItems = Children.toArray(children)
      .filter(isSegmentedControlElement)
      .map((child, index) => ({
        child,
        value: segmentedControlItemValue(child, index),
      }))
    const activeFromChildren =
      tabItems.find(({ child }) => child.props.active)?.value ??
      tabItems[0]?.value
    const activeTab = valueProp ?? activeFromChildren

    return (
      <TabsPrimitive.Root
        onValueChange={(next) => {
          onValueChange?.(next)
          if (onValueChange !== undefined) {
            return
          }
          // Backward compat: fire the matching item onClick when parent only
          // wires selection via item clicks (mouse still works; arrows need this).
          const match = tabItems.find(({ value }) => value === next)
          const itemClick = match?.child.props.onClick
          if (typeof itemClick === 'function') {
            itemClick({
              preventDefault() {},
              stopPropagation() {},
            } as Parameters<NonNullable<typeof itemClick>>[0])
          }
        }}
        orientation="horizontal"
        value={activeTab}
      >
        <TabsPrimitive.List
          className={controlClassName}
          ref={ref}
          {...props}
          data-slot="segmented-control"
        >
          {tabItems.map(({ child, value }) =>
            cloneElement(child, {
              __radixTab: true,
              key: child.key ?? value,
              value,
            }),
          )}
        </TabsPrimitive.List>
      </TabsPrimitive.Root>
    )
  }

  return (
    <div
      className={controlClassName}
      ref={ref}
      role={role}
      {...props}
      data-slot="segmented-control"
    >
      {children}
    </div>
  )
},
)
SegmentedControl.displayName = 'SegmentedControl'

export type SegmentedControlItemProps =
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'value'> & {
    __radixTab?: boolean
    active?: boolean
    value?: string
  }

export const SegmentedControlItem = forwardRef<
  HTMLButtonElement,
  SegmentedControlItemProps
>(
  (
    {
      __radixTab = false,
      active = false,
      className,
      type = 'button',
      value,
      ...props
    },
    ref,
  ) => {
    const itemClassName = cn(
      [
        'inline-flex h-8 items-center justify-center rounded-sm px-3 text-sm font-medium tracking-tight max-[680px]:min-h-11 max-[680px]:px-1 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
        'text-muted-foreground motion-safe:transition-colors hover:bg-primary/15 hover:text-foreground active:bg-primary/20',
        // Inset ring stays inside the muted track (offset rings clip / wash on purple).
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        'disabled:pointer-events-none disabled:opacity-50',
        // Card pill + light primary ring: clearer active state on purple/dark tracks.
        'data-[active]:bg-card data-[active]:font-semibold data-[active]:text-foreground data-[active]:shadow-sm data-[active]:ring-1 data-[active]:ring-primary/30 max-[680px]:data-[active]:ring-primary/80',
        'data-[state=active]:bg-card data-[state=active]:font-semibold data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-primary/30 max-[680px]:data-[state=active]:ring-primary/80',
      ],
      className,
    )

    if (__radixTab) {
      return (
        <TabsPrimitive.Trigger
          className={itemClassName}
          ref={ref}
          value={value ?? ''}
          {...props}
          data-active={active ? '' : undefined}
          data-slot="segmented-control-item"
        />
      )
    }

    return (
      <button
        className={itemClassName}
        ref={ref}
        type={type}
        {...props}
        aria-pressed={active}
        data-active={active ? '' : undefined}
        data-slot="segmented-control-item"
        value={value}
      />
    )
  },
)
SegmentedControlItem.displayName = 'SegmentedControlItem'

function isSegmentedControlElement(
  child: ReactNode,
): child is ReactElement<SegmentedControlItemProps> {
  return isValidElement<SegmentedControlItemProps>(child)
}

function segmentedControlItemValue(
  child: ReactElement<SegmentedControlItemProps>,
  index: number,
): string {
  if (typeof child.props.value === 'string' && child.props.value.length > 0) {
    return child.props.value
  }

  if (typeof child.props.children === 'string') {
    return child.props.children
  }

  return String(index)
}
