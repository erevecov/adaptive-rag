import { type HTMLAttributes, forwardRef } from 'react'
import { type VariantProps, cva } from 'class-variance-authority'

import { cn } from '@/lib/utils'

export type EmptyStateProps = HTMLAttributes<HTMLDivElement>

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className, role = 'status', ...props }, ref) => (
    <div
      className={cn(
        'flex flex-col gap-1.5 rounded-md border border-dashed border-border bg-muted/40 p-4 text-center text-sm text-muted-foreground',
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

const inlineFeedbackVariants = cva('text-sm font-medium', {
  defaultVariants: {
    tone: 'neutral',
  },
  variants: {
    tone: {
      danger: 'text-destructive',
      neutral: 'text-muted-foreground',
      success: 'text-emerald-700 dark:text-emerald-300',
      warning: 'text-amber-800 dark:text-amber-200',
    },
  },
})

type InlineFeedbackTone = NonNullable<
  VariantProps<typeof inlineFeedbackVariants>['tone']
>

export type InlineFeedbackProps = HTMLAttributes<HTMLParagraphElement> &
  VariantProps<typeof inlineFeedbackVariants>

export const InlineFeedback = forwardRef<
  HTMLParagraphElement,
  InlineFeedbackProps
>(({ className, role, tone, ...props }, ref) => {
  const feedbackTone: InlineFeedbackTone = tone ?? 'neutral'

  return (
    <p
      className={cn(inlineFeedbackVariants({ tone: feedbackTone }), className)}
      ref={ref}
      role={role ?? (feedbackTone === 'danger' ? 'alert' : undefined)}
      {...props}
      data-slot="inline-feedback"
      data-tone={feedbackTone}
    />
  )
})
InlineFeedback.displayName = 'InlineFeedback'

const calloutVariants = cva('rounded-md border p-4 text-sm', {
  defaultVariants: {
    tone: 'neutral',
  },
  variants: {
    tone: {
      danger: 'border-destructive/30 bg-destructive/10 text-destructive',
      neutral: 'border-border bg-muted text-foreground',
      success: 'border-emerald-500/35 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
      warning: 'border-amber-500/35 bg-amber-500/15 text-amber-800 dark:text-amber-200',
    },
  },
})

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
