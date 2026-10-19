import type { SourceHealth } from '../types'

/** /sources may return ingestion runs (newest first) or already-aggregated health. */
export function sourceHealth(rows: SourceHealth[]): SourceHealth[] {
  const names = [...new Set(rows.map(row => row.source || row.name).filter((name): name is string => !!name))]
  return names.map(name => {
    const runs = rows.filter(row => (row.source || row.name) === name).sort((a, b) => (b.started_at || b.last_attempt || '').localeCompare(a.started_at || a.last_attempt || ''))
    const newest = runs[0]
    const successful = runs.find(run => run.success === true)
    const lastSuccess = newest.last_success || newest.last_successful_refresh || successful?.finished_at || null
    const age = lastSuccess ? Date.now() - Date.parse(lastSuccess) : Infinity
    return {
      ...newest, source: name,
      last_attempt: newest.last_attempt || newest.finished_at || newest.started_at || null,
      last_success: lastSuccess,
      healthy: newest.healthy ?? (newest.success === undefined ? null : newest.success),
      is_stale: newest.is_stale ?? (!Number.isFinite(age) || age > (name === 'stm' ? 15 : 2880) * 60_000),
    }
  })
}
