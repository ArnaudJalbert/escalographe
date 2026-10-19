"""Offline parser fixtures captured from STM and Overpass on 2026-10-19."""

import json
from pathlib import Path

import pytest

from app.adapters.outbound.osm.parser import parse_overpass
from app.adapters.outbound.stm.parser import parse_station, station_urls

FIXTURES = Path(__file__).parent / "fixtures"
STM = "https://www.stm.info/fr/infos/etat-du-service/ascenseur"


def test_station_index_deduplicates_interchange_links():
    urls = station_urls((FIXTURES / "stm_index.html").read_text())
    assert len(urls) == 65
    assert urls.count(STM + "/station-berri-uqam") == 1
    assert all(url.startswith(STM + "/station-") for url in urls)


def test_berri_real_outage_and_duplicate_corridor_identity():
    rows = parse_station((FIXTURES / "stm_berri.html").read_text(), STM + "/station-berri-uqam")
    assert len(rows) == 22
    assert sum(r["status"] == "operational" for r in rows) == 21
    outages = [r for r in rows if r["status"] == "out_of_service"]
    assert len(outages) == 1
    assert outages[0]["from_level"] == "accès Gare d'autocars"
    assert outages[0]["direction"] is None
    assert all(r["latitude"] is None and r["longitude"] is None for r in rows)
    assert len({r["external_id"] for r in rows}) == len(rows)
    dupes = [
        r
        for r in rows
        if r["from_level"] == "quai Montmorency" and r["to_level"] == "quai Honoré-Beaugrand"
    ]
    assert len(dupes) == 3
    assert len({r["external_id"] for r in dupes}) == 3


def test_peel_outage_and_direction():
    rows = parse_station((FIXTURES / "stm_peel.html").read_text(), STM + "/station-peel")
    assert len(rows) == 8
    assert {r["direction"] for r in rows} == {"up", "down", None}
    assert (
        next(r for r in rows if r["status"] == "out_of_service")["from_level"] == "accès Peel est"
    )


def test_unknown_direction_is_not_assumed_operational():
    rows = parse_station(
        (FIXTURES / "stm_jean_talon.html").read_text(), STM + "/station-jean-talon"
    )
    unknown = [row for row in rows if row["source_status"] == "Sens inconnu"]
    assert len(unknown) == 4
    assert all(row["status"] == "unknown" and row["direction"] is None for row in unknown)


def test_station_with_no_escalators_is_not_schema_failure():
    assert (
        parse_station((FIXTURES / "stm_jolicoeur.html").read_text(), STM + "/station-jolicoeur")
        == []
    )


def test_stm_schema_change_fails_instead_of_reporting_no_outages():
    with pytest.raises(ValueError, match="station links"):
        station_urls("<html><body>Service normal</body></html>")
    with pytest.raises(ValueError, match="station heading"):
        parse_station("<html>all working</html>", STM + "/station-peel")


def test_osm_real_coordinates_and_no_invented_status():
    payload = json.loads((FIXTURES / "osm_overpass.json").read_text())
    records = parse_overpass(payload)
    assert {r["external_id"] for r in records} == {"way/1021741791", "way/1021741792"}
    assert all(r["status"] == "unknown" and r["source_status"] is None for r in records)
    assert all(r["geometry"] and len(r["geometry"]) == 2 for r in records)
    assert all(45.503 < r["latitude"] < 45.504 for r in records)
    assert {r["raw_data"]["incline"] for r in records} == {"up", "down"}
    assert all(
        r["direction"] is None for r in records
    )  # OSM incline is not STM operating direction.


def test_osm_malformed_and_legacy_tags():
    with pytest.raises(TypeError, match="elements"):
        parse_overpass({"error": "busy"})
    assert (
        parse_overpass(
            {
                "elements": [
                    {
                        "type": "way",
                        "id": 1,
                        "tags": {"highway": "steps", "conveying": "no"},
                        "center": {"lat": 45.5, "lon": -73.5},
                    }
                ]
            }
        )
        == []
    )
    rows = parse_overpass(
        {
            "elements": [
                {
                    "type": "node",
                    "id": 3,
                    "lat": 45.5,
                    "lon": -73.5,
                    "tags": {"highway": "escalator"},
                }
            ]
        }
    )
    assert len(rows) == 1 and rows[0]["status"] == "unknown"
