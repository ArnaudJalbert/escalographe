import { expect, test } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { escalators, summary } from '../tests/fixtures/network'

async function mockNetwork(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    let body: unknown = []
    if (path === '/api/v1/stats/summary') body = summary
    else if (path === '/api/v1/escalators') body = { items: escalators, total: escalators.length, limit: 100, offset: 0 }
    else if (path === '/api/v1/sources') body = [{ source: 'stm', healthy: true, last_success: summary.last_successful_stm_refresh }]
    else if (path === '/api/v1/stats/stations') body = [{ name: 'Berri-UQAM', outages: 1 }]
    else if (path === '/api/v1/stats/outages') body = [{ ...escalators[1], out_since: '2026-10-19T14:00:00Z' }]
    else if (path === '/api/v1/stats/availability') body = { items: [] }
    else if (path === '/api/v1/escalators/esc-2') body = escalators[1]
    else if (path === '/api/v1/escalators/esc-2/history') body = { items: [{ status: 'out_of_service', observed_at: '2026-10-19T14:00:00Z', source: 'stm' }] }
    else if (path === '/api/v1/stations/station-1') body = { id: 'station-1', name: 'Berri-UQAM', escalators: escalators.slice(0, 2) }
    else return route.fulfill({ status: 404, body: '{}' })
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  // Tiles are decorative in this deterministic browser test; markers and controls are still real Leaflet.
  await page.route('https://*.tile.openstreetmap.org/**', route => route.fulfill({ status: 200, contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8eee8"/><path d="M-20 45L300 118 M-20 165L300 238 M30 -20L115 300 M184 -20L269 300" stroke="#fff" stroke-width="16" fill="none"/><path d="M-20 45L300 118 M-20 165L300 238 M30 -20L115 300 M184 -20L269 300" stroke="#d5ded3" stroke-width="2" fill="none"/></svg>' }))
}

test.beforeEach(async ({ page }) => { await mockNetwork(page) })
for (const locale of ['fr', 'en'] as const) test(`dashboard status, map, selection and filters (${locale})`, async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
  if (locale === 'en') await page.getByRole('button', { name: 'English' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', locale)
  await expect(page.getByRole('heading', { name: locale === 'fr' ? /Ça roule ou c’est pété/i : /what’s working/i })).toBeVisible()
  await expect(page.getByLabel(`${locale === 'fr' ? 'Disponibilité actuelle' : 'Availability now'}: 50.0%`)).toBeVisible()
  await expect(page.getByRole('heading', { name: locale === 'fr' ? /escaliers roulants pétés 1/i : /escalators out of service 1/i })).toBeVisible()
  await expect(page.locator('.leaflet-container')).toBeVisible()
  await expect(page.locator('.leaflet-interactive')).toHaveCount(3)
  await page.getByLabel(locale === 'fr' ? 'Filtrer par état' : 'Filter by status').selectOption('out_of_service')
  await expect(page.getByText(locale === 'fr' ? '1 sur 3 escaliers roulants affichés' : '1 of 3 escalators shown')).toBeVisible()
  await expect(page.locator('.leaflet-interactive')).toHaveCount(1)
  await page.locator('.leaflet-interactive').click()
  await expect(page.locator('.map-popup')).toBeVisible()
  await expect(page.locator('.map-popup').getByText(locale === 'fr' ? 'Emplacement de la station; position de l’appareil inconnue.' : 'Station location; device position unknown.')).toBeVisible()
  await page.locator('.map-popup').getByRole('link', { name: locale === 'fr' ? /Voir l’escalier/ : /view escalator/i }).click()
  await expect(page).toHaveURL(/\/escalators\/esc-2$/)
  await expect(page.getByRole('heading', { name: 'Orange line platform' })).toBeVisible()
  await expect(page.getByText(locale === 'fr' ? 'Emplacement de la station; position de l’appareil inconnue.' : 'Station location; device position unknown.')).toBeVisible()
  await expect(page.getByText(locale === 'fr' ? /Cette observation peut être périmée/ : /this observation may be stale/i)).toBeVisible()
  await expect(page.getByText(locale === 'fr' ? 'Pété' : 'Out of service').first()).toBeVisible()
  await page.getByRole('link', { name: 'Berri-UQAM' }).first().click()
  await expect(page).toHaveURL(/\/stations\/station-1$/)
  await expect(page.getByRole('heading', { name: 'Berri-UQAM', exact: true })).toBeVisible()
  await expect(page.getByText(locale === 'fr' ? 'ESCALIERS ROULANTS CONNUS' : 'KNOWN ESCALATORS')).toBeVisible()
  await page.getByRole('link', { name: locale === 'fr' ? 'Retour à l’atlas' : 'Back to the atlas' }).click()
  await page.getByRole('link', { name: locale === 'fr' ? 'Comment ça marche' : 'How it works' }).click()
  await expect(page.getByRole('heading', { name: locale === 'fr' ? /Des données honnêtes/ : /Honest data/ })).toBeVisible()
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('lang', locale)
  await expect(page).toHaveTitle(locale === 'fr' ? /Atlas des escaliers roulants/ : /Montréal Escalator Atlas/)
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', locale === 'fr' ? /État et fiabilité/ : /Live escalator status/)
  await expect(page.getByRole('heading', { name: locale === 'fr' ? /Des données honnêtes/ : /Honest data/ })).toBeVisible()
  await expect(page.getByRole('link', { name: locale === 'fr' ? 'Voir le projet sur GitHub' : 'Find project on GitHub' })).toHaveAttribute('href', 'https://github.com/ArnaudJalbert/escalographe')
  await page.getByRole('button', { name: locale === 'fr' ? 'English' : 'Français' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', locale === 'fr' ? 'en' : 'fr')
})

test('@screenshots capture dashboard and escalator detail', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('3 sur 3 escaliers roulants affichés')).toBeVisible()
  await mkdir('screenshots', { recursive: true })
  await page.screenshot({ path: 'screenshots/dashboard.png', fullPage: true })
  await page.goto('/escalators/esc-2')
  await expect(page.getByRole('heading', { name: 'Orange line platform' })).toBeVisible()
  await page.screenshot({ path: 'screenshots/escalator-detail.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByLabel('Disponibilité actuelle: 50.0%')).toBeVisible()
  await page.screenshot({ path: 'screenshots/dashboard-mobile.png', fullPage: true })
})
