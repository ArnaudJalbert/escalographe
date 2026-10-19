"""Source client tests use real captured source shapes and no live network."""

from pathlib import Path

import httpx
import pytest

from app.adapters.outbound.osm.source import OsmEscalatorSource
from app.adapters.outbound.stm.source import StmEscalatorSource

P = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_stm_reads_details_and_retries_transient_failure():
    calls = []
    index = (P / "stm_index.html").read_text()
    detail = (P / "stm_berri.html").read_text()

    def respond(request):
        calls.append(str(request.url))
        assert request.headers.get("user-agent")
        if request.url.path.endswith("/ascenseur"):
            if calls.count(str(request.url)) == 1:
                return httpx.Response(503)
            return httpx.Response(200, text=index)
        return httpx.Response(200, text=detail)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), headers={"User-Agent": "Fixture test"}
    ) as client:
        snapshot = await StmEscalatorSource(client, backoff=0).fetch()
    assert len(snapshot.records) == 65 * 22
    assert snapshot.metadata["stations"] == 65
    assert sum(r.status == "out_of_service" for r in snapshot.records) == 65
    assert calls.count("https://www.stm.info/fr/infos/etat-du-service/ascenseur") == 2
    assert snapshot.records[0].station_latitude is not None
    assert snapshot.records[0].latitude is None


@pytest.mark.asyncio
async def test_stm_station_centroids_and_city_polygon():
    from app.adapters.outbound.stm.geography import station_location

    for name, inside in [
        ("Berri-UQAM", True),
        ("Jean-Talon", True),
        ("Côte-des-Neiges", True),
        ("Montmorency", False),
        ("Longueuil–Université-de-Sherbrooke", False),
    ]:
        location = station_location(name)
        assert location is not None, name
        assert location[2] is inside, name
    assert station_location("  STATION   de l'Eglise  ") is not None
    assert station_location("Côte-Sainte-Catherine") is not None
    assert station_location("D'Iberville") is not None
    assert station_location("Assomption") is not None
    assert station_location("Montmorency -Zone B")[2] is False
    assert station_location("Cartier -Zone B")[2] is False
    assert station_location("Imaginary station") is None


@pytest.mark.asyncio
async def test_stm_station_failure_aborts_entire_snapshot():
    index = (P / "stm_index.html").read_text()

    def respond(request):
        if request.url.path.endswith("/ascenseur"):
            return httpx.Response(200, text=index)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await StmEscalatorSource(client, retries=0).fetch()


@pytest.mark.asyncio
async def test_osm_city_area_query_and_unknown_status():
    fixture = (P / "osm_overpass.json").read_text()

    def respond(request):
        assert "map_to_area" in request.url.params["data"]
        assert "1634158" in request.url.params["data"]
        assert "bbox" not in request.url.params
        return httpx.Response(200, text=fixture)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        snapshot = await OsmEscalatorSource(client).fetch()
    assert len(snapshot.records) == 2
    assert snapshot.metadata["coverage"] == "city_boundary"
    assert all(r.status == "unknown" for r in snapshot.records)
    assert all(r.latitude is not None and r.longitude is not None for r in snapshot.records)


@pytest.mark.asyncio
async def test_osm_failure_is_explicitly_partial_real_api_sample():
    xml = (P / "osm_downtown_map.xml").read_text()

    def respond(request):
        if "interpreter" in request.url.path:
            return httpx.Response(504)
        return httpx.Response(200, text=xml)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        snapshot = await OsmEscalatorSource(client, retries=0).fetch()
    assert snapshot.metadata["partial"] is True
    assert snapshot.metadata["coverage"] == "partial_downtown_sample"
    assert {r.external_id for r in snapshot.records} == {
        "way/1319982885",
        "way/1319982887",
        "way/1319982889",
    }
    assert all(r.status == "unknown" for r in snapshot.records)


@pytest.mark.asyncio
async def test_osm_does_not_replace_data_with_empty_response():
    def respond(request):
        return httpx.Response(200, json={"elements": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError, match="zero city escalators"):
            await OsmEscalatorSource(client, retries=0, allow_partial_fallback=False).fetch()
