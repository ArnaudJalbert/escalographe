import { useMemo, useState } from 'react'
import { ArrowRight, ListFilter, Search, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Escalator } from '../types'
import { relativeTime, statusOf } from '../components/format'
import { AtlasMap } from '../components/AtlasMap'
import { StatusBadge } from '../components/Status'

type Filters = { search: string; status: string; source: string; station: string; direction: string; montrealOnly: boolean }
export function Explorer({ escalators, loading, error, total }: { escalators: Escalator[]; loading: boolean; error: boolean; total: number }) {
  const [filters, setFilters] = useState<Filters>({ search: '', status: '', source: '', station: '', direction: '', montrealOnly: true })
  const [view, setView] = useState<'map' | 'list'>('map')
  const stations = useMemo(() => [...new Set(escalators.map(item => item.station?.name).filter((name): name is string => !!name))].sort((a, b) => a.localeCompare(b)), [escalators])
  const sources = useMemo(() => [...new Set(escalators.flatMap(item => item.sources?.map(source => source.source).filter((name): name is string => !!name) ?? []))].sort(), [escalators])
  const filtered = useMemo(() => escalators.filter(item => {
    const term = filters.search.trim().toLocaleLowerCase()
    return (!term || `${item.name} ${item.station?.name || ''} ${item.building_name || ''} ${item.location_description || item.location?.description || ''}`.toLocaleLowerCase().includes(term))
      && (!filters.status || statusOf(item.status?.value) === filters.status)
      && (!filters.source || item.sources?.some(source => source.source === filters.source) || item.status?.source === filters.source)
      && (!filters.station || item.station?.name === filters.station)
      && (!filters.direction || item.direction === filters.direction)
      && (!filters.montrealOnly || item.within_montreal !== false)
  }), [escalators, filters])
  const update = (key: keyof Filters, value: string | boolean) => setFilters(previous => ({ ...previous, [key]: value }))
  return <section className="explorer-section page-wrap" id="explore" aria-labelledby="explore-heading">
    <div className="section-header"><div><div className="eyebrow">02 / EXPLORE THE NETWORK</div><h2 id="explore-heading">Find an escalator.</h2><p>Map view and accessible list, showing the same live observations.</p></div><div className="view-toggle" role="group" aria-label="View type"><button aria-pressed={view === 'map'} onClick={() => setView('map')}>Map</button><button aria-pressed={view === 'list'} onClick={() => setView('list')}>List</button></div></div>
    <div className="explorer-panel"><div className="filters"><label className="search-box"><Search size={17} aria-hidden="true" /><span className="sr-only">Search escalators</span><input value={filters.search} onChange={event => update('search', event.target.value)} placeholder="Search escalator or station…" /></label><label><span className="sr-only">Filter by status</span><select aria-label="Filter by status" value={filters.status} onChange={event => update('status', event.target.value)}><option value="">All statuses</option><option value="operational">Operational</option><option value="out_of_service">Out of service</option><option value="verification_needed">Needs verification</option><option value="unknown">Unknown</option></select></label><label><span className="sr-only">Filter by source</span><select aria-label="Filter by source" value={filters.source} onChange={event => update('source', event.target.value)}><option value="">All sources</option>{sources.map(source => <option key={source} value={source}>{source.toUpperCase()}</option>)}</select></label><label><span className="sr-only">Filter by station</span><select aria-label="Filter by station" value={filters.station} onChange={event => update('station', event.target.value)}><option value="">All stations</option>{stations.map(station => <option key={station} value={station}>{station}</option>)}</select></label><label><span className="sr-only">Filter by direction</span><select aria-label="Filter by direction" value={filters.direction} onChange={event => update('direction', event.target.value)}><option value="">Any direction</option><option value="up">Up</option><option value="down">Down</option><option value="reversible">Reversible</option></select></label><label className="checkbox-filter"><input type="checkbox" checked={filters.montrealOnly} onChange={event => update('montrealOnly', event.target.checked)} /><span>Montréal only</span></label></div>
    <div className="results-bar"><span><SlidersHorizontal size={15} /> {loading ? 'Loading the network…' : `${filtered.length} of ${total} escalators shown`}</span><span><ListFilter size={15} /> Filtered to current selection</span></div>
    {view === 'map' && <AtlasMap escalators={filtered} />}
    <div className="list-heading"><h3>{view === 'map' ? 'At a glance' : 'All escalators'}</h3><span>STATUS / LOCATION / OBSERVATION</span></div>
    {error && <div className="empty-card" role="alert">The escalator list could not be loaded. Try again in a moment.</div>}
    {!error && !loading && escalators.length === 0 && <div className="empty-card">No escalator records yet. Initial data collection may still be running.</div>}
    {!error && !loading && escalators.length > 0 && filtered.length === 0 && <div className="empty-card">No escalators match these filters. Try another station or status.</div>}
    {loading && <div className="empty-card">Loading current escalator observations…</div>}
    <div className="escalator-list">{filtered.slice(0, view === 'map' ? 8 : undefined).map(item => <Link className="escalator-row" key={item.id} to={`/escalators/${encodeURIComponent(item.id)}`}><span className={`row-status-dot dot-${statusOf(item.status?.value)}`} aria-hidden="true" /><span className="row-main"><strong>{item.name}</strong><small>{item.station?.name || item.building_name || 'Location not specified'} · {item.direction || 'Direction unknown'}</small></span><span className="row-status"><StatusBadge value={item.status?.value} stale={item.status?.is_stale} /></span><span className="row-updated">{relativeTime(item.status?.observed_at)}</span><ArrowRight className="row-arrow" size={17} aria-hidden="true" /></Link>)}</div>
    {view === 'map' && filtered.length > 8 && <button className="more-button" onClick={() => setView('list')}>View all {filtered.length} escalators <ArrowRight size={16} /></button>}
    {total > escalators.length && <p className="pagination-note">Showing the first {escalators.length} records. Refine the list using the filters above.</p>}
    </div>
  </section>
}
