import { type HTMLAttributes, forwardRef } from 'react'
import { type VariantProps, cva } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  [
    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
    'transition-colors',
  ],
  {
    defaultVariants: {
      tone: 'neutral',
    },
    variants: {
      tone: {
        danger: 'border-destructive/30 bg-destructive/10 text-destructive',
        neutral: 'border-border bg-secondary text-secondary-foreground',
        primary: 'border-primary/25 bg-primary/10 text-primary',
        success: 'border-primary/25 bg-primary/10 text-primary',
        warning: 'border-ring/30 bg-muted text-foreground',
      },
    },
  },
)

type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>['tone']>

export type BadgeProps = HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants>

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, tone, ...props }, ref) => (
    <span
      className={cn(badgeVariants({ tone }), className)}
      ref={ref}
      {...props}
      data-slot="badge"
    />
  ),
)
Badge.displayName = 'Badge'

export type StatusBadgeProps = BadgeProps

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ tone, ...props }, ref) => {
    const statusTone: BadgeTone = tone ?? 'neutral'

    return (
      <Badge
        ref={ref}
        tone={statusTone}
        {...props}
        data-tone={statusTone}
      />
    )
  },
)
StatusBadge.displayName = 'StatusBadge'
