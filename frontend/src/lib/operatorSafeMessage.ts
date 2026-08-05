const SECRET_PATTERNS: RegExp[] = [
  /\bsk-[A-Za-z0-9_-]{8,}\b/g,
  /\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b/gi,
  /\bapi[_-]?key\s*[=:]\s*\S+/gi,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
]

/** Strip likely secrets from operator-facing error/status copy. */
export function operatorSafeMessage(
  message: string | null | undefined,
  fallback = 'Request failed. Check settings and try again.',
): string {
  if (message == null || message.trim().length === 0) {
    return fallback
  }
  let sanitized = message
  for (const pattern of SECRET_PATTERNS) {
    sanitized = sanitized.replace(pattern, '[redacted]')
  }
  const trimmed = sanitized.trim()
  return trimmed.length > 0 ? trimmed : fallback
}
