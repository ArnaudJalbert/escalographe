import type { Escalator, Summary } from '../../src/types'

export const escalators: Escalator[] = [
  { id: 'esc-1', name: 'Main entrance to mezzanine', station: { id: 'station-1', name: 'Berri-UQAM' }, location: { latitude: 45.515, longitude: -73.56, from_level: 'entrance', to_level: 'mezzanine' }, direction: 'up', status: { value: 'operational', source: 'stm', observed_at: '2026-10-19T15:00:00Z', is_stale: false }, sources: [{ source: 'stm', external_id: 'A1' }], within_montreal: true },
  { id: 'esc-2', name: 'Orange line platform', station: { id: 'station-1', name: 'Berri-UQAM', latitude: 45.515, longitude: -73.56 }, location: { latitude: null, longitude: null, from_level: 'mezzanine', to_level: 'platform' }, direction: 'down', status: { value: 'out_of_service', source: 'stm', observed_at: '2026-10-19T14:00:00Z', is_stale: true }, sources: [{ source: 'stm', external_id: 'A2' }], within_montreal: true },
  { id: 'esc-3', name: 'Street passage', station: null, building_name: 'Place des Arts', location: { latitude: 45.508, longitude: -73.565, from_level: null, to_level: null }, direction: null, status: { value: 'unknown', source: null, observed_at: null, is_stale: false }, sources: [{ source: 'osm', external_id: 'way/3' }], within_montreal: true },
]
export const summary: Summary = { total: 3, operational: 1, out_of_service: 1, verification_needed: 0, unknown: 1, availability: 50, live_status_coverage: 2, last_successful_stm_refresh: '2026-10-19T15:00:00Z' }
