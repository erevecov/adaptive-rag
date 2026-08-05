import { type ReactNode } from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

const EMPTY_OPTION_VALUE = '__adaptive_rag_empty_select_value__'

export type SelectOption = {
  disabled?: boolean
  label: ReactNode
  textValue?: string
  value: string
}

export type SelectProps = Omit<
  SelectPrimitive.SelectProps,
  'children' | 'defaultValue' | 'onValueChange' | 'value'
> & {
  'aria-label'?: string
  'aria-labelledby'?: string
  'data-testid'?: string
  className?: string
  contentClassName?: string
  id?: string
  onValueChange(value: string): void
  options: readonly SelectOption[]
  placeholder?: ReactNode
  value: string
}

export function Select({
  'aria-label': ariaLabel,
  'aria-labelledby': ariaLabelledBy,
  'data-testid': testId,
  className,
  contentClassName,
  onValueChange,
  options,
  placeholder,
  value,
  id,
  ...props
}: SelectProps) {
  return (
    <SelectPrimitive.Root
      value={toRadixValue(value)}
      onValueChange={(nextValue) => onValueChange(fromRadixValue(nextValue))}
      {...props}
    >
      <SelectPrimitive.Trigger
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        className={cn(
          [
            'flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground max-[680px]:min-h-11',
            'motion-safe:transition-colors placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
            'data-[placeholder]:text-muted-foreground',
            'aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive',
          ],
          className,
        )}
        data-testid={testId}
        data-slot="select-trigger"
        id={id}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon aria-hidden="true" className="text-muted-foreground">
          <ChevronDown className="size-4" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className={cn(
            [
              'z-50 max-h-64 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-[var(--shadow-popover)]',
              'outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
            ],
            contentClassName,
          )}
          data-slot="select-content"
          position="popper"
          sideOffset={4}
        >
          <SelectPrimitive.Viewport className="grid gap-1 p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                className={cn(
                  [
                    'relative flex min-h-8 max-[680px]:min-h-11 cursor-default select-none items-center rounded-sm px-3 py-1.5 text-sm outline-none',
                    'text-popover-foreground motion-safe:transition-colors',
                    'focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                    // Primary tint reads clearer than accent wash on purple menus.
                    'data-[highlighted]:bg-primary/15 data-[highlighted]:text-foreground',
                    'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
                  ],
                )}
                data-slot="select-item"
                disabled={option.disabled}
                key={option.value}
                textValue={option.textValue}
                value={toRadixValue(option.value)}
              >
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator
                  aria-hidden="true"
                  className="ml-auto pl-2 text-muted-foreground"
                >
                  <Check className="size-4" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}

function toRadixValue(value: string): string {
  return value === '' ? EMPTY_OPTION_VALUE : value
}

function fromRadixValue(value: string): string {
  return value === EMPTY_OPTION_VALUE ? '' : value
}
