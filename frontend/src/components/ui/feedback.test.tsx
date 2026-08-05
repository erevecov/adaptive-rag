/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Callout, EmptyState, InlineFeedback } from './feedback'

afterEach(() => {
  cleanup()
})

describe('EmptyState', () => {
  test('uses stacked density with gap for multi-line operator copy', () => {
    render(
      <EmptyState>
        <p>No projects yet.</p>
        <p>Create one above.</p>
      </EmptyState>,
    )

    const empty = screen.getByText('No projects yet.').parentElement
    expect(empty?.getAttribute('data-slot')).toBe('empty-state')
    expect(empty?.className).toMatch(/flex/)
    expect(empty?.className).toMatch(/flex-col/)
    expect(empty?.className).toMatch(/gap-1\.5/)
  })
})

describe('InlineFeedback', () => {
  test('success tone uses emerald contrast for dark/purple themes', () => {
    render(<InlineFeedback tone="success">Saved</InlineFeedback>)

    const feedback = screen.getByText('Saved')
    expect(feedback.className).toContain('text-emerald-700')
    expect(feedback.getAttribute('data-tone')).toBe('success')
  })
})

describe('Callout', () => {
  test('success callout keeps emerald contrast on tinted fill', () => {
    render(<Callout tone="success">Ready</Callout>)

    const callout = screen.getByText('Ready')
    expect(callout.className).toContain('text-emerald-700')
    expect(callout.className).toContain('bg-emerald-500/15')
  })
})
