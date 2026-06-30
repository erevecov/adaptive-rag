import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

export const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium',
    'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  ],
  {
    defaultVariants: {
      size: 'md',
      variant: 'primary',
    },
    variants: {
      size: {
        icon: 'h-9 w-9 p-0',
        md: 'h-9 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
      },
      variant: {
        danger:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        ghost:
          'bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground',
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary:
          'border border-border bg-secondary text-secondary-foreground hover:bg-accent hover:text-accent-foreground',
      },
    },
  },
)

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size, type = 'button', variant, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ size, variant }), className)}
      ref={ref}
      type={type}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

export type IconButtonProps = Omit<
  ButtonProps,
  'aria-label' | 'children' | 'size'
> & {
  children: ReactNode
  label: string
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ children, className, label, title, variant = 'secondary', ...props }, ref) => (
    <Button
      aria-label={label}
      className={className}
      ref={ref}
      size="icon"
      title={title ?? label}
      variant={variant}
      {...props}
    >
      {children}
    </Button>
  ),
)
IconButton.displayName = 'IconButton'
