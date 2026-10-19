import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, RadioTower } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, asItems } from '../api/client'
import { formatTime, relativeTime, statusOf } from '../components/format'
import { sourceHealth } from '../components/sourceHealth'
import { DataNotice, StatusBadge, SummaryPanel } from '../components/Status'
import { Explorer } from '../features/Explorer'
import { Statistics } from '../features/Statistics'
import type { Escalator, Page } from '../types'

async function loadEscalators(): Promise<Page<Escalator>> {
  const first = await api.escalators({ limit: 100, offset: 0 })
  const items = [...first.items]
  // Continue pagination, but keep an upper bound to avoid unbounded requests on public clients.
  for (let offset = items.length; offset < first.total && offset < 3000; offset += 100) {
    const page = await api.escalators({ limit: 100, offset })
    if (!page.items.length) break
    items.push(...page.items)
  }
  return { ...first, items }
}
export function Dashboard() {
  const summary = useQuery({ queryKey: ['summary'], queryFn: api.summary })
  const escalators = useQuery({ queryKey: ['escalators'], queryFn: loadEscalators })
  const sources = useQuery({ queryKey: ['sources'], queryFn: api.sources, retry: false })
  const outageDetails = useQuery({ queryKey: ['outages'], queryFn: api.outages, retry: false })
  const outages = (escalators.data?.items || []).filter(item => statusOf(item.status?.value) === 'out_of_service').map(item => outageDetails.data?.find(detail => detail.id === item.id) || item).sort((a, b) => (a.out_since || 'z').localeCompare(b.out_since || 'z') || (a.station?.name || a.name).localeCompare(b.station?.name || b.name))
  const sourceRows = sourceHealth(asItems(sources.data))
  const staleCount = (escalators.data?.items || []).filter(item => item.status?.observed_at && item.status.is_stale).length
  return <>
    <SummaryPanel summary={summary.data} loading={summary.isLoading} error={summary.isError} />
    <div className="page-wrap"><div className="ticker-line"><div><RadioTower size={17} aria-hidden="true" /><strong>THE NETWORK, NOT THE GUESSWORK.</strong><span>Statuses are observations from public sources.</span></div><a href="#explore">Explore the map <ArrowRight size={15} /></a></div>
      {staleCount > 0 && <div className="mt-4"><DataNotice kind="warn" message={`${staleCount} escalator observations may be stale. Their last known statuses are still shown, not treated as outages.`} /></div>}
      {sources.isError && <div className="mt-4"><DataNotice kind="warn" message="Source health is temporarily unavailable. Individual observations remain visible with timestamps." /></div>}
    </div>
    <section className="outage-section page-wrap" aria-labelledby="outages-heading"><div className="section-header"><div><div className="eyebrow">01.5 / CURRENT INTERRUPTIONS</div><h2 id="outages-heading">Out of service <span className="outage-count">{outages.length}</span></h2><p>Known outages only. An unknown or stale status is not automatically an outage.</p></div><a href="#explore" className="section-link">Browse all <ArrowUpRight size={16} /></a></div>
      {escalators.isLoading ? <div className="empty-card">Checking for current interruptions…</div> : escalators.isError ? <div className="empty-card" role="alert">Current outages could not be loaded. No outage status is being assumed.</div> : outages.length === 0 ? <div className="quiet-state"><span className="quiet-icon">✓</span><div><strong>{escalators.data?.total ? 'No reported outages in the available data.' : 'No escalator observations available yet.'}</strong><small>{escalators.data?.total ? 'This does not confirm every escalator is working. Check coverage and freshness above.' : 'Initial data collection may still be running. No all-clear is implied.'}</small></div></div> : <div className="outage-list">{outages.slice(0, 6).map(item => <Link key={item.id} to={`/escalators/${encodeURIComponent(item.id)}`} className="outage-row"><span className="outage-bar" /><div><strong>{item.station?.name || item.building_name || item.name}</strong><small>{item.name} · {item.location_description || item.location?.description || [item.location?.from_level, item.location?.to_level].filter(Boolean).join(' → ') || 'Location not specified'}</small></div><StatusBadge value={item.status?.value} stale={item.status?.is_stale} /><span className="outage-updated">{item.out_since && <>Out since {formatTime(item.out_since)}<small>Last checked {relativeTime(item.status?.observed_at)}</small></>}{!item.out_since && <>Last checked {relativeTime(item.status?.observed_at)}<small>Start time not known</small></>}</span><ArrowRight size={17} aria-hidden="true" /></Link>)}</div>}
      {outages.length > 6 && <a className="more-button" href="#explore">See all {outages.length} outages <ArrowRight size={16} /></a>}
    </section>
    <Explorer escalators={escalators.data?.items || []} total={escalators.data?.total || 0} loading={escalators.isLoading} error={escalators.isError} />
    <Statistics summary={summary.data} />
    <section className="source-section"><div className="page-wrap source-inner"><div><div className="eyebrow">05 / SOURCE HEALTH</div><h2>Where this data comes from.</h2><p>Source failures are separate from escalator outages. We retain the last known observation when a refresh fails.</p><Link to="/about">Read the methodology <ArrowUpRight size={15} /></Link></div><div className="source-cards">{sourceRows.length ? sourceRows.map((source, index) => <div className="source-card" key={source.source || source.name || index}><div className="source-title"><strong>{(source.source || source.name || 'Data source').toUpperCase()}</strong><span className={source.healthy === false || source.is_stale || source.status === 'failing' ? 'health-delayed' : 'health-ok'}>{source.healthy === false || source.status === 'failing' ? 'Needs attention' : source.is_stale ? 'Delayed' : source.healthy === true ? 'Reporting' : source.status || 'Status not reported'}</span></div><p>Last successful refresh <strong>{source.last_success || source.last_successful_refresh ? formatTime(source.last_success || source.last_successful_refresh) : 'Not yet reported'}</strong></p>{source.last_attempt && <small>Last attempt {formatTime(source.last_attempt)}</small>}</div>) : <div className="source-card">Source health information is not available yet. Check individual observation timestamps above.</div>}</div></div></section>
  </>
}
