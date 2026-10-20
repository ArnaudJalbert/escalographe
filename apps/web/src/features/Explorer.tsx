import { useLanguage } from '../i18n'
import { useMemo, useState } from 'react'
import { ArrowRight, ListFilter, Search, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Escalator } from '../types'
import { relativeTime, statusOf, directionLabel } from '../components/format'
import { AtlasMap } from '../components/AtlasMap'
import { StatusBadge } from '../components/Status'

type Filters = { search: string; status: string; source: string; station: string; direction: string; montrealOnly: boolean }
export function Explorer({ escalators, loading, error, total }: { escalators: Escalator[]; loading: boolean; error: boolean; total: number }) {
  const { t, locale } = useLanguage()
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
    <div className="section-header"><div><div className="eyebrow">{t('02 / EXPLORE THE NETWORK')}</div><h2 id="explore-heading">{t('Find an escalator.')}</h2><p>{t('Map view and accessible list, showing the same live observations.')}</p></div><div className="view-toggle" role="group" aria-label={t('View type')}><button aria-pressed={view === 'map'} onClick={() => setView('map')}>{t('Map')}</button><button aria-pressed={view === 'list'} onClick={() => setView('list')}>{t('List')}</button></div></div>
    <div className="explorer-panel"><div className="filters"><label className="search-box"><Search size={17} aria-hidden="true" /><span className="sr-only">{t('Search escalators')}</span><input value={filters.search} onChange={event => update('search', event.target.value)} placeholder={t('Search escalator or station…')} /></label><label><span className="sr-only">{t('Filter by status')}</span><select aria-label={t('Filter by status')} value={filters.status} onChange={event => update('status', event.target.value)}><option value="">{t('All statuses')}</option><option value="operational">{t('Operational')}</option><option value="out_of_service">{t('Out of service')}</option><option value="verification_needed">{t('Needs verification')}</option><option value="unknown">{t('Unknown')}</option></select></label><label><span className="sr-only">{t('Filter by source')}</span><select aria-label={t('Filter by source')} value={filters.source} onChange={event => update('source', event.target.value)}><option value="">{t('All sources')}</option>{sources.map(source => <option key={source} value={source}>{source.toUpperCase()}</option>)}</select></label><label><span className="sr-only">{t('Filter by station')}</span><select aria-label={t('Filter by station')} value={filters.station} onChange={event => update('station', event.target.value)}><option value="">{t('All stations')}</option>{stations.map(station => <option key={station} value={station}>{station}</option>)}</select></label><label><span className="sr-only">{t('Filter by direction')}</span><select aria-label={t('Filter by direction')} value={filters.direction} onChange={event => update('direction', event.target.value)}><option value="">{t('Any direction')}</option><option value="up">{t('Up')}</option><option value="down">{t('Down')}</option><option value="reversible">{t('Reversible')}</option></select></label><label className="checkbox-filter"><input type="checkbox" checked={filters.montrealOnly} onChange={event => update('montrealOnly', event.target.checked)} /><span>{t('Montréal only')}</span></label></div>
    <div className="results-bar"><span><SlidersHorizontal size={15} /> {loading ? t('Loading the network…') : `${filtered.length} ${t('of')} ${total} ${t('escalators shown')}`}</span><span><ListFilter size={15} /> {t('Filtered to current selection')}</span></div>
    {view === 'map' && <AtlasMap escalators={filtered} />}
    <div className="list-heading"><h3>{view === 'map' ? t('At a glance') : t('All escalators')}</h3><span>{t('STATUS / LOCATION / OBSERVATION')}</span></div>
    {error && <div className="empty-card" role="alert">{t('The escalator list could not be loaded. Try again in a moment.')}</div>}
    {!error && !loading && escalators.length === 0 && <div className="empty-card">{t('No escalator records yet. Initial data collection may still be running.')}</div>}
    {!error && !loading && escalators.length > 0 && filtered.length === 0 && <div className="empty-card">{t('No escalators match these filters. Try another station or status.')}</div>}
    {loading && <div className="empty-card">{t('Loading current escalator observations…')}</div>}
    <div className="escalator-list">{filtered.slice(0, view === 'map' ? 8 : undefined).map(item => <Link className="escalator-row" key={item.id} to={`/escalators/${encodeURIComponent(item.id)}`}><span className={`row-status-dot dot-${statusOf(item.status?.value)}`} aria-hidden="true" /><span className="row-main"><strong>{item.name}</strong><small>{item.station?.name || item.building_name || t('Location not specified')} · {directionLabel(item.direction, locale)}</small></span><span className="row-status"><StatusBadge value={item.status?.value} stale={item.status?.is_stale} /></span><span className="row-updated">{relativeTime(item.status?.observed_at, locale)}</span><ArrowRight className="row-arrow" size={17} aria-hidden="true" /></Link>)}</div>
    {view === 'map' && filtered.length > 8 && <button className="more-button" onClick={() => setView('list')}>{t('View all')} {filtered.length} {t('escalators')} <ArrowRight size={16} /></button>}
    {total > escalators.length && <p className="pagination-note">{t('Showing the first')} {escalators.length} {t('records. Refine the list using the filters above.')}</p>}
    </div>
  </section>
}
