import { describe, expect, it } from 'vitest'
import { groupMapMarkers, mapPosition } from '../src/components/mapPosition'
import { escalators } from './fixtures/network'

describe('map position provenance', () => {
  it('prefers precise device coordinates', () => {
    expect(mapPosition({ ...escalators[0], station: { id: 's', name: 'Station', latitude: 45.9, longitude: -73.9 } })).toEqual({ latitude: 45.515, longitude: -73.56, approximate: false })
  })
  it('uses an explicitly approximate station location when the device has no coordinates', () => {
    expect(mapPosition(escalators[1])).toEqual({ latitude: 45.515, longitude: -73.56, approximate: true })
  })
  it('groups station-centroid markers but keeps precise devices separate', () => {
    const another = { ...escalators[1], id: 'esc-4' }
    const entries = [escalators[0], escalators[1], another].map(item => ({ item, position: mapPosition(item)! }))
    expect(groupMapMarkers(entries).map(group => group.map(({ item }) => item.id))).toEqual([['esc-1'], ['esc-2', 'esc-4']])
  })
  it('never invents a position without either coordinate pair', () => {
    expect(mapPosition({ ...escalators[1], station: null })).toBeNull()
  })
})
