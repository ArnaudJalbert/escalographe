"""Reconciliation rules (domain) and their persistence wiring (integration)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.application import EscalatorQuery, Reconcile
from app.domain import Status
from app.persistence import Base, Database
from app.ports import ExternalEscalatorRecord
from app.reconciliation import (
    OsmDevice,
    StmDevice,
    directions_conflict,
    haversine_m,
    levels_conflict,
    plan_reconciliation,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
PEEL = (45.5005, -73.5730)


def stm_device(device_id, lat, lon, from_level=None, to_level=None, direction=None):
    return StmDevice(device_id, "Peel", lat, lon, from_level, to_level, direction)


def osm_device(device_id, lat, lon, level=None, incline=None):
    return OsmDevice(device_id, lat, lon, level, incline, "yes")


# --- Domain rules -----------------------------------------------------------


def test_haversine_distance_and_missing_coordinates():
    assert 10 < haversine_m(45.5005, -73.5730, 45.5006, -73.5730) < 20
    assert haversine_m(45.5005, -73.5730, None, -73.5730) is None


def test_directions_conflict_only_on_opposites():
    assert directions_conflict("up", "down") is True
    assert directions_conflict("down", "up") is True
    assert directions_conflict("up", "up") is False
    assert directions_conflict("up", None) is False
    assert directions_conflict(None, "down") is False
    assert directions_conflict(None, None) is False


def test_levels_conflict_only_on_disjoint_numeric_levels():
    assert levels_conflict("0", "1", "2;-1") is True  # {0,1} vs {2,-1}: disjoint
    assert levels_conflict("0", "1", "0;-1") is False  # overlap at 0
    assert levels_conflict("Quai", "Mezzanine", "0;-1") is False  # STM not numeric
    assert levels_conflict(None, None, None) is False


def test_unique_station_match_proposes_merge():
    plan = plan_reconciliation(
        [stm_device("stm-1", *PEEL, "Niveau rue", "Mezzanine", "up")],
        [osm_device("way/1", 45.5006, -73.5731, incline="up")],
    )
    assert len(plan.merges) == 1
    merge = plan.merges[0]
    assert (merge.keep_id, merge.absorbed_id, merge.reason) == (
        "stm-1",
        "way/1",
        "unique-station-match",
    )
    assert plan.skipped == ()


def test_no_nearby_station_is_skipped():
    plan = plan_reconciliation(
        [stm_device("stm-1", *PEEL)],
        [osm_device("way/1", 45.62, -73.70)],
    )
    assert plan.merges == ()
    assert [skip.reason for skip in plan.skipped] == ["no-nearby-station"]


def test_multiple_candidates_without_evidence_are_ambiguous():
    plan = plan_reconciliation(
        [
            stm_device("stm-1", *PEEL, "Niveau rue", "Mezzanine"),
            stm_device("stm-2", *PEEL, "Mezzanine", "Quai"),
        ],
        [osm_device("way/1", 45.5006, -73.5731)],
    )
    assert plan.merges == ()
    assert [skip.reason for skip in plan.skipped] == ["ambiguous-multiple-candidates"]


def test_direction_evidence_disambiguates_candidates():
    plan = plan_reconciliation(
        [
            stm_device("stm-up", *PEEL, "Niveau rue", "Mezzanine", "up"),
            stm_device("stm-down", *PEEL, "Niveau rue", "Mezzanine", "down"),
        ],
        [osm_device("way/1", 45.5006, -73.5731, incline="down")],
    )
    assert [merge.keep_id for merge in plan.merges] == ["stm-down"]
    assert plan.skipped == ()


def test_direction_conflict_with_only_candidate_rules_it_out():
    plan = plan_reconciliation(
        [stm_device("stm-1", *PEEL, "Niveau rue", "Mezzanine", "up")],
        [osm_device("way/1", 45.5006, -73.5731, incline="down")],
    )
    assert plan.merges == ()
    assert [skip.reason for skip in plan.skipped] == ["evidence-conflict"]


def test_competing_osm_devices_keep_both_duplicates():
    plan = plan_reconciliation(
        [stm_device("stm-1", *PEEL, "Niveau rue", "Mezzanine")],
        [
            osm_device("way/1", 45.5006, -73.5731),
            osm_device("way/2", 45.5007, -73.5732),
        ],
    )
    assert [merge.absorbed_id for merge in plan.merges] == ["way/1"]
    assert [(skip.osm_id, skip.reason) for skip in plan.skipped] == [
        ("way/2", "ambiguous-competing-osm")
    ]


# --- Integration ------------------------------------------------------------


def fixture_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return Database(engine)


def stm_record(
    external_id="stm-1",
    station="Peel",
    lat=45.5005,
    lon=-73.5730,
    from_level="Niveau rue",
    to_level="Mezzanine",
    direction="up",
):
    return ExternalEscalatorRecord(
        source="stm",
        external_id=external_id,
        name=None,
        station_name=station,
        location_description=f"{from_level} → {to_level}",
        status=Status.OPERATIONAL,
        source_status="working",
        latitude=None,
        longitude=None,
        direction=direction,
        from_level=from_level,
        to_level=to_level,
        municipality=None,
        within_montreal=True,
        source_url="https://stm.example",
        raw_data={},
        observed_at=NOW,
        station_latitude=lat,
        station_longitude=lon,
        station_coordinate_source="stm_gtfs",
        station_coordinate_version="v1",
    )


def osm_record(external_id="way/1", lat=45.5006, lon=-73.5731, level=None, incline=None):
    return ExternalEscalatorRecord(
        source="osm",
        external_id=external_id,
        name=None,
        station_name=None,
        location_description=None,
        status=Status.UNKNOWN,
        source_status=None,
        latitude=lat,
        longitude=lon,
        direction=None,
        from_level=None,
        to_level=None,
        municipality="Montréal",
        within_montreal=True,
        source_url=f"https://osm.example/{external_id}",
        raw_data={"level": level, "incline": incline, "conveying": "yes"},
        observed_at=NOW,
    )


def test_reconcile_merges_osm_into_stm_and_adopts_geometry():
    db = fixture_db()
    with db() as tx:
        tx.ingest(stm_record())
        tx.ingest(osm_record())
    result = Reconcile(db).execute()
    assert result["candidates"] == 1
    assert result["merged"] == 1
    assert result["kept_separate"] == 0
    with db() as tx:
        rows = tx.list_escalators(EscalatorQuery(within_montreal=None))
    assert len(rows) == 1
    row = rows[0]
    assert sorted(src["source"] for src in row["sources"]) == ["osm", "stm"]
    assert row["status"]["value"] == "operational"
    assert row["latitude"] == pytest.approx(45.5006)
    assert row["longitude"] == pytest.approx(-73.5731)


def test_reconcile_keeps_ambiguous_station_records_separate():
    db = fixture_db()
    with db() as tx:
        tx.ingest(stm_record(external_id="stm-1"))
        tx.ingest(stm_record(external_id="stm-2", from_level="Mezzanine", to_level="Quai"))
        tx.ingest(osm_record())
    result = Reconcile(db).execute()
    assert result["merged"] == 0
    assert result["kept_separate"] == 1
    assert result["skipped"][0]["reason"] == "ambiguous-multiple-candidates"
    with db() as tx:
        assert len(tx.list_escalators(EscalatorQuery(within_montreal=None))) == 3


def test_reconcile_is_idempotent():
    db = fixture_db()
    with db() as tx:
        tx.ingest(stm_record())
        tx.ingest(osm_record())
    assert Reconcile(db).execute()["merged"] == 1
    second = Reconcile(db).execute()
    assert second["candidates"] == 0
    assert second["merged"] == 0
