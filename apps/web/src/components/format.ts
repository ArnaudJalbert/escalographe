import type { Status } from '../types'
import type { Locale } from '../i18n'

export const statusInfo: Record<Status, { label: string; short: string; color: string; symbol: string }> = {
  operational: { label: 'Operational', short: 'Working', color: '#23815e', symbol: '✓' },
  out_of_service: { label: 'Out of service', short: 'Out', color: '#cb493d', symbol: '×' },
  verification_needed: { label: 'Needs verification', short: 'Check', color: '#b78323', symbol: '!' },
  unknown: { label: 'Status unknown', short: 'Unknown', color: '#858781', symbol: '?' },
}
export function statusOf(value: string | undefined): Status { return value && value in statusInfo ? value as Status : 'unknown' }
export function statusLabel(value: string | undefined, locale: Locale): string {
  const status = statusOf(value)
  return locale === 'fr' ? { operational: 'En service', out_of_service: 'Pété', verification_needed: 'À vérifier', unknown: 'État inconnu' }[status] : statusInfo[status].label
}
export function directionLabel(value: string | null | undefined, locale: Locale): string {
  if (!value) return locale === 'fr' ? 'Direction inconnue' : 'Direction unknown'
  const known: Record<string, string> = { up: 'Montée', down: 'Descente', reversible: 'Réversible' }
  return locale === 'fr' ? known[value.toLowerCase()] || value : value
}
export function formatTime(value: string | null | undefined, locale: Locale = 'fr'): string {
  if (!value) return locale === 'fr' ? 'Pas encore signalé' : 'Not yet reported'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return locale === 'fr' ? 'Pas encore signalé' : 'Not yet reported'
  return new Intl.DateTimeFormat(locale === 'fr' ? 'fr-CA' : 'en-CA', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Toronto' }).format(date)
}
export function formatDateLabel(value: string, locale: Locale): string {
  if (!/^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(value)) return value
  const date = new Date(value.length === 10 ? `${value}T12:00:00Z` : value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(locale === 'fr' ? 'fr-CA' : 'en-CA', { month: 'short', day: 'numeric', timeZone: 'America/Toronto' }).format(date)
}
export function relativeTime(value: string | null | undefined, locale: Locale = 'fr'): string {
  if (!value) return locale === 'fr' ? 'Aucune mise à jour' : 'No update yet'
  const diff = Date.now() - new Date(value).getTime()
  if (!Number.isFinite(diff)) return locale === 'fr' ? 'Aucune mise à jour' : 'No update yet'
  if (diff < 0) return formatTime(value, locale)
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return locale === 'fr' ? 'À l’instant' : 'Just now'
  if (minutes < 60) return locale === 'fr' ? `il y a ${minutes} min` : `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return locale === 'fr' ? `il y a ${hours} h` : `${hours} hr ago`
  return locale === 'fr' ? `il y a ${Math.floor(hours / 24)} j` : `${Math.floor(hours / 24)} days ago`
}
export function percent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${(value <= 1 && value > 0 ? value * 100 : value).toFixed(1)}%`
}
