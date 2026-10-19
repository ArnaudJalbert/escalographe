import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App'
import { escalators, summary } from './fixtures/network'

function mockApi(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const path = new URL(input, 'http://localhost').pathname
    if (path in overrides) {
      if (overrides[path] === 'error') return { ok: false, status: 503 }
      return { ok: true, json: async () => overrides[path] }
    }
    let data: unknown = []
    if (path === '/api/v1/stats/summary') data = summary
    else if (path === '/api/v1/escalators') data = { items: escalators, total: 3, limit: 100, offset: 0 }
    else if (path === '/api/v1/sources') data = [{ source: 'stm', healthy: true }]
    else if (path === '/api/v1/stats/availability') data = { items: [] }
    else if (path === '/api/v1/stats/stations') data = { items: [] }
    return { ok: true, json: async () => data }
  }))
}
beforeEach(() => { window.history.pushState({}, '', '/') })
describe('dashboard', () => {
  it('renders availability, four status counts and a prominent outage', async () => {
    mockApi(); render(<App />)
    expect(await screen.findByLabelText('Availability now: 50.0%')).toBeInTheDocument()
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /out of service 1/i })).toBeInTheDocument()
    expect(screen.getByText(/Orange line platform · mezzanine → platform/)).toBeInTheDocument()
  })
  it('warns on stale status without changing it to an outage', async () => {
    mockApi(); render(<App />)
    expect(await screen.findByText(/1 escalator observations may be stale/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /out of service 1/i })).toBeInTheDocument()
  })
  it('filters by search and status, including unknown', async () => {
    mockApi(); render(<App />)
    await screen.findByText('3 of 3 escalators shown')
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Filter by status'), 'unknown')
    expect(screen.getByText('1 of 3 escalators shown')).toBeInTheDocument()
    expect(within(screen.getByTestId('mock-map')).getByText('Map: 1 markers')).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText(/Search escalator or station/), 'not a place')
    expect(screen.getByText(/No escalators match these filters/)).toBeInTheDocument()
  })
  it('never presents an empty dataset as zero availability or a confirmed all-clear', async () => {
    mockApi({ '/api/v1/stats/summary': { ...summary, total: 0, operational: 0, out_of_service: 0, unknown: 0, availability: null, live_status_coverage: 0 }, '/api/v1/escalators': { items: [], total: 0, limit: 100, offset: 0 } }); render(<App />)
    expect(await screen.findByText(/No escalator records yet/)).toBeInTheDocument()
    expect(screen.getByLabelText('Availability now: —')).toBeInTheDocument()
    expect(screen.getByText(/No escalator observations available yet/)).toBeInTheDocument()
  })
  it('does not show 0% when every observed status is unknown', async () => {
    mockApi({ '/api/v1/stats/summary': { ...summary, total: 1, operational: 0, out_of_service: 0, unknown: 1, availability: 0, live_status_coverage: 0 } }); render(<App />)
    expect(await screen.findByLabelText('Availability now: —')).toBeInTheDocument()
    expect(screen.getByText('Awaiting reported operational statuses')).toBeInTheDocument()
  })
  it('shows a clear API failure instead of made-up data', async () => {
    mockApi({ '/api/v1/stats/summary': 'error', '/api/v1/escalators': 'error' }); render(<App />)
    expect(await screen.findByText(/The live summary is unavailable/, {}, { timeout: 5000 })).toBeInTheDocument()
    expect(await screen.findByText(/The escalator list could not be loaded/, {}, { timeout: 5000 })).toBeInTheDocument()
  })
})
