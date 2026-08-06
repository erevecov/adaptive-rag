import {
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

const controlClasses = [
  'w-full rounded-md border border-input bg-background px-3 py-2 text-sm tracking-tight text-foreground',
  'motion-safe:transition-colors placeholder:text-muted-foreground hover:border-primary/40',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  'focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-input',
  // Invalid fields: destructive ring against fill (parity with danger Button).
  'aria-invalid:border-destructive aria-invalid:hover:border-destructive aria-invalid:focus-visible:ring-destructive',
]

export type InputProps = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => (
    <input
      className={cn('h-9 max-[680px]:min-h-11 max-[680px]:rounded-sm max-[680px]:border-primary/70 max-[680px]:px-2 max-[680px]:text-base max-[680px]:leading-snug', controlClasses, className)}
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
        'min-h-24 resize-y max-[680px]:min-h-28 max-[680px]:rounded-sm max-[680px]:border-primary/70 max-[680px]:px-2 max-[680px]:py-2 max-[680px]:text-base max-[680px]:leading-snug',
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
