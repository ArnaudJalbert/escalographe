import { AlertTriangle, ArrowUpRight, Clock3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatTime, percent, relativeTime, statusInfo, statusOf } from './format'
import type { Escalator, Status, Summary } from '../types'

export function StatusBadge({ value, stale = false }: { value: Status | string | undefined; stale?: boolean }) {
  const info = statusInfo[statusOf(value)]
  return <span className={`status-badge status-${statusOf(value)}`}><span className="badge-symbol" aria-hidden="true">{info.symbol}</span>{info.label}{stale && <span className="stale-tag">Stale</span>}</span>
}
export function DataNotice({ message, kind = 'info' }: { message: string; kind?: 'info' | 'warn' | 'error' }) {
  return <div className={`data-notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}><AlertTriangle size={17} aria-hidden="true" />{message}</div>
}
export function SummaryPanel({ summary, loading, error }: { summary?: Summary; loading: boolean; error: boolean }) {
  const values = [
    { label: 'Operational', value: summary?.operational, status: 'operational' },
    { label: 'Out of service', value: summary?.out_of_service, status: 'out_of_service' },
    { label: 'Needs verification', value: summary?.verification_needed, status: 'verification_needed' },
    { label: 'Unknown', value: summary?.unknown, status: 'unknown' },
  ] as const
  const known = summary ? summary.operational + summary.out_of_service + summary.verification_needed : 0
  const availability = known > 0 ? summary?.availability : null
  const coverage = summary?.live_status_coverage
  const coverageText = typeof coverage === 'number' ? `${coverage.toLocaleString()} / ${summary?.total ?? 0}` : coverage && typeof coverage === 'object' ? `${coverage.count ?? 0} / ${coverage.total ?? summary?.total ?? 0}` : summary ? `${summary.operational + summary.out_of_service + summary.verification_needed} / ${summary.total}` : '—'
  return <section className="summary-section" aria-labelledby="summary-heading"><div className="page-wrap">
    <div className="section-top"><div><div className="eyebrow"><span className="live-pip" /> LIVE NETWORK PICTURE</div><h1 id="summary-heading">What’s working, <em>right now?</em></h1><p>Current escalator status across Montréal, at a glance.</p></div><div className="refresh-note"><Clock3 size={16} aria-hidden="true" /><span>STM last checked<br /><strong>{summary?.last_successful_stm_refresh ? relativeTime(summary.last_successful_stm_refresh) : 'Awaiting first update'}</strong></span></div></div>
    {summary?.last_successful_stm_refresh && Date.now() - new Date(summary.last_successful_stm_refresh).getTime() > 15 * 60_000 && <DataNotice kind="warn" message={`Status data may be stale. Last successful STM refresh: ${formatTime(summary.last_successful_stm_refresh)}.`} />}
    {error && <DataNotice kind="error" message="The live summary is unavailable. Try refreshing the page; no status has been assumed." />}
    <div className="summary-grid"><div className="availability-card"><div className="card-kicker">01 / AVAILABILITY NOW</div><div className="availability-value" aria-label={`Availability now: ${summary ? percent(availability) : 'unavailable'}`}>{loading ? <span className="skeleton sk-wide" /> : summary ? percent(availability) : '—'}</div><div className="availability-caption">{known ? 'of escalators with known status are operational' : 'Awaiting reported operational statuses'}</div><div className="availability-rule"><span style={{ width: availability == null ? '0%' : `${Math.min(100, availability <= 1 && availability > 0 ? availability * 100 : availability)}%` }} /></div><div className="coverage-line">LIVE STATUS COVERAGE <strong>{coverageText}</strong></div></div>
    <div className="counts-grid">{values.map(({ label, value, status }, index) => <div className={`count-card count-${status}`} key={status}><div className="count-top"><span className="count-icon" aria-hidden="true">{statusInfo[status].symbol}</span><span className="count-index">0{index + 2}</span></div><div className="count-number">{loading ? <span className="skeleton sk-num" /> : value ?? '—'}</div><div className="count-label">{label}</div></div>)}</div></div>
    <div className="summary-bottom"><span>Known status excludes mapped escalators without live observations.</span><Link to="/about">How are these numbers calculated? <ArrowUpRight size={13} /></Link></div>
  </div></section>
}
export function EscalatorMeta({ escalator }: { escalator: Escalator }) {
  return <div className="detail-meta"><span>{escalator.station ? <Link className="text-link" to={`/stations/${encodeURIComponent(escalator.station.id)}`}>{escalator.station.name}</Link> : escalator.building_name ?? 'Location not specified'}</span><span>{[escalator.location.from_level, escalator.location.to_level].filter(Boolean).join(' → ') || 'Levels not reported'}</span><span>{escalator.direction || 'Direction unknown'}</span></div>
}
