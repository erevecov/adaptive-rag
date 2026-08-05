/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { DataList, DataListItem } from './data-list'
import { Field, FieldHelp, FieldLabel } from './field'
import { Panel, PanelBody, PanelHeader } from './panel'

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
    expect(screen.getByText('Body').className).toMatch(/\bp-4\b/)
    expect(screen.getByText('Body').className).toMatch(/pt-0/)
  })
})

describe('Field disabled styling', () => {
  test('label dims when a descendant control is disabled', () => {
    render(
      <Field>
        <FieldLabel htmlFor="x">Name</FieldLabel>
        <input disabled id="x" />
      </Field>,
    )

    const field = screen.getByText('Name').closest('[data-slot="field"]')
    expect(field?.className).toContain('group/field')
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
  })
})

describe('DataListItem', () => {
  test('allows truncation inside flex rows via min-w-0', () => {
    render(
      <DataList>
        <DataListItem>row</DataListItem>
      </DataList>,
    )

    const row = screen.getByText('row')
    expect(row.className).toContain('min-w-0')
    expect(row.className).toContain('motion-safe:transition-colors')
    expect(row.className).toContain('hover:bg-muted/30')
  })
})
