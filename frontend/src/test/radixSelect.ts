import { screen } from '@testing-library/react'
import type userEvent from '@testing-library/user-event'

export async function chooseRadixSelectOption(
  user: ReturnType<typeof userEvent.setup>,
  selectTrigger: HTMLElement,
  optionName: string | RegExp,
) {
  await user.click(selectTrigger)
  await user.click(await screen.findByRole('option', { name: optionName }))
}
