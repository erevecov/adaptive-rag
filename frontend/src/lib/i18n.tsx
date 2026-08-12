import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type Locale = 'en' | 'es'

export const LOCALE_STORAGE_KEY = 'adaptive-rag-locale'
export const DEFAULT_LOCALE: Locale = 'en'

const EN = {
  'account.appearance': 'Appearance',
  'account.language': 'Language',
  'account.languageDescription': 'Choose the interface language.',
  'account.myAccount': 'My Account',
  'account.themeDescription': 'Choose the interface palette.',
  'auth.feedback': 'Feedback',
  'auth.feedbackSoon': 'Feedback will be available soon.',
  'auth.signOut': 'Sign out',
  'auth.signOutFailed': 'Sign out failed. Please try again.',
  'locale.en': 'English',
  'locale.enDescription': 'Default product language.',
  'locale.es': 'Español',
  'locale.esDescription': 'Spanish interface labels.',
  'session.actions': 'Options for {title}',
  'session.active': 'Active',
  'session.activeTitle': 'Active sessions',
  'session.archive': 'Archive',
  'session.archived': 'Archived',
  'session.archivedTitle': 'Archived sessions',
  'session.copyId': 'Copy session ID',
  'session.copyIdFailed': 'Could not copy session ID.',
  'session.copyIdOk': 'Session ID copied.',
  'session.delete': 'Delete',
  'session.deleteConfirm':
    'Delete this session permanently? This cannot be undone.',
  'session.emptyActive': 'No conversations yet.',
  'session.emptyArchived': 'No archived conversations yet.',
  'session.emptyTraining': 'No training sessions yet.',
  'session.lastActivity': 'Last activity: {value}',
  'session.lastActivityUnknown': 'Last activity unknown',
  'session.loading': 'Loading…',
  'session.loadingSessions': 'Loading sessions',
  'session.loadMore': 'Show more',
  'session.newChat': 'New chat',
  'session.newChatTitle': 'New chat',
  'session.open': 'Open session {title}',
  'session.openWithStatus': 'Open session {title} ({status})',
  'session.rename': 'Rename',
  'session.renameLabel': 'New session name',
  'session.sessions': 'Sessions',
  'session.train': 'Train',
  'session.trainingApproved': 'approved training',
  'session.trainingPending': 'pending training',
  'session.trainTitle': 'Training sessions',
  'session.unarchive': 'Unarchive',
  'time.now': 'now',
  'workspace.noAccess': 'You do not have access to that workspace',
  'workspace.none': 'No workspace',
  'workspace.selected': 'Selected workspace',
} as const

type MessageKey = keyof typeof EN

const ES: Record<MessageKey, string> = {
  'account.appearance': 'Apariencia',
  'account.language': 'Idioma',
  'account.languageDescription': 'Elige el idioma de la interfaz.',
  'account.myAccount': 'Mi cuenta',
  'account.themeDescription': 'Elige la paleta de la interfaz.',
  'auth.feedback': 'Feedback',
  'auth.feedbackSoon': 'El feedback estará disponible pronto.',
  'auth.signOut': 'Salir',
  'auth.signOutFailed': 'No se pudo cerrar la sesión. Inténtalo de nuevo.',
  'locale.en': 'English',
  'locale.enDescription': 'Idioma predeterminado del producto.',
  'locale.es': 'Español',
  'locale.esDescription': 'Etiquetas de la interfaz en español.',
  'session.actions': 'Opciones de {title}',
  'session.active': 'Activos',
  'session.activeTitle': 'Sesiones activas',
  'session.archive': 'Archivar',
  'session.archived': 'Archivados',
  'session.archivedTitle': 'Sesiones archivadas',
  'session.copyId': 'Copiar ID de sesión',
  'session.copyIdFailed': 'No se pudo copiar el ID de sesión.',
  'session.copyIdOk': 'ID de sesión copiado.',
  'session.delete': 'Eliminar',
  'session.deleteConfirm':
    '¿Eliminar esta sesión de forma permanente? No se puede deshacer.',
  'session.emptyActive': 'Aún no hay conversaciones.',
  'session.emptyArchived': 'Aún no hay conversaciones archivadas.',
  'session.emptyTraining': 'Aún no hay entrenamiento.',
  'session.lastActivity': 'Última actividad: {value}',
  'session.lastActivityUnknown': 'Última actividad desconocida',
  'session.loading': 'Cargando…',
  'session.loadingSessions': 'Cargando sesiones',
  'session.loadMore': 'Ver más',
  'session.newChat': 'Nuevo chat',
  'session.newChatTitle': 'Nuevo chat',
  'session.open': 'Abrir sesión {title}',
  'session.openWithStatus': 'Abrir sesión {title} ({status})',
  'session.rename': 'Renombrar',
  'session.renameLabel': 'Nuevo nombre de sesión',
  'session.sessions': 'Sesiones',
  'session.train': 'Train',
  'session.trainingApproved': 'entrenamiento aprobado',
  'session.trainingPending': 'entrenamiento pendiente',
  'session.trainTitle': 'Sesiones con entrenamiento',
  'session.unarchive': 'Desarchivar',
  'time.now': 'ahora',
  'workspace.noAccess': 'No tienes acceso a ese workspace',
  'workspace.none': 'Sin workspace',
  'workspace.selected': 'Workspace seleccionado',
}

const MESSAGES: Record<Locale, Record<MessageKey, string>> = {
  en: EN,
  es: ES,
}

export type TranslateFn = (
  key: MessageKey,
  vars?: Record<string, string>,
) => string

type LocaleContextValue = {
  locale: Locale
  setLocale(locale: Locale): void
  t: TranslateFn
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function isLocale(value: unknown): value is Locale {
  return value === 'en' || value === 'es'
}

export function readPersistedLocale(): Locale {
  try {
    const cached = localStorage.getItem(LOCALE_STORAGE_KEY)
    return isLocale(cached) ? cached : DEFAULT_LOCALE
  } catch {
    return DEFAULT_LOCALE
  }
}

export function applyDocumentLocale(locale: Locale): void {
  document.documentElement.lang = locale
}

export function translate(
  locale: Locale,
  key: MessageKey,
  vars?: Record<string, string>,
): string {
  let message = MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key
  if (vars !== undefined) {
    for (const [name, value] of Object.entries(vars)) {
      message = message.replaceAll(`{${name}}`, value)
    }
  }
  return message
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => readPersistedLocale())

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, next)
    } catch {
      // Ignore quota / private-mode failures; in-memory locale still applies.
    }
    applyDocumentLocale(next)
  }, [])

  const t = useCallback<TranslateFn>(
    (key, vars) => translate(locale, key, vars),
    [locale],
  )

  const value = useMemo(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t],
  )

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  )
}

export function useLocale(): LocaleContextValue {
  const value = useContext(LocaleContext)
  if (value !== null) {
    return value
  }
  return {
    locale: DEFAULT_LOCALE,
    setLocale() {
      // No-op outside LocaleProvider (unit tests render App directly).
    },
    t(key, vars) {
      return translate(DEFAULT_LOCALE, key, vars)
    },
  }
}
