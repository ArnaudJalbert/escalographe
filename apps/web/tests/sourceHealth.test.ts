import { describe, expect, it, vi } from 'vitest'
import { sourceHealth } from '../src/components/sourceHealth'

describe('source health', () => {
  it('keeps the last successful refresh distinct from a failed attempt', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-19T11:15:00Z'))
    try {
      expect(sourceHealth([
      { source: 'stm', success: false, started_at: '2026-10-19T11:00:00Z', finished_at: '2026-10-19T11:01:00Z' },
      { source: 'osm', success: true, started_at: '2026-10-19T10:00:00Z', finished_at: '2026-10-19T10:01:00Z' },
      { source: 'stm', success: true, started_at: '2026-10-19T09:00:00Z', finished_at: '2026-10-19T09:01:00Z' },
    ])).toEqual([
      expect.objectContaining({ source: 'stm', healthy: false, is_stale: true, last_attempt: '2026-10-19T11:01:00Z', last_success: '2026-10-19T09:01:00Z' }),
      expect.objectContaining({ source: 'osm', healthy: true, is_stale: false, last_success: '2026-10-19T10:01:00Z' }),
    ])
    } finally {
      vi.useRealTimers()
    }
  })
})
