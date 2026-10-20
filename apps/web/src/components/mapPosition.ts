import type { Escalator } from '../types'

export type MapPosition = { latitude: number; longitude: number; approximate: boolean }
export type Mapped = { item: Escalator; position: MapPosition }

export function mapPosition(item: Escalator): MapPosition | null {
  if (Number.isFinite(item.location?.latitude) && Number.isFinite(item.location?.longitude)) {
    return { latitude: item.location.latitude!, longitude: item.location.longitude!, approximate: false }
  }
  if (Number.isFinite(item.station?.latitude) && Number.isFinite(item.station?.longitude)) {
    return { latitude: item.station!.latitude!, longitude: item.station!.longitude!, approximate: true }
  }
  return null
}

export function groupMapMarkers(located: Mapped[]): Mapped[][] {
  const groups = new Map<string, Mapped[]>()
  for (const entry of located) {
    const key = entry.position.approximate ? `station:${entry.item.station?.id}:${entry.position.latitude}:${entry.position.longitude}` : `device:${entry.item.id}`
    groups.set(key, [...(groups.get(key) || []), entry])
  }
  return [...groups.values()]
}
