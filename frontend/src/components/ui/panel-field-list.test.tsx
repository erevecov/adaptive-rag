/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { DataList, DataListItem } from './data-list'
import { Field, FieldError, FieldHelp, FieldLabel, FieldControl } from './field'
import { Panel, PanelBody, PanelDescription, PanelHeader, PanelTitle } from './panel'

afterEach(() => {
  cleanup()
})

describe('Panel density', () => {
  test('defaults to 4/8 spacing rhythm', () => {
    render(
      <Panel>
        <PanelHeader>Header</PanelHeader>
        <PanelBody>Body</PanelBody>
      </Panel>,
    )

    expect(screen.getByText('Header').className).toMatch(/\bp-4\b/)
    expect(screen.getByText('Header').className).toContain('max-[680px]:p-0.5')
    expect(screen.getByText('Body').className).toMatch(/\bp-4\b/)
    expect(screen.getByText('Body').className).toContain('max-[680px]:p-0.5')
    expect(screen.getByText('Body').className).toMatch(/pt-0/)
  })

  test('panel shell transitions colors; description stays compact', () => {
    render(
      <Panel>
        <PanelHeader>
          <PanelTitle>Appearance</PanelTitle>
          <PanelDescription>Choose the interface palette.</PanelDescription>
        </PanelHeader>
      </Panel>,
    )

    const panel = screen.getByText('Appearance').closest('[data-slot="panel"]')
    expect(panel?.className).toContain('motion-safe:transition-colors')
    expect(panel?.className).toContain('max-[680px]:rounded-md')
    expect(panel?.className).toContain('max-[680px]:shadow-primary/95')
    expect(screen.getByText('Appearance').className).toContain('tracking-tight')
    expect(screen.getByText('Appearance').className).toContain('max-[680px]:tracking-tighter')
    expect(screen.getByText('Appearance').className).toContain('max-[680px]:text-[0.5625rem]')
    expect(screen.getByText('Appearance').className).toContain('max-[680px]:leading-tight')
    const description = screen.getByText('Choose the interface palette.')
    expect(description.getAttribute('data-slot')).toBe('panel-description')
    expect(description.className).toContain('text-xs')
    expect(description.className).toContain('leading-relaxed')
    expect(description.className).toContain('max-[680px]:text-[0.5625rem]')
    expect(description.className).toContain('max-[680px]:tracking-tighter')
  })
})

describe('Field disabled styling', () => {
  test('label dims when a descendant control is disabled', () => {
    render(
      <Field>
        <FieldLabel htmlFor="x">Name</FieldLabel>
        <FieldControl>
          <input disabled id="x" />
        </FieldControl>
      </Field>,
    )

    const field = screen.getByText('Name').closest('[data-slot="field"]')
    expect(field?.className).toContain('group/field')
    expect(field?.className).toContain('max-[680px]:gap-0.5')
    expect(
      screen.getByText('Name').closest('[data-slot="field"]')?.querySelector(
        '[data-slot="field-control"]',
      )?.className,
    ).toContain('max-[680px]:gap-0.5')
    expect(screen.getByText('Name').className).toContain('tracking-tight')
    expect(screen.getByText('Name').className).toContain('max-[680px]:tracking-tighter')
    expect(screen.getByText('Name').className).toContain('max-[680px]:text-[0.5625rem]')
    expect(screen.getByText('Name').className).toContain(
      'group-has-[:disabled]/field:opacity-70',
    )
  })
})

describe('FieldHelp density', () => {
  test('uses compact xs help copy for operator forms', () => {
    render(
      <Field>
        <FieldLabel htmlFor="token">Token</FieldLabel>
        <FieldHelp id="token-help">Paste once; never shown after save.</FieldHelp>
      </Field>,
    )

    const help = screen.getByText('Paste once; never shown after save.')
    expect(help.getAttribute('data-slot')).toBe('field-help')
    expect(help.className).toContain('text-xs')
    expect(help.className).toContain('leading-relaxed')
    expect(help.className).toContain('max-[680px]:tracking-tighter')
  })
})

describe('FieldError density', () => {
  test('keeps compact destructive alert copy', () => {
    render(<FieldError>Required.</FieldError>)

    const error = screen.getByRole('alert')
    expect(error.getAttribute('data-slot')).toBe('field-error')
    expect(error.className).toContain('text-xs')
    expect(error.className).toContain('text-destructive')
    expect(error.className).toContain('leading-relaxed')
    expect(error.className).toContain('max-[680px]:tracking-tighter')
  })
})

describe('DataListItem', () => {
  test('allows truncation inside flex rows via min-w-0', () => {
    render(
      <DataList>
        <DataListItem>row</DataListItem>
      </DataList>,
    )

    const list = screen.getByText('row').closest('[data-slot="data-list"]')
    expect(list?.className).toContain('max-[680px]:gap-0.5')
    const row = screen.getByText('row')
    expect(row.className).toContain('min-w-0')
    expect(row.className).toContain('motion-safe:transition-colors')
    expect(row.className).toContain('hover:bg-primary/15')
    expect(row.className).toContain('max-[680px]:hover:bg-primary/50')
    expect(row.className).toContain('active:bg-primary/20')
    expect(row.className).toContain('max-[680px]:active:bg-primary/95')
    expect(row.className).toContain('focus-visible:bg-primary/15')
    expect(row.className).toContain('max-[680px]:focus-visible:bg-primary/40')
    expect(row.className).toContain('focus-visible:ring-inset')
    expect(row.className).toContain('max-[680px]:rounded-sm')
    expect(row.className).toContain('max-[680px]:p-0.5')
    expect(row.className).toContain('tracking-tight')
    expect(row.className).toContain('max-[680px]:text-[0.5625rem]')
    expect(row.className).toContain('max-[680px]:leading-snug')
    expect(row.className).toContain('max-[680px]:tracking-tighter')
    expect(row.className).toContain('max-[680px]:shadow-primary/95')
  })
})
