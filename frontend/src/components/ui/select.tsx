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
            'flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm tracking-tight text-foreground max-[680px]:min-h-11 max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:px-0.5 max-[680px]:text-base max-[680px]:leading-snug',
            'group motion-safe:transition-colors placeholder:text-muted-foreground hover:border-primary/40 max-[680px]:hover:border-primary/95 active:border-primary/50 max-[680px]:active:border-primary/95',
            'data-[state=open]:border-primary/95 data-[state=open]:bg-primary/95',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-input',
            'data-[placeholder]:text-muted-foreground',
            'aria-invalid:border-destructive aria-invalid:hover:border-destructive aria-invalid:focus-visible:ring-destructive',
          ],
          className,
        )}
        data-testid={testId}
        data-slot="select-trigger"
        id={id}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon
          aria-hidden="true"
          className="size-4 shrink-0 text-muted-foreground motion-safe:transition-transform max-[680px]:size-5 group-data-[state=open]:rotate-180"
        >
          <ChevronDown className="size-full" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className={cn(
            [
              'z-50 max-h-64 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-border bg-popover p-1 text-sm tracking-tight text-popover-foreground shadow-[var(--shadow-popover)] motion-safe:transition-colors max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:p-0.5 max-[680px]:tracking-tighter max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95',
              'outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
            ],
            contentClassName,
          )}
          data-slot="select-content"
          position="popper"
          sideOffset={4}
        >
          <SelectPrimitive.Viewport className="grid gap-1 p-0 max-[680px]:gap-0.5">
            {options.map((option) => (
              <SelectPrimitive.Item
                className={cn(
                  [
                    'relative flex min-h-8 max-[680px]:min-h-11 cursor-default select-none items-center rounded-sm px-3 py-1.5 text-sm tracking-tight outline-none max-[680px]:px-0.5 max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
                    'text-popover-foreground motion-safe:transition-colors active:bg-primary/20 max-[680px]:active:bg-primary/95',
                    'focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                    // Primary tint reads clearer than accent wash on purple menus.
                    'data-[highlighted]:bg-primary/15 data-[highlighted]:text-foreground max-[680px]:data-[highlighted]:bg-primary/95',
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
                  className="ml-auto pl-2 text-muted-foreground max-[680px]:pl-1"
                >
                  <Check className="size-4 max-[680px]:size-5" />
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
