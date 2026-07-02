import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export type PanelProps = HTMLAttributes<HTMLDivElement>

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn(
        'rounded-lg border border-border bg-card text-card-foreground shadow-sm',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="panel"
    />
  ),
)
Panel.displayName = 'Panel'

export type PanelHeaderProps = HTMLAttributes<HTMLDivElement>

export const PanelHeader = forwardRef<HTMLDivElement, PanelHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('flex flex-col gap-1.5 p-6', className)}
      ref={ref}
      {...props}
      data-slot="panel-header"
    />
  ),
)
PanelHeader.displayName = 'PanelHeader'

export type PanelTitleProps = HTMLAttributes<HTMLHeadingElement>

export const PanelTitle = forwardRef<HTMLHeadingElement, PanelTitleProps>(
  ({ className, ...props }, ref) => (
    <h3
      className={cn('text-lg font-semibold leading-none tracking-normal', className)}
      ref={ref}
      {...props}
      data-slot="panel-title"
    />
  ),
)
PanelTitle.displayName = 'PanelTitle'

export type PanelDescriptionProps = HTMLAttributes<HTMLParagraphElement>

export const PanelDescription = forwardRef<
  HTMLParagraphElement,
  PanelDescriptionProps
>(({ className, ...props }, ref) => (
  <p
    className={cn('text-sm text-muted-foreground', className)}
    ref={ref}
    {...props}
    data-slot="panel-description"
  />
))
PanelDescription.displayName = 'PanelDescription'

export type PanelBodyProps = HTMLAttributes<HTMLDivElement>

export const PanelBody = forwardRef<HTMLDivElement, PanelBodyProps>(
  ({ className, ...props }, ref) => (
    <div className={cn('p-6 pt-0', className)} ref={ref} {...props} data-slot="panel-body" />
  ),
)
PanelBody.displayName = 'PanelBody'
