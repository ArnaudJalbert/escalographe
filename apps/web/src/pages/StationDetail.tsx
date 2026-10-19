import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { percent } from '../components/format'
import { StatusBadge } from '../components/Status'
import type { Escalator } from '../types'

export function StationDetail() {
  const { id } = useParams()
  const station = useQuery({ queryKey: ['station', id], queryFn: () => api.station(id!), enabled: !!id })
  const escalators = useQuery({ queryKey: ['station-escalators', id], queryFn: () => api.escalators({ station: id!, limit: 500 }), enabled: !!id })
  if (station.isLoading) return <div className="page-wrap detail-loading">Loading station…</div>
  if (station.isError || !station.data) return <div className="page-wrap detail-loading" role="alert">This station could not be found. <Link className="text-link" to="/">Back to the atlas</Link></div>
  const items: Escalator[] = station.data.escalators?.length ? station.data.escalators : escalators.data?.items || []
  const operational = items.filter(item => item.status?.value === 'operational').length
  const out = items.filter(item => item.status?.value === 'out_of_service').length
  const known = items.filter(item => item.status?.value && item.status.value !== 'unknown').length
  return <div className="page-wrap detail-page"><Link className="back-link" to="/"><ArrowLeft size={16} /> Back to the atlas</Link><div className="detail-head"><div><div className="eyebrow">STATION / MONTRÉAL</div><h1>{station.data.name}</h1><p>Current observations for escalators at this station.</p></div></div><div className="station-metrics"><div><span>KNOWN ESCALATORS</span><strong>{station.data.escalator_count ?? items.length}</strong></div><div><span>OPERATIONAL</span><strong>{operational}</strong></div><div><span>OUT OF SERVICE</span><strong>{out}</strong></div><div><span>AVAILABILITY</span><strong>{known ? percent(100 * operational / known) : '—'}</strong></div></div><h2 className="station-subtitle">Escalators at {station.data.name}</h2>{escalators.isLoading && !station.data.escalators && <p>Loading escalators…</p>}{escalators.isError && !station.data.escalators && <p role="alert">Escalator list is temporarily unavailable.</p>}{!items.length && !escalators.isLoading && <div className="empty-card">No escalators are listed at this station yet.</div>}<div className="escalator-list">{items.map(item => <Link key={item.id} to={`/escalators/${encodeURIComponent(item.id)}`} className="escalator-row"><span className="row-main"><strong>{item.name}</strong><small>{item.direction || 'Direction unknown'}</small></span><StatusBadge value={item.status?.value} stale={item.status?.is_stale} /></Link>)}</div></div>
}
