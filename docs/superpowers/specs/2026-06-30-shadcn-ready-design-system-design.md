# Shadcn-Ready Design System Foundation

## Context

The frontend is a Vite + React application with a large `App.tsx`, custom CSS in
`App.css`, and only `react`/`react-dom` as runtime dependencies. The goal is to
introduce a Vercel-inspired design system foundation without doing a full app
restyle yet.

The product direction is:

- Minimal, modern, neutral, and work-focused.
- Compatible with Radix UI and shadcn/ui future adoption.
- Start with foundation and shell, not a wholesale redesign.
- Use Tailwind CSS from the first slice because shadcn/ui is designed around
  Tailwind classes plus semantic CSS variables.

## Decision

Implement a shadcn-ready foundation with Tailwind CSS v4, but keep the first
implementation slice limited to design tokens, UI primitives, and low-risk shell
application.

This is not a full visual migration. The app behavior, API client, data flow,
chat streaming, route handling, and domain state remain unchanged.

## Goals

- Add Tailwind CSS v4 through the Vite plugin.
- Add shadcn-compatible project structure and configuration.
- Define semantic CSS variables compatible with shadcn/ui conventions.
- Create reusable UI primitives for repeated shell/control patterns.
- Apply the foundation to the app shell and low-risk repeated controls.
- Preserve the current user workflows.
- Keep the implementation ready for future Radix/shadcn component adoption.

## Non-Goals

- Do not rewrite `App.tsx` wholesale.
- Do not restyle every chat, runtime, observability, authoring, and account
  surface in this slice.
- Do not change `ApiClient`, request orchestration, chat streaming, persistence,
  or routing behavior.
- Do not install Radix primitives until a concrete component needs them.
- Do not introduce TanStack Query, Router, Table, or Form as part of this slice.
- Do not add a marketing-style landing page or decorative visual layer.

## Visual Direction

The first design language should be inspired by Vercel's product surfaces:

- Dark-first neutral palette, with a light theme preserved.
- True neutral backgrounds, restrained contrast, and thin borders.
- Small radii, generally `6px` to `10px`.
- Compact control density with strong text hierarchy.
- Minimal elevation; prefer borders and background shifts over shadows.
- Clear focus rings through a shared `--ring` token.
- No gradient orbs, bokeh, decorative cards, or broad restyle gestures.

The design should feel like a precise product console: quiet, readable, and
suited to repeated operational use.

## Tailwind And Shadcn Setup

Add Tailwind CSS v4 as the styling engine for new design-system work:

- Install `tailwindcss` and `@tailwindcss/vite`.
- Install `clsx`, `tailwind-merge`, and `class-variance-authority` when the
  first `ui/*` components use `cn(...)` and typed variants.
- Set `iconLibrary` to `lucide` for shadcn compatibility; install
  `lucide-react` only when the implementation first replaces local SVG icons or
  adds a shadcn component that imports lucide icons.
- Register `tailwindcss()` in `frontend/vite.config.ts` alongside the React
  plugin.
- Import Tailwind in `frontend/src/index.css`.
- Keep semantic CSS variables in `index.css` as the design-token contract.

Add a `components.json` compatible with shadcn/ui for a Vite React TypeScript
project:

- `style`: `new-york`.
- `rsc`: `false`.
- `tsx`: `true`.
- `tailwind.css`: `src/index.css`.
- `tailwind.baseColor`: `neutral`.
- `tailwind.cssVariables`: `true`.
- Aliases:
  - `components`: `@/components`
  - `ui`: `@/components/ui`
  - `lib`: `@/lib`
  - `utils`: `@/lib/utils`
  - `hooks`: `@/hooks`
- `iconLibrary`: `lucide`

The repository should also support the `@/` alias in TypeScript and Vite before
components depend on it.

## Tokens

Use shadcn-style semantic CSS variables as the public design API. Include both
light and dark values:

- `--background`
- `--foreground`
- `--card`
- `--card-foreground`
- `--popover`
- `--popover-foreground`
- `--primary`
- `--primary-foreground`
- `--secondary`
- `--secondary-foreground`
- `--muted`
- `--muted-foreground`
- `--accent`
- `--accent-foreground`
- `--destructive`
- `--destructive-foreground`
- `--border`
- `--input`
- `--ring`
- `--radius`

