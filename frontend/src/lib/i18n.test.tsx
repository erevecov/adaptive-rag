/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test } from 'vitest'

import {
  LocaleProvider,
  LOCALE_STORAGE_KEY,
  translate,
  useLocale,
} from './i18n'

afterEach(() => {
  cleanup()
  localStorage.removeItem(LOCALE_STORAGE_KEY)
})

function Probe() {
  const { locale, setLocale, t } = useLocale()
  return (
    <div>
      <p>{t('session.newChat')}</p>
      <button type="button" onClick={() => setLocale('es')}>
        to-es
      </button>
      <span data-testid="locale">{locale}</span>
    </div>
  )
}

describe('i18n', () => {
  test('defaults to English copy', () => {
    expect(translate('en', 'session.newChat')).toBe('New chat')
    expect(translate('en', 'session.open', { title: 'Hello' })).toBe(
      'Open session Hello',
    )
  })

  test('translates Spanish session labels without mojibake', () => {
    expect(translate('es', 'session.open', { title: 'Hola' })).toBe(
      'Abrir sesión Hola',
    )
    expect(translate('es', 'session.renameLabel')).toBe(
      'Nuevo nombre de sesión',
    )
    expect(translate('es', 'session.loadMore')).toBe('Ver más')
  })

  test('LocaleProvider persists language selection', async () => {
    const user = userEvent.setup()
    render(
      <LocaleProvider>
        <Probe />
      </LocaleProvider>,
    )

    expect(screen.getByText('New chat')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'to-es' }))
    expect(screen.getByText('Nuevo chat')).toBeTruthy()
    expect(screen.getByTestId('locale').textContent).toBe('es')
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('es')
  })
})
