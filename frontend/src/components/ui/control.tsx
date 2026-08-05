import {
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

const controlClasses = [
  'w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground',
  'motion-safe:transition-colors placeholder:text-muted-foreground',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  'focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
  // Invalid fields: destructive ring against fill (parity with danger Button).
  'aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive',
]

export type InputProps = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => (
    <input
      className={cn('h-9 max-[680px]:min-h-11', controlClasses, className)}
      ref={ref}
      type={type}
      {...props}
      data-slot="input"
    />
  ),
)
Input.displayName = 'Input'

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        'min-h-24 resize-y max-[680px]:min-h-28 max-[680px]:px-2.5 max-[680px]:py-2.5',
        controlClasses,
        className,
      )}
      ref={ref}
      {...props}
      data-slot="textarea"
    />
  ),
)
Textarea.displayName = 'Textarea'
