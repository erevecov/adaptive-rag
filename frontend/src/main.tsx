import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import {
  LocaleProvider,
  applyDocumentLocale,
  readPersistedLocale,
} from './lib/i18n.tsx'
import { applyTheme, readPersistedTheme } from './lib/theme.ts'

applyTheme(readPersistedTheme())
applyDocumentLocale(readPersistedLocale())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LocaleProvider>
      <App />
    </LocaleProvider>
  </StrictMode>,
)
