import type { Status } from '../types'

export const statusInfo: Record<Status, { label: string; short: string; color: string; symbol: string }> = {
  operational: { label: 'Operational', short: 'Working', color: '#23815e', symbol: '✓' },
  out_of_service: { label: 'Out of service', short: 'Out', color: '#cb493d', symbol: '×' },
  verification_needed: { label: 'Needs verification', short: 'Check', color: '#b78323', symbol: '!' },
  unknown: { label: 'Status unknown', short: 'Unknown', color: '#858781', symbol: '?' },
}
export function statusOf(value: string | undefined): Status { return value && value in statusInfo ? value as Status : 'unknown' }
export function formatTime(value: string | null | undefined): string {
  if (!value) return 'Not yet reported'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Not yet reported'
  return new Intl.DateTimeFormat('en-CA', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Toronto' }).format(date)
}
export function relativeTime(value: string | null | undefined): string {
  if (!value) return 'No update yet'
  const diff = Date.now() - new Date(value).getTime()
  if (!Number.isFinite(diff)) return 'No update yet'
  if (diff < 0) return formatTime(value)
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hr ago`
  return `${Math.floor(hours / 24)} days ago`
}
export function percent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${(value <= 1 && value > 0 ? value * 100 : value).toFixed(1)}%`
}
