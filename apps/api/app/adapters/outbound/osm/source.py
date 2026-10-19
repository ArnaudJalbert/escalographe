"""OpenStreetMap city-boundary Overpass source; OSM never supplies live state."""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from app.domain import Status
from app.ports import ExternalEscalatorRecord, SourceSnapshot

from .parser import parse_overpass

LOGGER = logging.getLogger(__name__)
USER_AGENT = "Escalographe/0.1 (+https://github.com/ArnaudJalbert/escalographe; OSM attribution in application)"
# Main public interpreter. Area 3601634158 is generated from city boundary relation 1634158,
# not a rectangle and not the whole Montréal agglomeration.
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CITY_RELATION_ID = 1634158
QUERY = """[out:json][timeout:60];
rel(1634158);map_to_area->.city;
(
 way["highway"="steps"]["conveying"](area.city);
 node["highway"="steps"]["conveying"](area.city);
 relation["highway"="steps"]["conveying"](area.city);
 node["highway"="escalator"](area.city);
 way["highway"="escalator"](area.city);
 relation["highway"="escalator"](area.city);
);
out center geom;
"""
RETRYABLE = {429, 500, 502, 503, 504}
# Explicitly *partial* emergency seed only; never presented as city-wide coverage.
PARTIAL_BBOX = "-73.569,45.502,-73.562,45.507"
PARTIAL_URL = "https://api.openstreetmap.org/api/0.6/map"


class OsmEscalatorSource:
    name = "osm"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        retries: int = 2,
        backoff: float = 1.0,
        overpass_url: str = OVERPASS_URL,
        allow_partial_fallback: bool = True,
    ):
        self.client = client
        self.retries = retries
        self.backoff = backoff
        self.overpass_url = overpass_url
        self.allow_partial_fallback = allow_partial_fallback

    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        for attempt in range(self.retries + 1):
            try:
                response = await client.get(url, headers={"User-Agent": USER_AGENT}, **kwargs)
                if response.status_code in RETRYABLE and attempt < self.retries:
                    await asyncio.sleep(min(self.backoff * 2**attempt, 8))
                    continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.retries:
                    raise RuntimeError(f"OSM source fetch failed after retries: {url}") from exc
                await asyncio.sleep(min(self.backoff * 2**attempt, 8))
        raise RuntimeError(f"OSM source fetch failed after retries: {url}")

    @staticmethod
    def _partial_xml(xml: str) -> dict:
        """Convert a bounded official OSM map response to the Overpass parser shape."""
        root = ET.fromstring(xml)
        if root.tag != "osm":
            raise ValueError("OSM map response is not OSM XML")
        nodes = {
            n.attrib["id"]: {"lat": float(n.attrib["lat"]), "lon": float(n.attrib["lon"])}
            for n in root.findall("node")
            if all(key in n.attrib for key in ("id", "lat", "lon"))
        }
        elements = []
        for way in root.findall("way"):
            tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
            if tags.get("highway") != "steps" or tags.get("conveying") in (None, "no"):
                continue
            if way.get("id") is None:
                continue
            geometry = [
                nodes[nd.attrib["ref"]]
                for nd in way.findall("nd")
                if "ref" in nd.attrib and nd.attrib["ref"] in nodes
            ]
            if geometry:
                elements.append(
                    {"type": "way", "id": int(way.attrib["id"]), "tags": tags, "geometry": geometry}
                )
        return {"elements": elements}

    async def fetch(self) -> SourceSnapshot:
        async def collect(client):
            metadata = {
                "city_boundary_osm_relation": CITY_RELATION_ID,
                "coverage": "city_boundary",
                "source_url": self.overpass_url,
                "attribution": "© OpenStreetMap contributors",
            }
            try:
                response = await self._get(client, self.overpass_url, params={"data": QUERY})
                data = response.json()
                rows = parse_overpass(data)
                if not rows:
                    # An empty answer may reflect stale/missing Overpass area, not no escalators.
                    raise ValueError(
                        "Overpass returned zero city escalators; rejecting ambiguous refresh"
                    )
            except (httpx.HTTPError, RuntimeError, ValueError, TypeError) as exc:
                if not self.allow_partial_fallback:
                    raise
                LOGGER.warning(
                    "overpass_unavailable_partial_osm_fallback", extra={"reason": str(exc)}
                )
                response = await self._get(client, PARTIAL_URL, params={"bbox": PARTIAL_BBOX})
                rows = parse_overpass(self._partial_xml(response.text))
                if not rows:
                    raise ValueError("Partial OSM API fallback has no valid escalators") from exc
                metadata.update(
                    {
                        "coverage": "partial_downtown_sample",
                        "partial": True,
                        "sample_bbox": PARTIAL_BBOX,
                        "source_url": str(response.url),
                        "warning": "Only a small downtown sample; not city-wide coverage",
                    }
                )
            now = datetime.now(UTC)
            records = tuple(
                ExternalEscalatorRecord(
                    source="osm",
                    external_id=row["external_id"],
                    name=row["raw_data"]["tags"].get("name"),
                    station_name=row["station"],
                    location_description=row["location_description"],
                    status=Status.UNKNOWN,
                    source_status=None,
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    direction=None,
                    from_level=None,
                    to_level=None,
                    municipality="Montréal" if not metadata.get("partial") else None,
                    within_montreal=True if not metadata.get("partial") else None,
                    source_url=row["source_url"],
                    raw_data=row["raw_data"],
                    observed_at=now,
                )
                for row in rows
            )
            LOGGER.info(
                "osm_snapshot_fetched",
                extra={"count": len(records), "coverage": metadata["coverage"]},
            )
            return SourceSnapshot("osm", records, now, metadata)

        if self.client is not None:
            return await collect(self.client)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(75.0), follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            return await collect(client)
