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
test('dashboard status, map, selection and filters', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /what’s working/i })).toBeVisible()
  await expect(page.getByLabel('Availability now: 50.0%')).toBeVisible()
  await expect(page.getByRole('heading', { name: /out of service 1/i })).toBeVisible()
  await expect(page.locator('.leaflet-container')).toBeVisible()
  await expect(page.locator('.leaflet-interactive')).toHaveCount(3)
  await page.getByLabel('Filter by status').selectOption('out_of_service')
  await expect(page.getByText('1 of 3 escalators shown')).toBeVisible()
  await expect(page.locator('.leaflet-interactive')).toHaveCount(1)
  await page.locator('.leaflet-interactive').click()
  await expect(page.locator('.map-popup')).toBeVisible()
  await expect(page.locator('.map-popup').getByText('Station location; device position unknown.')).toBeVisible()
  await page.locator('.map-popup').getByRole('link', { name: /view escalator/i }).click()
  await expect(page).toHaveURL(/\/escalators\/esc-2$/)
  await expect(page.getByRole('heading', { name: 'Orange line platform' })).toBeVisible()
  await expect(page.getByText('Station location; device position unknown.')).toBeVisible()
  await expect(page.getByText(/this observation may be stale/i)).toBeVisible()
})

test('@screenshots capture dashboard and escalator detail', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('3 of 3 escalators shown')).toBeVisible()
  await mkdir('screenshots', { recursive: true })
  await page.screenshot({ path: 'screenshots/dashboard.png', fullPage: true })
  await page.goto('/escalators/esc-2')
  await expect(page.getByRole('heading', { name: 'Orange line platform' })).toBeVisible()
  await page.screenshot({ path: 'screenshots/escalator-detail.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByLabel('Availability now: 50.0%')).toBeVisible()
  await page.screenshot({ path: 'screenshots/dashboard-mobile.png', fullPage: true })
})
