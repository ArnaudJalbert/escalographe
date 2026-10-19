import type { AvailabilityHistory, AvailabilityPoint, Escalator, HistoryRecord, Page, SourceHealth, Station, StationOutages, Summary } from '../types'

export class ApiError extends Error { constructor(public status: number, message: string) { super(message) } }
const base = import.meta.env.VITE_API_BASE_URL ?? ''
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${base}/api/v1${path}`, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new ApiError(response.status, response.status === 404 ? 'Not found' : `The data service returned ${response.status}`)
  return response.json() as Promise<T>
}
function query(params: Record<string, string | number | boolean | null | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  return search.size ? `?${search}` : ''
}
export const api = {
  escalators: (params: Record<string, string | number | boolean | null | undefined> = {}) => get<Page<Escalator>>(`/escalators${query(params)}`),
  escalator: (id: string) => get<Escalator>(`/escalators/${encodeURIComponent(id)}`),
  history: (id: string) => get<Page<HistoryRecord> | HistoryRecord[]>(`/escalators/${encodeURIComponent(id)}/history`),
  stations: () => get<Page<Station> | Station[]>('/stations?limit=500'),
  station: (id: string) => get<Station>(`/stations/${encodeURIComponent(id)}`),
  summary: () => get<Summary>('/stats/summary'),
  outages: () => get<Escalator[]>('/stats/outages'),
  availability: (range: string) => get<AvailabilityPoint[] | AvailabilityHistory>(`/stats/availability${query({ range })}`),
  stationStats: () => get<StationOutages[] | { items?: StationOutages[]; stations?: StationOutages[] }>('/stats/stations'),
  sources: () => get<SourceHealth[] | { items: SourceHealth[] }>('/sources'),
}
export function asItems<T>(value: Page<T> | T[] | { items?: T[]; points?: T[]; stations?: T[] } | undefined): T[] {
  if (!value) return []
  return Array.isArray(value) ? value : value.items ?? ('points' in value ? value.points : undefined) ?? ('stations' in value ? value.stations : undefined) ?? []
}
