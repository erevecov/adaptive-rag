# Runtime Navigation Clarity Design

This change implements the approved design in
`docs/superpowers/specs/2026-06-29-runtime-navigation-design.md`.

## Decisions

- Keep one product shell.
- Keep `Chat`, `My account` and `Settings` as primary sidebar navigation.
- Render secondary navigation inside the sidebar based on the selected primary
  view.
- Use explicit state for selected account module, settings module and settings
  submodule.
- Keep backend runtime contracts unchanged.
- Split the Runtime UI into named panels that reuse existing handlers and API
  client calls.

## Runtime Submodules

- `Connections`: provider connection list, connection form and secret rotation.
- `Model catalog`: model sync selector/action and provider model catalog.
- `Global defaults`: fixed slots, chat model pool and global chat retrieval.
- `Project overrides`: effective project runtime settings and reset actions.

## Non-goals

- No new backend routes.
- No durable memory implementation.
- No full URL router.
- No runtime provider or slot redesign.
