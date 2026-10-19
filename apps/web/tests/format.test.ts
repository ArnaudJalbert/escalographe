import { describe, expect, it } from 'vitest'
import { directionLabel, formatDateLabel, formatTime, relativeTime, statusLabel } from '../src/components/format'

describe('localized presentation', () => {
  it('formats observed dates in Montréal time in both languages', () => {
    const stamp = '2026-10-19T14:00:00Z'
    expect(formatTime(stamp, 'fr')).toMatch(/oct\.?.*10:00|oct\.?.*10 h 00/i)
    expect(formatTime(stamp, 'en')).toMatch(/Oct.*10:00/i)
    expect(formatDateLabel('2026-10-19', 'fr')).toMatch(/oct/i)
    expect(formatDateLabel('2026-10-19', 'en')).toMatch(/Oct/i)
    expect(relativeTime(null, 'fr')).toBe('Aucune mise à jour')
    expect(relativeTime(null, 'en')).toBe('No update yet')
  })
  it('translates normalized statuses and directions but preserves unrecognized source text', () => {
    expect(statusLabel('out_of_service', 'fr')).toBe('Hors service')
    expect(statusLabel('out_of_service', 'en')).toBe('Out of service')
    expect(statusLabel(undefined, 'fr')).toBe('État inconnu')
    expect(directionLabel('up', 'fr')).toBe('Montée')
    expect(directionLabel('up', 'en')).toBe('up')
    expect(directionLabel('STM source wording', 'fr')).toBe('STM source wording')
  })
})
