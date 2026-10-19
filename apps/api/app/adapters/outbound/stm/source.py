"""First-party STM HTML source. Do not interpret the station index as equipment status."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.domain import Status
from app.ports import ExternalEscalatorRecord, SourceSnapshot

from .geography import geography_snapshot, station_location
from .parser import BASE_URL, parse_station, station_urls

LOGGER = logging.getLogger(__name__)
USER_AGENT = "MontrealEscalatorAtlas/0.1 (+https://github.com/; STM-derived factual status)"
RETRYABLE = {429, 500, 502, 503, 504}


class StmEscalatorSource:
    """Fetch all distinct STM station details; fail atomically on partial refresh.

    The use case decides whether to persist the returned snapshot. A missing or
    failed station must never cause a partial overwrite of previous statuses.
    """

    name = "stm"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        retries: int = 2,
        backoff: float = 0.5,
        concurrency: int = 4,
    ):
        self.client = client
        self.retries = retries
        self.backoff = backoff
        self.concurrency = concurrency

    async def _get(self, client: httpx.AsyncClient, url: str) -> str:
        for attempt in range(self.retries + 1):
            try:
                response = await client.get(url, headers={"User-Agent": USER_AGENT})
                if response.status_code in RETRYABLE and attempt < self.retries:
                    delay = min(self.backoff * 2**attempt, 8)
                    if response.headers.get("retry-after", "").isdigit():
                        delay = max(delay, min(int(response.headers["retry-after"]), 30))
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                return response.text
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.retries:
                    raise RuntimeError(f"STM fetch failed after retries: {url}") from exc
                await asyncio.sleep(min(self.backoff * 2**attempt, 8))
        raise RuntimeError(f"STM fetch failed after retries: {url}")

    async def fetch(self) -> SourceSnapshot:
        async def collect(client):
            urls = station_urls(await self._get(client, BASE_URL))
            semaphore = asyncio.Semaphore(self.concurrency)

            async def station(url):
                async with semaphore:
                    return parse_station(await self._get(client, url), url)

            pages = await asyncio.gather(*(station(url) for url in urls))
            now = datetime.now(UTC)
            rows = [row for page in pages for row in page]
            if not rows:
                raise ValueError("STM returned station links but no escalator records")
            geography = geography_snapshot()
            locations = {row["station"]: station_location(row["station"]) for row in rows}
            unmatched = sorted(name for name, location in locations.items() if location is None)
            if unmatched:
                LOGGER.warning("stm_stations_without_gtfs_match", extra={"stations": unmatched})

            def make_record(row):
                location = locations[row["station"]]
                latitude, longitude, within_montreal = (
                    location if location is not None else (None, None, None)
                )
                return ExternalEscalatorRecord(
                    source="stm",
                    external_id=row["external_id"],
                    name=None,
                    station_name=row["station"],
                    location_description=row["location_description"],
                    status=Status(row["status"]),
                    source_status=row["source_status"],
                    latitude=None,
                    longitude=None,
                    direction=row["direction"],
                    from_level=row["from_level"],
                    to_level=row["to_level"],
                    municipality=None,
                    within_montreal=within_montreal,
                    source_url=row["source_url"],
                    raw_data=row["raw_data"],
                    observed_at=now,
                    station_latitude=latitude,
                    station_longitude=longitude,
                    station_coordinate_source="stm_gtfs" if location else None,
                    station_coordinate_version=(
                        geography["gtfs"]["feed_version"] if location else None
                    ),
                )

            records = tuple(make_record(row) for row in rows)
            LOGGER.info("stm_snapshot_fetched", extra={"stations": len(urls), "records": len(rows)})
            return SourceSnapshot(
                "stm",
                records,
                now,
                {
                    "stations": len(urls),
                    "source_url": BASE_URL,
                    "status_authority": "stm",
                    "station_geography": {
                        "gtfs": geography["gtfs"],
                        "boundary": geography["boundary"],
                    },
                    "unmatched_station_names": unmatched,
                },
            )

        if self.client is not None:
            return await collect(self.client)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(18.0), follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            return await collect(client)
