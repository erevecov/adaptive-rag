import { cva } from 'class-variance-authority'

export const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium tracking-tight max-[680px]:gap-0.5 max-[680px]:rounded-sm max-[680px]:tracking-tighter',
    'motion-safe:transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  ],
  {
    defaultVariants: {
      size: 'md',
      variant: 'primary',
    },
    variants: {
      size: {
        // ≤680: 44px min touch targets (composer/operator chrome parity).
        icon: 'size-9 p-0 max-[680px]:size-11',
        md: 'h-9 px-4 py-2 max-[680px]:min-h-11 max-[680px]:px-1 max-[680px]:text-[0.5625rem]',
        sm: 'h-8 px-3 text-xs max-[680px]:min-h-11 max-[680px]:px-1 max-[680px]:text-[0.5625rem]',
      },
      variant: {
        danger:
          // Solid ring against destructive fill (parity with primary; purple/dark).
          'bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive-foreground',
        ghost:
          'bg-transparent text-foreground hover:bg-primary/15 hover:text-foreground',
        // Contrast ring against primary fill (dark near-white / purple violet)
        primary:
          'bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-primary-foreground',
        secondary:
          // Primary-tint hover reads clearer than accent wash on purple chrome.
          'border border-border bg-secondary text-secondary-foreground hover:border-primary/40 hover:bg-primary/15 hover:text-foreground max-[680px]:border-primary/65',
      },
    },
  },
)
