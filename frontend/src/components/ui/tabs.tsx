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
}

export const SegmentedControl = forwardRef<
  HTMLDivElement,
  SegmentedControlProps
>(({ children, className, role = 'group', ...props }, ref) => {
  const controlClassName = cn(
    'inline-flex items-center gap-1 rounded-md border border-border bg-muted p-1',
    className,
  )

  if (role === 'tablist') {
    const tabItems = Children.toArray(children)
      .filter(isSegmentedControlElement)
      .map((child, index) => ({
        child,
        value: segmentedControlItemValue(child, index),
      }))
    const activeTab =
      tabItems.find(({ child }) => child.props.active)?.value ??
      tabItems[0]?.value

    return (
      <TabsPrimitive.Root orientation="horizontal" value={activeTab}>
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
})
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
        'inline-flex h-8 items-center justify-center rounded-sm px-3 text-sm font-medium',
        'text-muted-foreground transition-colors hover:bg-background hover:text-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
        'data-[active]:bg-background data-[active]:text-foreground data-[active]:shadow-sm',
        'data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm',
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
