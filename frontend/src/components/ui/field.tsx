import {
  type HTMLAttributes,
  type LabelHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

export type FieldProps = HTMLAttributes<HTMLDivElement>

export const Field = forwardRef<HTMLDivElement, FieldProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('group/field flex flex-col gap-2 max-[680px]:gap-0.5', className)}
      ref={ref}
      {...props}
      data-slot="field"
    />
  ),
)
Field.displayName = 'Field'

export type FieldLabelProps = LabelHTMLAttributes<HTMLLabelElement>

export const FieldLabel = forwardRef<HTMLLabelElement, FieldLabelProps>(
  ({ className, ...props }, ref) => (
    <label
      className={cn(
        'text-sm font-medium leading-none tracking-tight text-foreground max-[680px]:text-[0.5625rem] group-has-[:disabled]/field:cursor-not-allowed group-has-[:disabled]/field:opacity-70',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="field-label"
    />
  ),
)
FieldLabel.displayName = 'FieldLabel'

export type FieldControlProps = HTMLAttributes<HTMLDivElement>

export const FieldControl = forwardRef<HTMLDivElement, FieldControlProps>(
  ({ className, ...props }, ref) => (
    <div className={cn('flex flex-col gap-2 max-[680px]:gap-0.5', className)} ref={ref} {...props} data-slot="field-control" />
  ),
)
FieldControl.displayName = 'FieldControl'

export type FieldHelpProps = HTMLAttributes<HTMLParagraphElement>

export const FieldHelp = forwardRef<HTMLParagraphElement, FieldHelpProps>(
  ({ className, ...props }, ref) => (
    <p
      className={cn(
        // Dense operator help: xs + relaxed leading; muted stays readable on purple.
        'text-xs leading-relaxed tracking-tight text-muted-foreground max-[680px]:text-[0.5625rem] max-[680px]:leading-snug',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="field-help"
    />
  ),
)
FieldHelp.displayName = 'FieldHelp'

export type FieldErrorProps = HTMLAttributes<HTMLParagraphElement>

export const FieldError = forwardRef<HTMLParagraphElement, FieldErrorProps>(
  ({ className, role = 'alert', ...props }, ref) => (
    <p
      className={cn(
        // Match FieldHelp density; keep medium weight for scan priority.
        'text-xs font-medium leading-relaxed tracking-tight text-destructive max-[680px]:text-[0.5625rem] max-[680px]:leading-snug',
        className,
      )}
      ref={ref}
      role={role}
      {...props}
      data-slot="field-error"
    />
  ),
)
FieldError.displayName = 'FieldError'
