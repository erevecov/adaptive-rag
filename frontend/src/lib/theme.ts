type ThemeSwatch = {
  accent: string
  bg: string
  fg: string
  muted: string
}

export type Theme = 'light' | 'dark' | 'purple'

export type ThemeDef = {
  description: string
  id: Theme
  label: string
  swatch: ThemeSwatch
}

export const THEMES: readonly ThemeDef[] = [
  {
    description: 'Clean daylight palette for authoring and review work.',
    id: 'light',
    label: 'Light',
    swatch: { accent: '#23423e', bg: '#f4f6f8', fg: '#18201f', muted: '#63706d' },
  },
  {
    description: 'Black palette for low-light sessions.',
    id: 'dark',
    label: 'Dark',
    swatch: { accent: '#f5f5f5', bg: '#000000', fg: '#f5f5f5', muted: '#a3a3a3' },
  },
  {
    description: 'High-contrast purple workspace palette.',
    id: 'purple',
    label: 'Purple',
    swatch: { accent: '#7f68ff', bg: '#070513', fg: '#f4f0ff', muted: '#a99bd5' },
  },
] as const

export const DEFAULT_THEME: Theme = 'purple'
export const THEME_STORAGE_KEY = 'adaptive-rag-theme'

const DARK_THEMES: ReadonlySet<Theme> = new Set(['dark', 'purple'])
const THEME_IDS: ReadonlySet<string> = new Set(THEMES.map((theme) => theme.id))

export function isTheme(value: unknown): value is Theme {
  return typeof value === 'string' && THEME_IDS.has(value)
}

export function isDarkTheme(theme: Theme): boolean {
  return DARK_THEMES.has(theme)
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
  root.classList.toggle('dark', isDarkTheme(theme))
}

export function readPersistedTheme(): Theme {
  const cached = localStorage.getItem(THEME_STORAGE_KEY)
  return isTheme(cached) ? cached : DEFAULT_THEME
}
