# L’Escalographe

**Montréal Escalator Atlas.** A live map and open API for escalators in Montréal. The first screen separates operational, out-of-service, needs-verification, and unknown status. Observation age is shown separately, because an old report of a working escalator is not a fresh report. The website is available in French and English, with French as the default and a persistent language switch.

Live at [arnaudjalbert-escalographe.fly.dev](https://arnaudjalbert-escalographe.fly.dev). The PR application was deployed and verified on October 20, 2026. See [deployment details](DEPLOYMENT.md).

![Tableau de bord en français, alimenté par les observations réelles de la STM et d’OSM](docs/screenshots/dashboard.png)

[English dashboard](docs/screenshots/dashboard-english.png) · [French escalator detail](docs/screenshots/escalator-detail.png). These screenshots come from the locally running product with real source imports, captured on October 19, 2026.

## What it covers

- STM escalator reports supply operational status for STM equipment. Official STM GTFS station centroids locate stations on the map without claiming they are exact escalator positions. OpenStreetMap supplies mapped escalators and geographic metadata; an OSM-only record has unknown operational status.
- Current status, outages, station views, source health, a map, and a searchable table are exposed through a React app and a read-only FastAPI API.
- Historical observations accumulate after ingestion begins. No historical percentage is invented for a newly started database.
- Geographic default is the City of Montréal. STM records outside the city may remain accessible when the API supports the wider query.

The project is independent. It is not affiliated with or endorsed by STM, the City of Montréal, or the OpenStreetMap Foundation. See [data sources](DATA_SOURCES.md) for attribution and limitations.

## Start locally

Install Python 3.12, Node 22, and npm. From the repository root:

```sh
make install
make dev
```

The API listens on `http://localhost:8000`, its interactive documentation on `http://localhost:8000/docs`, and Vite prints the web development URL, typically `http://localhost:5173`. The Makefile uses `./data/escalators.db`; the directory is ignored by Git. The first startup migrates the database. If the scheduler is enabled by the backend, it ingests in the background; you can also request a refresh explicitly:

```sh
make ingest-stm
make ingest-osm
# or: make ingest-all
```

The CLI is also callable from `apps/api` as `python -m app.cli ingest stm`, `python -m app.cli ingest osm`, and `python -m app.cli migrate`. Do not run two schedulers against the same SQLite database.

For a production-like local image, with a Docker daemon running:

```sh
docker compose up --build
```

The site is then at `http://localhost:8000`. Compose uses a named persistent volume mounted at `/data`; remove that volume only when you intentionally want to erase local history. The container migrates the mounted SQLite database before starting one Uvicorn worker.

## API

The API lives under `/api/v1`. For example:

```sh
curl -fsS http://localhost:8000/api/health
curl -fsS 'http://localhost:8000/api/v1/escalators?limit=20&within_montreal=true'
curl -fsS http://localhost:8000/api/v1/stats/summary
curl -fsS http://localhost:8000/api/v1/escalators.geojson
```

See `/docs` for response schemas, filters, station endpoints, history, and source health. API `/api/*` errors remain API errors, not HTML fallback pages.

## Design and measurement

[ARCHITECTURE.md](ARCHITECTURE.md) describes ports, adapters, transaction boundaries, and tests. The French UI calls escalators *escaliers roulants* and uses *pété* as a casual label for an STM-reported out-of-service status. The API keeps the canonical `out_of_service` value. Unknown status and stale data do not imply a breakdown; an old out-of-service observation retains its label and gets a stale warning. Current availability divides operational escalators by operational plus out-of-service plus needs-verification escalators; unknown records are excluded. Coverage is reported separately. A fetch failure does not mark all escalators out of service: previous observations remain and eventually become stale. History is measured by time intervals, not number of rows.

## Checks and deployment

```sh
make lint
make test
make build
docker build -t escalographe .
```

Pull requests run backend lint/tests, frontend lint/types/unit/browser tests/build, and a Docker image build in GitHub Actions. After CI passes on `main`, a second workflow deploys the tested commit using the configured `FLY_API_TOKEN` repository secret. The Fly app and its single `yyz` volume are provisioned. [DEPLOYMENT.md](DEPLOYMENT.md) lists the commands and smoke checks.

Known limits: STM–OSM identity matching is deliberately conservative, so some physical escalators appear twice; STM station-centroid markers are approximate, not device positions; OSM has no live status; early reliability estimates lack enough history; a single SQLite volume is not automatically replicated. If Overpass fails, the adapter explicitly records a partial downtown OSM fallback rather than claiming full-city coverage. No data is fabricated to fill gaps.

## License

Application code is [MIT licensed](LICENSE). OSM data is separate and requires its own attribution and license compliance; see [DATA_SOURCES.md](DATA_SOURCES.md).
