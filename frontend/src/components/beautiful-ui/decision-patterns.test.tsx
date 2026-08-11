/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { ApprovalPrompt } from './approval-prompt'
import { ChangeTable } from './change-table'
import { RecommendationPanel } from './recommendation-panel'
import { SelectionToolbar } from './selection-toolbar'

afterEach(() => {
  cleanup()
})

describe('ApprovalPrompt', () => {
  test('emits only the chosen id', async () => {
    const user = userEvent.setup()
    const onChoose = vi.fn()
    render(
      <ApprovalPrompt
        choices={[{ id: 'approve', label: 'Approve' }, { id: 'reject', label: 'Reject' }]}
        onChoose={onChoose}
        question="Review proposal"
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Approve' }))

    expect(onChoose).toHaveBeenCalledWith('approve')
    expect(onChoose).toHaveBeenCalledTimes(1)
  })

  test('disables choices while busy', () => {
    render(
      <ApprovalPrompt
        busy
        choices={[{ id: 'approve', label: 'Approve' }]}
        onChoose={() => undefined}
        question="Review proposal"
      />,
    )

    expect((screen.getByRole('button', { name: 'Approve' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
  })

  test('submits a trimmed custom answer only when it is non-empty', async () => {
    const user = userEvent.setup()
    const onCustomSubmit = vi.fn()
    render(
      <ApprovalPrompt
        choices={[]}
        customLabel="Refinement"
        onChoose={() => undefined}
        onCustomSubmit={onCustomSubmit}
        question="Review proposal"
      />,
    )

    const input = screen.getByRole('textbox', { name: 'Refinement' })
    await user.type(input, '  Add source links  ')
    await user.click(screen.getByRole('button', { name: 'Submit refinement' }))
    await user.click(screen.getByRole('button', { name: 'Submit refinement' }))

    expect(onCustomSubmit).toHaveBeenCalledWith('Add source links')
    expect(onCustomSubmit).toHaveBeenCalledTimes(1)
  })

  test('disables the custom input and submit control while busy', () => {
    render(
      <ApprovalPrompt
        busy
        choices={[]}
        customLabel="Refinement"
        onChoose={() => undefined}
        onCustomSubmit={() => undefined}
        question="Review proposal"
      />,
    )

    expect((screen.getByRole('textbox', { name: 'Refinement' }) as HTMLInputElement).disabled).toBe(
      true,
    )
    expect(
      (screen.getByRole('button', { name: 'Submit refinement' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  test('assigns distinct custom input ids to multiple prompts', () => {
    render(
      <>
        <ApprovalPrompt
          choices={[]}
          customLabel="First refinement"
          onChoose={() => undefined}
          onCustomSubmit={() => undefined}
          question="First proposal"
        />
        <ApprovalPrompt
          choices={[]}
          customLabel="Second refinement"
          onChoose={() => undefined}
          onCustomSubmit={() => undefined}
          question="Second proposal"
        />
      </>,
    )

    expect(screen.getByRole('textbox', { name: 'First refinement' }).getAttribute('id')).not.toBe(
      screen.getByRole('textbox', { name: 'Second refinement' }).getAttribute('id'),
    )
  })
})

describe('RecommendationPanel', () => {
  test('emits acceptance through its caller callback', async () => {
    const user = userEvent.setup()
    const onAccept = vi.fn()
    render(
      <RecommendationPanel
        description="Use the evaluated retriever configuration."
        onAccept={onAccept}
        title="Retriever recommendation"
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Accept recommendation' }))

    expect(onAccept).toHaveBeenCalledTimes(1)
  })

  test('displays supplied confidence within its bounds and reports alternatives by id', async () => {
    const user = userEvent.setup()
    const onAlternative = vi.fn()
    render(
      <RecommendationPanel
        alternatives={[{ description: 'Keep the existing model', id: 'keep', label: 'Keep current' }]}
        confidence={150}
        description="Use the evaluated retriever configuration."
        onAccept={() => undefined}
        onAlternative={onAlternative}
        title="Retriever recommendation"
      />,
    )

    expect((screen.getByRole('progressbar', { name: 'Confidence' }) as HTMLProgressElement).value).toBe(
      100,
    )
    await user.click(screen.getByRole('button', { name: 'Keep current' }))

    expect(onAlternative).toHaveBeenCalledWith('keep')
  })

  test('does not invent confidence when the caller omits it', () => {
    render(
      <RecommendationPanel
        description="Use the evaluated retriever configuration."
        onAccept={() => undefined}
        title="Retriever recommendation"
      />,
    )

    expect(screen.queryByRole('progressbar', { name: 'Confidence' })).toBeNull()
  })

  test('clamps negative confidence to zero', () => {
    render(
      <RecommendationPanel
        confidence={-10}
        description="Use the evaluated retriever configuration."
        onAccept={() => undefined}
        title="Retriever recommendation"
      />,
    )

    expect((screen.getByRole('progressbar', { name: 'Confidence' }) as HTMLProgressElement).value).toBe(
      0,
    )
  })
})

describe('ChangeTable', () => {
  test('uses semantic headers for original and proposed values', () => {
    render(
      <ChangeTable
        label="Proposal changes"
        rows={[{ field: 'Title', id: 'title', original: 'Draft', proposed: 'Published' }]}
      />,
    )

    const table = screen.getByRole('table', { name: 'Proposal changes' })
    expect(table).toBeTruthy()
    expect(table.querySelector('caption')?.textContent).toBe('Proposal changes')
    expect(screen.getByRole('columnheader', { name: 'Field' }).getAttribute('scope')).toBe('col')
    expect(screen.getByRole('columnheader', { name: 'Original' }).getAttribute('scope')).toBe('col')
    expect(screen.getByRole('columnheader', { name: 'Proposed' }).getAttribute('scope')).toBe('col')
    expect(screen.getByRole('rowheader', { name: 'Title' }).getAttribute('scope')).toBe('row')
  })
})

describe('SelectionToolbar', () => {
  test('stays generic and emits a semantic action id', async () => {
    const user = userEvent.setup()
    const onAction = vi.fn()
    render(
      <SelectionToolbar
        actions={[{ id: 'explain', label: 'Explain' }]}
        onAction={onAction}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Explain' }))

    expect(onAction).toHaveBeenCalledWith('explain')
  })

  test('disables every action when disabled', () => {
    render(
      <SelectionToolbar
        actions={[{ id: 'explain', label: 'Explain' }, { id: 'copy', label: 'Copy' }]}
        disabled
        onAction={() => undefined}
      />,
    )

    expect((screen.getByRole('button', { name: 'Explain' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Copy' }) as HTMLButtonElement).disabled).toBe(true)
  })
})

test('decision containers retain square chrome', () => {
  const { container } = render(
    <>
      <ApprovalPrompt choices={[]} onChoose={() => undefined} question="Review proposal" />
      <RecommendationPanel
        description="Use the evaluated retriever configuration."
        onAccept={() => undefined}
        title="Retriever recommendation"
      />
      <ChangeTable label="Proposal changes" rows={[]} />
      <SelectionToolbar actions={[]} onAction={() => undefined} />
    </>,
  )

  for (const selector of [
    '[data-slot="approval-prompt"]',
    '[data-slot="recommendation-panel"]',
    '[data-slot="change-table"]',
    '[data-slot="selection-toolbar"]',
  ]) {
    expect(container.querySelector(selector)?.className).toContain('rounded-[2px]')
  }
})
