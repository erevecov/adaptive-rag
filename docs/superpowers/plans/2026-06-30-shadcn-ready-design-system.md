# Shadcn-Ready Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Tailwind v4 + shadcn-ready design-system foundation and apply it only to low-risk app shell primitives.

**Architecture:** Tailwind and shadcn compatibility are added as frontend infrastructure first, then semantic tokens bridge the existing `--app-*` CSS variables. New `frontend/src/components/ui/*` primitives stay presentational and are adopted through small wrappers in `App.tsx` so feature behavior stays unchanged.

**Tech Stack:** React 19, Vite 8, TypeScript 6, Tailwind CSS v4, `@tailwindcss/vite`, `clsx`, `tailwind-merge`, `class-variance-authority`, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/package.json` and `frontend/pnpm-lock.yaml`: add Tailwind and class composition dependencies.
- Modify `frontend/vite.config.ts`: add the Tailwind Vite plugin and the `@` alias.
- Modify `frontend/tsconfig.json`: add the root `@/*` path mapping that shadcn CLI reads.
- Modify `frontend/tsconfig.app.json`: add the app `@/*` path mapping used by TypeScript project compilation.
- Create `frontend/components.json`: shadcn-compatible project configuration for Vite, React, TypeScript, neutral base, CSS variables, and lucide icon library.
- Modify `frontend/src/index.css`: import Tailwind, define shadcn-compatible semantic tokens, and bridge existing `--app-*` variables.
- Create `frontend/src/lib/utils.ts`: expose `cn(...)`.
- Create `frontend/src/lib/utils.test.ts`: verify `cn(...)` class composition and Tailwind conflict resolution.
- Create `frontend/src/components/ui/button.tsx`: presentational `Button`, `IconButton`, and `buttonVariants`.
- Create `frontend/src/components/ui/button.test.tsx`: verify variants and accessible icon labels.
- Create `frontend/src/components/ui/panel.tsx`: presentational panel wrappers.
- Create `frontend/src/components/ui/field.tsx`: presentational field wrappers.
- Create `frontend/src/components/ui/nav.tsx`: presentational navigation section and sidebar item wrappers.
- Create `frontend/src/components/ui/nav.test.tsx`: verify active and disabled ARIA state mapping.
- Modify `frontend/src/App.tsx`: import `IconButton` and `SidebarItem` wrappers; apply them to the sidebar burger and primary sidebar nav through existing local components.
- Modify `frontend/src/App.css`: point shell/sidebar/button CSS variables at the new semantic token bridge, keeping existing selectors intact.

---

### Task 1: Tailwind And Shadcn Tooling

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/pnpm-lock.yaml`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tsconfig.json`
- Modify: `frontend/tsconfig.app.json`
- Create: `frontend/components.json`

- [ ] **Step 1: Install dependencies**

Run:

```powershell
pnpm --dir frontend add tailwindcss @tailwindcss/vite clsx tailwind-merge class-variance-authority
```

Expected: `frontend/package.json` gains the five packages and `frontend/pnpm-lock.yaml` updates.

- [ ] **Step 2: Configure Vite**

Replace `frontend/vite.config.ts` with:

```ts
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: Configure TypeScript aliases**

In `frontend/tsconfig.json`, add a root `compilerOptions` block before `references`:

```json
"compilerOptions": {
  "paths": {
    "@/*": ["./src/*"]
  }
}
```

In `frontend/tsconfig.app.json`, add `paths` inside `compilerOptions`:

```json
"paths": {
  "@/*": ["./src/*"]
}
```

Do not add `baseUrl`; TypeScript 6 accepts this `paths` mapping without it, and avoiding `baseUrl` avoids deprecation suppression. The resulting `compilerOptions` must still include the existing strict/lint options.

- [ ] **Step 4: Add shadcn configuration**

Create `frontend/components.json` with:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 5: Verify config compiles**

Run:

```powershell
pnpm dlx shadcn@latest info --json
pnpm dlx shadcn@latest add button --dry-run
pnpm --dir frontend typecheck
```

Expected: shadcn info resolves aliases under `frontend\\src\\...`, the dry run would create `src\\components\\ui\\button.tsx`, and typecheck exits `0`. If typecheck fails because dependencies are not installed in the worktree, run `pnpm --dir frontend install` and retry.

- [ ] **Step 6: Commit tooling**

Run:

```powershell
git add frontend/package.json frontend/pnpm-lock.yaml frontend/vite.config.ts frontend/tsconfig.json frontend/tsconfig.app.json frontend/components.json
git commit -m "feat(frontend): add tailwind shadcn tooling"
```

---

### Task 2: Class Composition Helper

**Files:**
- Create: `frontend/src/lib/utils.test.ts`
- Create: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/utils.test.ts`:

```ts
import { describe, expect, test } from 'vitest'

import { cn } from './utils'

describe('cn', () => {
  test('combines conditional classes and resolves Tailwind conflicts', () => {
    const result = cn(
      'px-2 text-sm',
      false && 'hidden',
      ['px-4', 'font-medium'],
      { 'text-foreground': true },
    )

    expect(result).toBe('text-sm px-4 font-medium text-foreground')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pnpm --dir frontend test src/lib/utils.test.ts
```

Expected: FAIL because `frontend/src/lib/utils.ts` does not exist or does not export `cn`.

- [ ] **Step 3: Implement minimal helper**

Create `frontend/src/lib/utils.ts`:

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
pnpm --dir frontend test src/lib/utils.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit helper**

Run:

```powershell
git add frontend/src/lib/utils.ts frontend/src/lib/utils.test.ts
git commit -m "feat(frontend): add class composition helper"
```

---

### Task 3: Semantic Tokens And Tailwind Entry

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Update global CSS tokens**

Replace `frontend/src/index.css` with:

```css
@import "tailwindcss";

@custom-variant dark (&:is([data-theme='dark'] *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --radius-sm: calc(var(--radius) - 2px);
  --radius-md: var(--radius);
  --radius-lg: calc(var(--radius) + 2px);
}

:root {
  color-scheme: light;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  --background: #ffffff;
  --foreground: #171717;
  --card: #ffffff;
  --card-foreground: #171717;
  --popover: #ffffff;
  --popover-foreground: #171717;
  --primary: #171717;
  --primary-foreground: #fafafa;
  --secondary: #f5f5f5;
  --secondary-foreground: #171717;
  --muted: #f5f5f5;
  --muted-foreground: #737373;
  --accent: #f5f5f5;
  --accent-foreground: #171717;
  --destructive: #dc2626;
  --destructive-foreground: #ffffff;
  --border: #e5e5e5;
  --input: #e5e5e5;
  --ring: #a3a3a3;
  --radius: 8px;
}

[data-theme='dark'] {
  color-scheme: dark;
  --background: #000000;
  --foreground: #fafafa;
  --card: #050505;
  --card-foreground: #fafafa;
  --popover: #050505;
  --popover-foreground: #fafafa;
  --primary: #fafafa;
  --primary-foreground: #0a0a0a;
  --secondary: #171717;
  --secondary-foreground: #fafafa;
  --muted: #171717;
  --muted-foreground: #a3a3a3;
  --accent: #171717;
  --accent-foreground: #fafafa;
  --destructive: #ef4444;
  --destructive-foreground: #ffffff;
  --border: #262626;
  --input: #262626;
  --ring: #737373;
}

[data-theme='purple'] {
  color-scheme: dark;
  --background: #070513;
  --foreground: #f4f0ff;
  --card: #100d1e;
  --card-foreground: #f4f0ff;
  --popover: #100d1e;
  --popover-foreground: #f4f0ff;
  --primary: #8f7dff;
  --primary-foreground: #ffffff;
  --secondary: #17122a;
  --secondary-foreground: #f4f0ff;
  --muted: #120f22;
  --muted-foreground: #b5acd5;
  --accent: #24185c;
  --accent-foreground: #ffffff;
  --destructive: #ffb4b4;
  --destructive-foreground: #170a0a;
  --border: #2a2247;
  --input: #382e61;
  --ring: #8f7dff;
}

* {
  box-sizing: border-box;
}

body {
  background: var(--background);
  color: var(--foreground);
  margin: 0;
}
```

- [ ] **Step 2: Verify Tailwind import builds**

Run:

```powershell
pnpm --dir frontend build
```

Expected: PASS. The Vite build should process `@import "tailwindcss";` through `@tailwindcss/vite`.

- [ ] **Step 3: Commit tokens**

Run:

```powershell
git add frontend/src/index.css
git commit -m "feat(frontend): add semantic design tokens"
```

---

### Task 4: Button Primitive

**Files:**
- Create: `frontend/src/components/ui/button.test.tsx`
- Create: `frontend/src/components/ui/button.tsx`

- [ ] **Step 1: Write failing button tests**

Create `frontend/src/components/ui/button.test.tsx`:

```tsx
/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Button, IconButton } from './button'

afterEach(() => {
  cleanup()
})

describe('Button', () => {
  test('renders the primary variant by default', () => {
    render(<Button>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button.className).toContain('bg-primary')
    expect(button.className).toContain('text-primary-foreground')
  })

  test('merges caller classes after variant classes', () => {
    render(<Button className="px-8">Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button.className).toContain('px-8')
  })
})

describe('IconButton', () => {
  test('uses the provided label as the accessible name', () => {
    render(
      <IconButton label="Open menu">
        <span aria-hidden="true">M</span>
      </IconButton>,
    )

    expect(screen.getByRole('button', { name: 'Open menu' })).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pnpm --dir frontend test src/components/ui/button.test.tsx
```

Expected: FAIL because `frontend/src/components/ui/button.tsx` does not exist.

- [ ] **Step 3: Implement button primitive**

Create `frontend/src/components/ui/button.tsx`:

```tsx
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
        ghost: 'bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground',
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

export type IconButtonProps = Omit<ButtonProps, 'aria-label' | 'children' | 'size'> & {
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
pnpm --dir frontend test src/components/ui/button.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit button**

Run:

```powershell
git add frontend/src/components/ui/button.tsx frontend/src/components/ui/button.test.tsx
git commit -m "feat(frontend): add button primitive"
```

---

### Task 5: Panel, Field, And Nav Primitives

**Files:**
- Create: `frontend/src/components/ui/nav.test.tsx`
- Create: `frontend/src/components/ui/nav.tsx`
- Create: `frontend/src/components/ui/panel.tsx`
- Create: `frontend/src/components/ui/field.tsx`

- [ ] **Step 1: Write failing nav tests**

Create `frontend/src/components/ui/nav.test.tsx`:

```tsx
/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { SidebarItem } from './nav'

afterEach(() => {
  cleanup()
})

describe('SidebarItem', () => {
  test('marks active item with aria-current page', () => {
    render(<SidebarItem active>Chat</SidebarItem>)

    expect(screen.getByRole('button', { name: 'Chat' }).getAttribute('aria-current')).toBe(
      'page',
    )
  })

  test('passes disabled state to the button element', () => {
    render(<SidebarItem disabled>Locked</SidebarItem>)

    expect(screen.getByRole('button', { name: 'Locked' }).hasAttribute('disabled')).toBe(
      true,
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pnpm --dir frontend test src/components/ui/nav.test.tsx
```

Expected: FAIL because `frontend/src/components/ui/nav.tsx` does not exist.

- [ ] **Step 3: Implement nav primitive**

Create `frontend/src/components/ui/nav.tsx`:

```tsx
import { type ButtonHTMLAttributes, type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export type NavSectionProps = HTMLAttributes<HTMLElement> & {
  title?: string
}

export function NavSection({
  children,
  className,
  title,
  ...props
}: NavSectionProps) {
  return (
    <section className={cn('grid gap-1', className)} {...props}>
      {title ? (
        <h2 className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  )
}

export type SidebarItemProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean
}

export const SidebarItem = forwardRef<HTMLButtonElement, SidebarItemProps>(
  ({ active = false, className, type = 'button', ...props }, ref) => (
    <button
      aria-current={active ? 'page' : undefined}
      className={cn(
        'inline-flex h-8 w-full items-center rounded-md px-2 text-left text-sm font-medium text-muted-foreground transition-colors',
        'hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:pointer-events-none disabled:opacity-50',
        active && 'bg-accent text-accent-foreground',
        className,
      )}
      data-active={active ? 'true' : undefined}
      ref={ref}
      type={type}
      {...props}
    />
  ),
)
SidebarItem.displayName = 'SidebarItem'
```

- [ ] **Step 4: Implement panel primitive**

Create `frontend/src/components/ui/panel.tsx`:

```tsx
import { type HTMLAttributes, type LabelHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export const Panel = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('rounded-lg border border-border bg-card text-card-foreground', className)}
      ref={ref}
      {...props}
    />
  ),
)
Panel.displayName = 'Panel'

export const PanelHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn('grid gap-1.5 border-b border-border p-4', className)} ref={ref} {...props} />
  ),
)
PanelHeader.displayName = 'PanelHeader'

export const PanelTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h2 className={cn('text-sm font-semibold text-foreground', className)} ref={ref} {...props} />
  ),
)
PanelTitle.displayName = 'PanelTitle'

export const PanelDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p className={cn('text-sm text-muted-foreground', className)} ref={ref} {...props} />
  ),
)
PanelDescription.displayName = 'PanelDescription'

export const PanelBody = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn('p-4', className)} ref={ref} {...props} />
  ),
)
PanelBody.displayName = 'PanelBody'
```

- [ ] **Step 5: Implement field primitive**

Create `frontend/src/components/ui/field.tsx`:

```tsx
import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export const Field = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn('grid gap-2', className)} ref={ref} {...props} />
  ),
)
Field.displayName = 'Field'

export const FieldLabel = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label className={cn('text-sm font-medium text-foreground', className)} ref={ref} {...props} />
  ),
)
FieldLabel.displayName = 'FieldLabel'

export const FieldControl = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn('min-w-0', className)} ref={ref} {...props} />
  ),
)
FieldControl.displayName = 'FieldControl'

export const FieldHelp = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p className={cn('text-xs text-muted-foreground', className)} ref={ref} {...props} />
  ),
)
FieldHelp.displayName = 'FieldHelp'

export const FieldError = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p className={cn('text-xs font-medium text-destructive', className)} ref={ref} role="alert" {...props} />
  ),
)
FieldError.displayName = 'FieldError'
```

- [ ] **Step 6: Run nav test to verify it passes**

Run:

```powershell
pnpm --dir frontend test src/components/ui/nav.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Run typecheck**

Run:

```powershell
pnpm --dir frontend typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit primitives**

Run:

```powershell
git add frontend/src/components/ui/nav.tsx frontend/src/components/ui/nav.test.tsx frontend/src/components/ui/panel.tsx frontend/src/components/ui/field.tsx
git commit -m "feat(frontend): add shell ui primitives"
```

---

### Task 6: Shell Adoption Through Existing Components

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing sidebar integration test**

Append this test to `frontend/src/App.test.tsx` inside the existing test suite area, near other navigation tests:

```tsx
test('marks the active primary sidebar destination with aria-current', async () => {
  const client = createClientStub({})

  render(<App apiClient={client} initialProjectId={projectId} />)

  await screen.findByRole('button', { name: 'Chat' })

  expect(screen.getByRole('button', { name: 'Chat' }).getAttribute('aria-current')).toBe(
    'page',
  )
  expect(screen.getByRole('button', { name: 'My account' }).getAttribute('aria-current')).toBe(
    null,
  )
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pnpm --dir frontend test src/App.test.tsx
```

Expected: FAIL because the current `SidebarNavButton` uses `aria-pressed` but does not set `aria-current="page"`.

- [ ] **Step 3: Import UI primitives in `App.tsx`**

Add these imports near the existing component imports in `frontend/src/App.tsx`:

```tsx
import { IconButton } from '@/components/ui/button'
import { SidebarItem as UiSidebarItem } from '@/components/ui/nav'
```

- [ ] **Step 4: Replace sidebar burger button with `IconButton`**

In `AppSidebar`, replace the current `<button className="sidebar-burger" ...>` block with:

```tsx
<IconButton
  aria-expanded={isOpen}
  className="sidebar-burger"
  label={isOpen ? 'Collapse left sidebar' : 'Open left sidebar'}
  onClick={onToggle}
  title={isOpen ? 'Collapse menu' : 'Open menu'}
>
  <MenuIcon />
</IconButton>
```

- [ ] **Step 5: Keep local `SidebarNavButton` API and delegate to UI primitive**

Replace the body of `SidebarNavButton` in `frontend/src/App.tsx` with:

```tsx
function SidebarNavButton({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick(): void
}) {
  return (
    <UiSidebarItem
      active={active}
      className={active ? 'sidebar-nav-button sidebar-nav-button-active' : 'sidebar-nav-button'}
      onClick={onClick}
    >
      {label}
    </UiSidebarItem>
  )
}
```

- [ ] **Step 6: Bridge existing shell variables to semantic tokens**

At the top of `frontend/src/App.css`, update the light `:root` values so the existing `--app-*` variables are backed by the new semantic token names:

```css
:root {
  --app-page-background: var(--background);
  --app-shell-background: var(--background);
  --app-text: var(--foreground);
  --app-text-strong: var(--foreground);
  --app-text-muted: var(--muted-foreground);
  --app-surface: color-mix(in srgb, var(--card) 92%, transparent);
  --app-surface-solid: var(--card);
  --app-surface-muted: var(--muted);
  --app-border: var(--border);
  --app-border-strong: color-mix(in srgb, var(--border) 78%, var(--foreground));
  --app-primary: var(--primary);
  --app-primary-hover: color-mix(in srgb, var(--primary) 90%, var(--background));
  --app-primary-fg: var(--primary-foreground);
  --app-accent: var(--accent-foreground);
  --app-accent-soft: var(--accent);
  --app-input: var(--background);
  --app-input-border: var(--input);
  --app-ring: color-mix(in srgb, var(--ring) 24%, transparent);
  --app-error: var(--destructive);
  --app-shadow: none;
}
```

For `[data-theme='dark']` and `[data-theme='purple']`, keep the existing selector blocks but remove duplicated palette values that conflict with semantic tokens. The dark and purple theme values now live in `index.css`; `App.css` should only keep local layout-specific values and sidebar aliases.

- [ ] **Step 7: Run sidebar test to verify it passes**

Run:

```powershell
pnpm --dir frontend test src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Run focused component tests**

Run:

```powershell
pnpm --dir frontend test src/lib/utils.test.ts src/components/ui/button.test.tsx src/components/ui/nav.test.tsx
```

Expected: PASS.

- [ ] **Step 9: Commit shell adoption**

Run:

```powershell
git add frontend/src/App.tsx frontend/src/App.css frontend/src/App.test.tsx
git commit -m "feat(frontend): adopt design primitives in shell"
```

---

### Task 7: Full Frontend Verification

**Files:**
- No code changes expected unless verification exposes a concrete defect.

- [ ] **Step 1: Run full frontend tests**

Run:

```powershell
pnpm --dir frontend test
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend typecheck**

Run:

```powershell
pnpm --dir frontend typecheck
```

Expected: command exits `0`.

- [ ] **Step 3: Run frontend lint**

Run:

```powershell
pnpm --dir frontend lint
```

Expected: command exits `0`.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
pnpm --dir frontend build
```

Expected: command exits `0` and Vite emits a production build.

- [ ] **Step 5: Start dev server for browser QA**

Run:

```powershell
pnpm --dir frontend dev -- --host 127.0.0.1
```

Expected: Vite prints a localhost URL. Keep this process running only while doing browser QA.

- [ ] **Step 6: Browser QA desktop**

Open the Vite URL at a desktop-sized viewport and verify:

- Left sidebar opens and collapses.
- Active `Chat` primary nav has `aria-current="page"` and remains visually active.
- Buttons retain readable text and visible focus state.
- Chat screen renders without overlapping text.
- Settings navigation still opens when selecting `Settings`.

- [ ] **Step 7: Browser QA mobile-sized viewport**

Set viewport width near `390px` and verify:

- Sidebar toggle remains reachable.
- Sidebar collapsed state does not cover the main content unexpectedly.
- Topline session/project labels truncate instead of overflowing.
- Icon buttons remain square and do not resize surrounding layout.

- [ ] **Step 8: Stop dev server**

Stop the Vite process with `Ctrl+C` in the terminal where it is running.

- [ ] **Step 9: Commit verification fixes if needed**

If browser QA required a code fix, run:

```powershell
git add frontend/src/App.tsx frontend/src/App.css frontend/src/index.css frontend/src/components/ui
git commit -m "fix(frontend): polish design system shell qa"
```

If no fix was required, do not create an empty commit.
