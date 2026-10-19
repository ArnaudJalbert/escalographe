export type Status = 'operational' | 'out_of_service' | 'verification_needed' | 'unknown'
export type SourceRecord = { source?: string; source_url?: string | null; external_id?: string | null; url?: string | null }
export type Escalator = {
  id: string; name: string; station: { id: string; name: string; latitude?: number | null; longitude?: number | null } | null
  building_name?: string | null; location_description?: string | null; out_since?: string | null; municipality?: string | null; within_montreal?: boolean | null
  location: { latitude: number | null; longitude: number | null; from_level: string | null; to_level: string | null; description?: string | null }
  direction: string | null
  status: { value: Status; source: string | null; observed_at: string | null; is_stale: boolean }
  sources: SourceRecord[]
}
export type Page<T> = { items: T[]; total: number; limit: number; offset: number }
export type Summary = { total: number; operational: number; out_of_service: number; verification_needed: number; unknown: number; availability: number | null; live_status_coverage: number | { count?: number; total?: number; percentage?: number } | null; last_successful_stm_refresh: string | null }
export type SourceHealth = { source?: string; name?: string; success?: boolean; started_at?: string | null; finished_at?: string | null; last_success?: string | null; last_successful_refresh?: string | null; last_attempt?: string | null; healthy?: boolean | null; is_stale?: boolean; status?: string | null; error_message?: string | null }
export type HistoryRecord = { id?: string; status?: Status | { value: Status }; observed_at?: string; ended_at?: string | null; source?: string }
export type Station = { id: string; name: string; escalators?: Escalator[]; escalator_count?: number; operational?: number; out_of_service?: number; availability?: number | null }
export type AvailabilityPoint = { date?: string; timestamp?: string; observed_at?: string; period?: string; availability?: number | null; operational?: number; total?: number }
export type AvailabilityHistory = { points?: AvailabilityPoint[]; items?: AvailabilityPoint[]; collection_started_at?: string | null }
export type StationOutages = { station_id?: string; station?: string; name?: string; outages?: number; out_of_service?: number; count?: number }
