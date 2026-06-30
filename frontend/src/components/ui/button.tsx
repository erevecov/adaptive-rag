import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from 'react'
import { type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'
import { buttonVariants } from './button-variants'

type ButtonSlot = 'button' | 'icon-button'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    'data-slot'?: ButtonSlot | (string & {})
  }

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      'data-slot': dataSlot,
      size,
      type = 'button',
      variant,
      ...props
    },
    ref,
  ) => (
    <button
      className={cn(buttonVariants({ size, variant }), className)}
      ref={ref}
      type={type}
      {...props}
      data-slot={dataSlot === 'icon-button' ? 'icon-button' : 'button'}
    />
  ),
)
Button.displayName = 'Button'

export type IconButtonProps = Omit<
  ButtonProps,
  'aria-label' | 'children' | 'data-slot' | 'size'
> & {
  children: ReactNode
  label: string
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ children, className, label, title, variant = 'secondary', ...props }, ref) => (
    <Button
      className={className}
      ref={ref}
      {...props}
      aria-label={label}
      data-slot="icon-button"
      size="icon"
      title={title ?? label}
      variant={variant}
    >
      {children}
    </Button>
  ),
)
IconButton.displayName = 'IconButton'
