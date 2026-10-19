"""HTTP inbound adapter; routes only invoke application use cases."""

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .adapters.inbound.http.schemas import Escalator, EscalatorPage, Health, Summary
from .application import Catalogue, EscalatorQuery
from .bootstrap import migrate
from .persistence import create_database


def create_app(db=None, start_scheduler=True):
    @asynccontextmanager
    async def lifespan(app):
        if start_scheduler:
            migrate()
            from .scheduler import run_scheduler

            scheduler = await run_scheduler(db)
            try:
                yield
            finally:
                scheduler.cancel()
        else:
            yield

    app = FastAPI(
        title="Montréal Escalator Atlas API",
        description="Live escalator status and historical reliability across Montréal.",
        version="0.1.0",
        lifespan=lifespan,
    )
    db = db or create_database()
    catalogue = Catalogue(db, lambda: datetime.now(UTC))

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    def lookup(escalator_id):
        item = catalogue.get(escalator_id)
        if not item:
            raise HTTPException(status_code=404, detail="Escalator not found")
        return item

    @app.get(
        "/api/health",
        tags=["Health"],
        response_model=Health,
        summary="Application and source health",
    )
    def health():
        try:
            sources = catalogue.source_health()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        return {
            "status": "ok",
            "database": "ok",
            "version": os.environ.get("APP_VERSION", "0.1.0"),
            "git_sha": os.environ.get("GIT_SHA"),
            "sources": sources,
        }

    @app.get(
        "/api/v1/escalators",
        tags=["Escalators"],
        response_model=EscalatorPage,
        summary="List escalators and their current observed status",
    )
    def escalators(
        status: str | None = None,
        station: str | None = None,
        source: str | None = None,
        municipality: str | None = None,
        within_montreal: bool | None = True,
        bbox: str | None = None,
        search: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        if status and status not in (
            "operational",
            "out_of_service",
            "verification_needed",
            "unknown",
        ):
            raise HTTPException(422, "Invalid status")
        bounds = None
        if bbox:
            try:
                bounds = tuple(float(x) for x in bbox.split(","))
                if len(bounds) != 4 or bounds[0] > bounds[2] or bounds[1] > bounds[3]:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, "bbox must be west,south,east,north") from None
        filters = EscalatorQuery(
            status, station, source, municipality, within_montreal, bounds, search, limit, offset
        )
        items = catalogue.list(filters)
        # Count separately without offset to preserve pagination metadata.
        total = len(
            catalogue.list(
                EscalatorQuery(
                    status,
                    station,
                    source,
                    municipality,
                    within_montreal,
                    bounds,
                    search,
                    100000,
                    0,
                )
            )
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @app.get("/api/v1/escalators.geojson", tags=["Escalators"])
    def geojson(within_montreal: bool | None = True):
        items = catalogue.list(EscalatorQuery(within_montreal=within_montreal, limit=100000))
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            x["longitude"]
                            if x["longitude"] is not None
                            else x["station"]["longitude"],
                            x["latitude"]
                            if x["latitude"] is not None
                            else x["station"]["latitude"],
                        ],
                    },
                    "properties": {
                        **{k: v for k, v in x.items() if k not in ("latitude", "longitude")},
                        "geometry_accuracy": (
                            "device" if x["latitude"] is not None else "station_approximation"
                        ),
                    },
                }
                for x in items
                if (x["latitude"] is not None and x["longitude"] is not None)
                or (
                    x["station"] is not None
                    and x["station"].get("latitude") is not None
                    and x["station"].get("longitude") is not None
                )
            ],
        }

    @app.get(
        "/api/v1/escalators/{escalator_id}",
        tags=["Escalators"],
        response_model=Escalator,
        summary="Get one escalator, including provenance and freshness",
    )
    def escalator(escalator_id: str):
        return lookup(escalator_id)

    @app.get("/api/v1/escalators/{escalator_id}/history", tags=["Escalators"])
    def history(escalator_id: str):
        lookup(escalator_id)
        return catalogue.history(escalator_id)

    @app.get("/api/v1/stations", tags=["Stations"])
    def stations():
        return catalogue.stations()

    @app.get("/api/v1/stations/{station_id}", tags=["Stations"])
    def station(station_id: str):
        item = next((s for s in catalogue.stations() if s["id"] == station_id), None)
        if not item:
            raise HTTPException(404, "Station not found")
        items = catalogue.list(EscalatorQuery(station=item["name"], limit=100000))
        return {**item, "escalators": items, "summary": asdict(catalogue.summary_for(items))}

    @app.get(
        "/api/v1/stats/summary",
        tags=["Statistics"],
        response_model=Summary,
        summary="Current availability and live-status coverage",
    )
    def summary(within_montreal: bool | None = True):
        result = asdict(catalogue.summary(within_montreal))
        latest = next(
            (r for r in catalogue.sources() if r["source"] == "stm" and r["success"]), None
        )
        result["last_successful_stm_refresh"] = latest["finished_at"] if latest else None
        return result

    @app.get("/api/v1/stats/outages", tags=["Statistics"])
    def outages():
        return catalogue.outages()

    @app.get("/api/v1/stats/stations", tags=["Statistics"])
    def station_stats():
        return [
            {
                **s,
                "outages": len(
                    catalogue.list(
                        EscalatorQuery(station=s["name"], status="out_of_service", limit=100000)
                    )
                ),
            }
            for s in catalogue.stations()
        ]

    @app.get("/api/v1/stats/availability", tags=["Statistics"])
    def availability_history(range: str = Query("24h", pattern="^(24h|7d|30d)$")):
        days, bucket_hours = {"24h": (1, 1), "7d": (7, 24), "30d": (30, 24)}[range]
        return {"range": range, **catalogue.availability_history(days, bucket_hours)}

    @app.get("/api/v1/sources", tags=["Sources"])
    def sources():
        return catalogue.sources()

    @app.get("/api/v1/meta", tags=["Metadata"])
    def meta():
        return {
            "name": "Montréal Escalator Atlas",
            "status_stale_after_minutes": 15,
            "sources": ["stm", "osm"],
            "attribution": "© OpenStreetMap contributors",
        }

    static = Path(__file__).resolve().parents[2] / "web" / "dist"
    if static.joinpath("index.html").exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith(("api/", "docs", "openapi.json")):
                raise HTTPException(404)
            asset = static / path
            if path and asset.is_file() and asset.resolve().is_relative_to(static.resolve()):
                return FileResponse(asset)
            return FileResponse(static / "index.html")

    return app


app = create_app()
