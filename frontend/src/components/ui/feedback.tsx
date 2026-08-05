import { type HTMLAttributes, forwardRef } from 'react'
import { type VariantProps, cva } from 'class-variance-authority'

import { cn } from '@/lib/utils'

export type EmptyStateProps = HTMLAttributes<HTMLDivElement>

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className, role = 'status', ...props }, ref) => (
    <div
      className={cn(
        'flex flex-col gap-1.5 rounded-md border border-dashed border-border/80 bg-muted/20 p-4 text-center text-sm tracking-tight text-muted-foreground max-[680px]:gap-1 max-[680px]:rounded-sm max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-snug',
        'motion-safe:transition-colors',
        className,
      )}
      ref={ref}
      role={role}
      {...props}
      data-slot="empty-state"
    />
  ),
)
EmptyState.displayName = 'EmptyState'

const inlineFeedbackVariants = cva(
  'text-sm font-medium leading-relaxed tracking-tight motion-safe:transition-colors max-[680px]:text-xs max-[680px]:leading-snug',
  {
    defaultVariants: {
      tone: 'neutral',
    },
    variants: {
      tone: {
        danger: 'text-destructive',
        neutral: 'text-muted-foreground',
        success: 'text-emerald-800 dark:text-emerald-200',
        warning: 'text-amber-900 dark:text-amber-100',
      },
    },
  },
)

type InlineFeedbackTone = NonNullable<
  VariantProps<typeof inlineFeedbackVariants>['tone']
>

export type InlineFeedbackProps = HTMLAttributes<HTMLParagraphElement> &
  VariantProps<typeof inlineFeedbackVariants> & {
    'data-slot'?: string
  }

export const InlineFeedback = forwardRef<
  HTMLParagraphElement,
  InlineFeedbackProps
>(({ className, role, tone, ...props }, ref) => {
  const feedbackTone: InlineFeedbackTone = tone ?? 'neutral'
  const {
    'data-slot': dataSlot,
    ...rest
  } = props
  const slot =
    typeof dataSlot === 'string' && dataSlot.length > 0
      ? dataSlot
      : 'inline-feedback'

  return (
    <p
      className={cn(inlineFeedbackVariants({ tone: feedbackTone }), className)}
      ref={ref}
      role={role ?? (feedbackTone === 'danger' ? 'alert' : undefined)}
      {...rest}
      data-slot={slot}
      data-tone={feedbackTone}
    />
  )
})
InlineFeedback.displayName = 'InlineFeedback'

const calloutVariants = cva(
  'rounded-md border p-4 text-sm leading-relaxed tracking-tight motion-safe:transition-colors max-[680px]:p-3 max-[680px]:text-xs max-[680px]:leading-snug',
  {
    defaultVariants: {
      tone: 'neutral',
    },
    variants: {
      tone: {
        danger: 'border-destructive/30 bg-destructive/10 text-destructive',
        neutral: 'border-border bg-muted/15 text-foreground',
        success:
          'border-emerald-500/35 bg-emerald-500/15 text-emerald-800 dark:text-emerald-200',
        warning:
          'border-amber-500/35 bg-amber-500/15 text-amber-900 dark:text-amber-100',
      },
    },
  },
)

type CalloutTone = NonNullable<VariantProps<typeof calloutVariants>['tone']>

export type CalloutProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof calloutVariants>

export const Callout = forwardRef<HTMLDivElement, CalloutProps>(
  ({ className, role, tone, ...props }, ref) => {
    const calloutTone: CalloutTone = tone ?? 'neutral'

    return (
      <div
        className={cn(calloutVariants({ tone: calloutTone }), className)}
        ref={ref}
        role={role ?? (calloutTone === 'danger' ? 'alert' : undefined)}
        {...props}
        data-slot="callout"
        data-tone={calloutTone}
      />
    )
  },
)
Callout.displayName = 'Callout'
