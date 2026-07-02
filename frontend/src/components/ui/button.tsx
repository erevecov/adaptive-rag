import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from 'react'
import { type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'
import { buttonVariants } from './button-variants'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    'data-slot'?: string
  }

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size, type = 'button', variant, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ size, variant }), className)}
      ref={ref}
      type={type}
      {...props}
      data-slot="button"
    />
  ),
)
Button.displayName = 'Button'

export type IconButtonProps = Omit<
  ButtonProps,
  | 'aria-hidden'
  | 'aria-label'
  | 'aria-labelledby'
  | 'children'
  | 'data-slot'
  | 'role'
  | 'size'
  | 'tabIndex'
  | 'title'
> & {
  'aria-hidden'?: never
  'aria-label'?: never
  'aria-labelledby'?: never
  children: ReactNode
  'data-slot'?: never
  label: string
  role?: never
  size?: never
  tabIndex?: never
  title?: never
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      children,
      className,
      label,
      type = 'button',
      variant = 'secondary',
      ...props
    },
    ref,
  ) => {
    const buttonProps = {
      ...props,
    } as typeof props & Record<string, unknown>
    delete buttonProps['aria-label']
    delete buttonProps['aria-labelledby']
    delete buttonProps['aria-hidden']
    delete buttonProps['data-slot']
    delete buttonProps.role
    delete buttonProps.size
    delete buttonProps.tabIndex
    delete buttonProps.title

    return (
      <button
        className={cn(className, buttonVariants({ size: 'icon', variant }))}
        ref={ref}
        type={type}
        {...buttonProps}
        aria-label={label}
        data-slot="icon-button"
        title={label}
      >
        {children}
      </button>
    )
  },
)
IconButton.displayName = 'IconButton'
