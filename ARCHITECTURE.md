# Architecture

L’Escalographe uses a Python hexagonal backend. The API, CLI, and scheduler are three ways to invoke the same application use cases; none owns status normalization or ingestion decisions.

```text
                    FastAPI    CLI    Scheduler
                       \        |       /
                        application
                     use cases / ports
                              |
                            domain
                      entities / rules
                              ^
                              |
              outbound port implementations
              SQLAlchemy    STM     Overpass
```

The arrow of *code dependencies* points inward: adapters import application ports and domain types; application imports domain; domain imports neither adapters nor frameworks. An application port describes what the use case needs. An adapter supplies the implementation at startup in the outer bootstrap layer. The ORM, FastAPI, HTTP responses, HTML selectors, and Overpass syntax never enter the domain. Domain and application tests can use fake ports without a database, network, or web framework. Separate adapter tests cover parsing and SQL mapping. CI runs backend tests, including dependency-boundary tests.

## Request and ingestion paths

An HTTP request enters FastAPI, becomes an application query, calls the unit-of-work port, then serializes application data into an HTTP response. Scheduled and CLI refreshes invoke the same refresh use case. The STM adapter retrieves current operational reports; the Overpass adapter discovers geometry and metadata. Both return normalized source records. Source identity is kept by `(source, external_id)`; a reconciliation step then collapses an OSM device into an STM device only when a single, unambiguous candidate survives the station, direction and level filters, never on proximity alone. That conservative choice can still leave duplicate physical devices, but keeps false merges rarer than duplicates; see issue #4. An ingestion transaction preserves source provenance, current status, status transitions, and run health. A failed fetch records an ingestion error but leaves the previous observation intact. OSM alone never implies an operational escalator.

The unit of work owns the transaction for each refresh. SQLAlchemy models and sessions stay inside the persistence adapter, which serializes application-facing dictionaries; they are not domain entities. One process owns SQLite writes and the scheduler. A new provider needs an adapter that returns the normalized source snapshot and composition-root wiring. PostgreSQL would require a replacement persistence adapter, migration plan, and deployment configuration.

## Runtime

The Node build stage produces Vite static files in `/app/static`. The Python image serves FastAPI and the SPA from port 8000. `/api/*`, `/docs`, and `/openapi.json` remain API routes; only non-API browser routes use the SPA fallback. The container entrypoint migrates `/data/escalators.db` after the Fly volume is mounted, then starts one Uvicorn worker. The image drops root privileges after adjusting the mount ownership. Fly runs one machine in `yyz`, does not auto-stop it, and mounts exactly one `data` volume at `/data`. This is a deliberate availability tradeoff to avoid two independent SQLite histories and two schedulers. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Measurement

Current availability is `operational / (operational + out_of_service + verification_needed)`. Unknown statuses do not count in either term; report live-status coverage separately. Staleness measures time since the last successful observation and does not rewrite the status. Historical availability uses the duration of observed status intervals rather than event counts. If a source is unavailable, do not interpret missing observations as outages.
