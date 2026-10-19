import { useLanguage } from '../i18n'
import { useQuery } from '@tanstack/react-query'
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from 'react-leaflet'
import { Link } from 'react-router-dom'
import type { Escalator } from '../types'
import { api } from '../api/client'
import { formatTime, statusInfo, statusOf } from './format'
import { groupMapMarkers, mapPosition } from './mapPosition'
import { StatusBadge } from './Status'

const attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
function markerStyle(item: Escalator, approximate: boolean) {
  return { color: approximate ? '#203d33' : '#ffffff', weight: 2, dashArray: approximate ? '3 3' : undefined, fillColor: statusInfo[statusOf(item.status?.value)].color, fillOpacity: approximate ? .62 : 1 }
}
export function AtlasMap({ escalators, height = 470 }: { escalators: Escalator[]; height?: number }) {
  const { t, locale } = useLanguage()
  const located = escalators.flatMap(item => { const position = mapPosition(item); return position ? [{ item, position }] : [] })
  const markers = groupMapMarkers(located)
  const approximate = located.filter(({ position }) => position.approximate).length
  return <div className="map-frame" style={{ height }}><MapContainer center={[45.5088, -73.5878]} zoom={11} scrollWheelZoom={false} className="atlas-map" aria-label={t('Map of Montréal escalators')}>
    <TileLayer attribution={attribution} url={tileUrl} />
    {markers.map(group => {
      const { item, position } = group[0]
      return <CircleMarker key={position.approximate ? `station:${item.station?.id}` : item.id} center={[position.latitude, position.longitude]} radius={position.approximate ? group.length > 1 ? 15 : 10 : 8} pathOptions={group.length > 1 ? { color: '#203d33', weight: 2, dashArray: '3 3', fillColor: '#304b3a', fillOpacity: .85 } : markerStyle(item, position.approximate)}>
        {group.length > 1 && <Tooltip permanent direction="center" className="station-marker-count">{group.length}</Tooltip>}
        <Popup><div className="map-popup">{position.approximate && <span className="approximate-note">{t('Station location; device position unknown.')}</span>}{group.length > 1 && <strong>{item.station?.name} · {group.length} {t('escalators')}</strong>}{group.map(({ item: escalator }) => <div className="map-popup-item" key={escalator.id}><strong>{escalator.name}</strong>{group.length === 1 && <span>{escalator.station?.name || escalator.building_name || 'Montréal'}</span>}<StatusBadge value={escalator.status?.value} stale={escalator.status?.is_stale} /><small>{t('Observed:')} {formatTime(escalator.status?.observed_at, locale)}</small><Link to={`/escalators/${encodeURIComponent(escalator.id)}`}>{t('View escalator →')}</Link></div>)}</div></Popup>
      </CircleMarker>
    })}
  </MapContainer>{located.length === 0 && <div className="map-overlay">{t('No coordinates available for the current selection. Browse the list below instead.')}</div>}<div className="map-count">{located.length} {t('mapped /')} {escalators.length} {t('shown')}{approximate > 0 && ` · ${approximate} ${t('at approximate station locations')}`}</div></div>
}
export function DetailMap({ escalator }: { escalator: Escalator }) {
  const { t } = useLanguage()
  const position = mapPosition(escalator)
  if (!position) return <div className="empty-card">{t('Location coordinates have not been reported.')}</div>
  return <div className="map-frame" style={{ height: 320 }}><MapContainer center={[position.latitude, position.longitude]} zoom={position.approximate ? 14 : 15} scrollWheelZoom={false} className="atlas-map" aria-label={`${position.approximate ? t('Approximate station location') : t('Map')} ${t('of')} ${escalator.name}`}><TileLayer attribution={attribution} url={tileUrl} /><CircleMarker center={[position.latitude, position.longitude]} radius={10} pathOptions={markerStyle(escalator, position.approximate)} /></MapContainer>{position.approximate && <div className="map-overlay">{t('Station location; device position unknown.')}</div>}</div>
}
export function useEscalatorDetail(id: string | undefined) { return useQuery({ queryKey: ['escalator', id], queryFn: () => api.escalator(id!), enabled: !!id }) }
