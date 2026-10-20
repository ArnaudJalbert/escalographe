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
beforeEach(() => { window.history.pushState({}, '', '/'); try { localStorage.clear() } catch { /* storage disabled in Node */ } })
describe.each([
  { locale: 'fr', availability: 'Disponibilité actuelle', outage: /escaliers roulants pétés 1/i, stale: /1 observation peut être périmée/i, shown: '3 sur 3 escaliers roulants affichés', filter: 'Filtrer par état', search: /Chercher un escalier roulant/, empty: /Aucun escalier roulant répertorié/, noData: /Aucune observation disponible/, awaiting: 'En attente d’états de fonctionnement signalés', error: /Le résumé en direct est indisponible/ },
  { locale: 'en', availability: 'Availability now', outage: /escalators out of service 1/i, stale: /1 escalator observation may be stale/i, shown: '3 of 3 escalators shown', filter: 'Filter by status', search: /Search escalator/, empty: /No escalator records yet/, noData: /No escalator observations available yet/, awaiting: 'Awaiting reported operational statuses', error: /The live summary is unavailable/ },
])('dashboard $locale', ({ locale, availability, outage, stale, shown, filter, search, empty, noData, awaiting, error }) => {
  async function renderInLocale() {
    const user = userEvent.setup()
    render(<App />)
    if (locale === 'en') await user.click(screen.getByRole('button', { name: 'English' }))
    return user
  }
  it('renders availability, status counts and outage', async () => {
    mockApi(); await renderInLocale()
    expect(await screen.findByLabelText(`${availability}: 50.0%`)).toBeInTheDocument()
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: outage })).toBeInTheDocument()
    expect(screen.getByText(locale === 'fr' ? 'Pétés' : 'Out of service', { selector: '.count-label' })).toBeInTheDocument()
    if (locale === 'fr') expect(screen.getByRole('heading', { name: /Ça roule ou c’est pété\?/i })).toBeInTheDocument()
    expect(screen.getByText(/Orange line platform · mezzanine → platform/)).toBeInTheDocument()
    expect(document.documentElement.lang).toBe(locale)
  })
  it('warns on stale status without changing it to an outage', async () => {
    mockApi(); await renderInLocale()
    expect(await screen.findByText(stale)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: outage })).toBeInTheDocument()
  })
  it('filters by search and status, including unknown', async () => {
    mockApi(); const user = await renderInLocale()
    await screen.findByText(shown)
    await user.selectOptions(screen.getByLabelText(filter), 'unknown')
    expect(screen.getByText(locale === 'fr' ? '1 sur 3 escaliers roulants affichés' : '1 of 3 escalators shown')).toBeInTheDocument()
    expect(within(screen.getByTestId('mock-map')).getByText('Map: 1 markers')).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText(search), 'not a place')
    expect(screen.getByText(locale === 'fr' ? /Aucun escalier roulant ne correspond/ : /No escalators match/)).toBeInTheDocument()
  })
  it('never presents an empty dataset as zero availability or a confirmed all-clear', async () => {
    mockApi({ '/api/v1/stats/summary': { ...summary, total: 0, operational: 0, out_of_service: 0, unknown: 0, availability: null, live_status_coverage: 0 }, '/api/v1/escalators': { items: [], total: 0, limit: 100, offset: 0 } }); await renderInLocale()
    expect(await screen.findByText(empty)).toBeInTheDocument()
    expect(screen.getByLabelText(`${availability}: —`)).toBeInTheDocument()
    expect(screen.getByText(noData)).toBeInTheDocument()
  })
  it('does not show 0% when every observed status is unknown', async () => {
    mockApi({ '/api/v1/stats/summary': { ...summary, total: 1, operational: 0, out_of_service: 0, unknown: 1, availability: 0, live_status_coverage: 0 } }); await renderInLocale()
    expect(await screen.findByLabelText(`${availability}: —`)).toBeInTheDocument()
    expect(screen.getByText(awaiting)).toBeInTheDocument()
  })
  it('shows a clear API failure instead of made-up data', async () => {
    mockApi({ '/api/v1/stats/summary': 'error', '/api/v1/escalators': 'error' }); await renderInLocale()
    expect(await screen.findByText(error, {}, { timeout: 7000 })).toBeInTheDocument()
    expect(await screen.findByText(locale === 'fr' ? /Impossible de charger la liste/ : /The escalator list could not be loaded/)).toBeInTheDocument()
  }, 10000)
})
