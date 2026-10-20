# L’Escalographe web

React, TypeScript, Vite, Tailwind, TanStack Query, React Leaflet, and Recharts frontend for the Montréal Escalator Atlas API.

```bash
npm ci
npm run dev           # proxy /api to localhost:8000
npm run lint
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run screenshots   # ignored output in apps/web/screenshots/
```

`VITE_API_BASE_URL` can point to an API origin; leave it unset when the API and SPA share an origin. The browser never contacts STM directly. Playwright intercepts API requests with deterministic test-only records. Its map tiles are deterministic, decorative test fixtures, not real street tiles. An existing Chromium binary can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome`.

The map prefers device coordinates. When only a station centroid is available, the dashed marker is grouped by station and explicitly labeled "Station location; device position unknown." An unknown-only or empty dataset shows no availability percentage rather than a misleading 0%.