Bridge existing `--app-*` variables to the new semantic tokens during the
transition. Existing CSS can continue to work while new components use the
shadcn-compatible token names.

## Component Scope

Create `frontend/src/components/ui` with small presentational primitives:

- `button.tsx`
  - `Button`
  - `IconButton`
  - Variants: `primary`, `secondary`, `ghost`, `danger`
  - Sizes: `sm`, `md`, `icon`
- `panel.tsx`
  - `Panel`
  - `PanelHeader`
  - `PanelTitle`
  - `PanelDescription`
  - `PanelBody`
- `field.tsx`
  - `Field`
  - `FieldLabel`
  - `FieldControl`
  - `FieldHelp`
  - `FieldError`
- `nav.tsx`
  - `NavSection`
  - `SidebarItem`
  - Active, collapsed, disabled states

Create `frontend/src/lib/utils.ts` with a `cn(...)` class composition helper
compatible with shadcn conventions. The implementation can use `clsx` and
`tailwind-merge`.

Use `class-variance-authority` only where variants are genuinely useful, such
as `Button`. Avoid over-abstracting simple wrappers.

## Shell Application

Apply the first visual pass only to low-risk shell and repeated control areas:

- App shell background and layout tokens.
- Sidebar surface, section labels, active item, hover, collapsed state.
- Primary/secondary/ghost/icon buttons.
- Panel surfaces for repeated shell containers.
- Form field wrappers where the markup is straightforward.
- Tabs or segmented controls where they already exist as simple state switches.

Do not migrate feature-heavy regions in this slice unless the surrounding code
already makes it trivial. The chat composer, streaming transcript, runtime
forms, observability tables, and knowledge review flows should remain behavior-
first and can be migrated in later focused slices.

## Data Flow

All new `ui/*` components are presentational:

- They receive props, `className`, and children.
- They do not fetch data.
- They do not know about projects, sessions, providers, or chat state.
- They do not own domain state.

The existing app data flow remains intact. This keeps the design-system slice
separable from later data-fetching or component-architecture work.

## Accessibility

The foundation must preserve or improve accessibility:

- Visible focus ring through `--ring`.
- `aria-current` for active navigation items.
- `aria-invalid` and error text association for fields when applicable.
- `aria-expanded` for collapsible controls where applicable.
- Disabled states must be visually and semantically disabled.
- Icon-only buttons require accessible labels.

Future Radix components should inherit these tokens and interaction expectations
rather than define a separate visual language.

## Testing And Verification

Run the existing frontend gates after implementation:

- `pnpm --dir frontend test`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend lint`
- `pnpm --dir frontend build`

Add focused component tests only for behavior that can regress:

- Variant class selection if the helper logic is non-trivial.
- ARIA state mapping for nav and fields.
- Disabled/icon button accessible labels where practical.

Perform browser QA on desktop and mobile-sized viewports:

- Shell layout remains usable.
- Sidebar collapsed/open states still work.
- Text does not overflow controls.
- Focus states are visible.
- Existing chat/settings workflows still render.

This slice does not require pixel-perfect visual snapshot approval because it is
a foundation slice, not a full app redesign.

## Risks

The main risk is scope creep. Tailwind and shadcn readiness can tempt a broad
restyle. Keep this slice constrained to foundation, shell, and repeated
primitives.

The second risk is duplicate styling systems. Existing `App.css` should remain
during migration, but new reusable UI should use Tailwind plus semantic tokens.
Where existing `--app-*` tokens overlap with new shadcn-style tokens, bridge
them explicitly instead of maintaining two unrelated palettes.

The third risk is adding Radix too early. Radix should enter when a component
needs accessible behavior that native markup does not provide, such as dialog,
select, tooltip, dropdown menu, tabs, or popover.

## Follow-Up Slices

After this foundation lands, likely next slices are:

1. Migrate runtime settings forms and selects to shadcn/Radix-compatible
   primitives.
2. Add Radix `Dialog`, `Tooltip`, or `Select` for the first interaction that
   needs it.
3. Extract feature modules out of the large `App.tsx` while replacing local
   shell markup with `ui/*` components.
4. Consider TanStack Query separately for server-state cleanup once the design
   foundation is stable.

## Approved Direction

The approved direction is: shadcn-ready foundation with Tailwind from the first
slice, Vercel-inspired visual language, and no full app restyle yet.
