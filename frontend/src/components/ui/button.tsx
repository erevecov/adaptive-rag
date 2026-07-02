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

const fixedIconSizingClassPattern =
  /^(?:size|w|h|min-w|min-h|max-w|max-h|p|px|py|pt|pr|pb|pl)-/
const fixedIconSizingProperties = new Set([
  'block-size',
  'height',
  'inline-size',
  'max-block-size',
  'max-height',
  'max-inline-size',
  'max-width',
  'min-block-size',
  'min-height',
  'min-inline-size',
  'min-width',
  'padding',
  'padding-block',
  'padding-bottom',
  'padding-inline',
  'padding-left',
  'padding-right',
  'padding-top',
  'width',
])

function iconUtilityToken(token: string): string {
  let bracketDepth = 0
  let utilityStart = 0

  for (let index = 0; index < token.length; index += 1) {
    const character = token[index]

    if (character === '[') {
      bracketDepth += 1
    } else if (character === ']') {
      bracketDepth = Math.max(0, bracketDepth - 1)
    } else if (character === ':' && bracketDepth === 0) {
      utilityStart = index + 1
    }
  }

  return token.slice(utilityStart).replace(/^!/, '')
}

function isIconSizingClass(token: string): boolean {
  const utility = iconUtilityToken(token)

  if (fixedIconSizingClassPattern.test(utility)) {
    return true
  }

  const arbitraryProperty = utility.match(/^\[([a-z-]+):/i)
  return (
    arbitraryProperty !== null &&
    fixedIconSizingProperties.has(arbitraryProperty[1].toLowerCase())
  )
}

function withoutIconSizingClasses(className?: string): string | undefined {
  const sanitizedClassName = className
    ?.split(/\s+/)
    .filter(Boolean)
    .filter((token) => !isIconSizingClass(token))
    .join(' ')

  return sanitizedClassName === '' ? undefined : sanitizedClassName
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
        className={cn(
          buttonVariants({ size: 'icon', variant }),
          withoutIconSizingClasses(className),
        )}
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
