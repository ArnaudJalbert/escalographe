from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.application import EscalatorQuery
from app.domain import Status
from app.main import create_app
from app.persistence import Base, Database
from app.ports import ExternalEscalatorRecord

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def fixture_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return Database(engine)


def record(status=Status.OPERATIONAL, observed_at=NOW, source="stm", external_id="1"):
    return ExternalEscalatorRecord(
        source,
        external_id,
        "Escalator",
        "Berri-UQAM",
        "platform",
        status,
        status.value,
        45.5,
        -73.56,
        "up",
        "platform",
        "mezzanine",
        "Montréal",
        True,
        "https://example.org",
        {"test": True},
        observed_at,
    )


def test_persistence_transition_and_osm_does_not_override_stm():
    db = fixture_db()
    with db() as tx:
        tx.ingest(record())
    with db() as tx:
        tx.ingest(record(observed_at=NOW.replace(hour=1)))
    with db() as tx:
        tx.ingest(record(Status.UNKNOWN, source="osm", external_id="way/2"))
    with db() as tx:
        rows = tx.list_escalators(EscalatorQuery())
        assert len(rows) == 2
        stm = next(row for row in rows if row["sources"][0]["source"] == "stm")
        assert stm["status"]["value"] == "operational"
        assert len(tx.history(stm["id"])) == 1
    with db() as tx:
        tx.ingest(record(Status.OUT_OF_SERVICE, NOW.replace(hour=2)))
    with db() as tx:
        history = tx.history(stm["id"])
        assert len(history) == 2
        assert history[0]["ended_at"] is not None
        assert tx.get_escalator(stm["id"])["status"]["value"] == "out_of_service"


def test_station_coordinates_do_not_become_device_coordinates_and_fk_order():
    from dataclasses import replace

    db = fixture_db()
    with db() as tx:
        tx.ingest(
            replace(
                record(),
                latitude=None,
                longitude=None,
                station_latitude=45.515,
                station_longitude=-73.56,
                station_coordinate_source="stm_gtfs",
                within_montreal=True,
            )
        )
    client = TestClient(create_app(db=db, start_scheduler=False))
    item = client.get("/api/v1/escalators").json()["items"][0]
    assert item["latitude"] is None and item["longitude"] is None
    assert item["station"]["latitude"] == 45.515
    assert item["station"]["longitude"] == -73.56
    assert item["station"]["coordinate_source"] == "stm_gtfs"
    assert client.get("/api/v1/stations").json()[0]["latitude"] == 45.515
    feature = client.get("/api/v1/escalators.geojson").json()["features"][0]
    assert feature["geometry"]["coordinates"] == [-73.56, 45.515]
    assert feature["properties"]["geometry_accuracy"] == "station_approximation"


def test_unmatched_station_remains_without_coordinates():
    from dataclasses import replace

    db = fixture_db()
    with db() as tx:
        tx.ingest(
            replace(
                record(),
                station_name="Unknown Stop",
                latitude=None,
                longitude=None,
                within_montreal=None,
            )
        )
    with db() as tx:
        item = tx.list_escalators(EscalatorQuery(within_montreal=None))[0]
    assert item["station"]["latitude"] is None
    assert item["station"]["longitude"] is None
    assert item["within_montreal"] is None


def test_existing_escalator_can_acquire_a_new_station_without_fk_failure():
    from dataclasses import replace

    db = fixture_db()
    with db() as tx:
        tx.ingest(replace(record(), station_name=None))
    with db() as tx:
        tx.ingest(
            replace(
                record(),
                station_name="Berri-UQAM",
                station_latitude=45.515,
                station_longitude=-73.56,
                station_coordinate_source="stm_gtfs",
            )
        )
    with db() as tx:
        rows = tx.list_escalators(EscalatorQuery())
    assert len(rows) == 1
    assert rows[0]["station"]["latitude"] == 45.515


def test_unknown_city_classification_does_not_retain_stale_true():
    from dataclasses import replace

    db = fixture_db()
    with db() as tx:
        tx.ingest(record())
    with db() as tx:
        tx.ingest(replace(record(), within_montreal=None, station_name="Unknown Stop"))
    with db() as tx:
        assert tx.list_escalators(EscalatorQuery(within_montreal=True)) == []
        assert (
            tx.list_escalators(EscalatorQuery(within_montreal=None))[0]["within_montreal"] is None
        )


def test_outages_expose_known_transition_start():
    db = fixture_db()
    with db() as tx:
        tx.ingest(record(Status.OUT_OF_SERVICE))
    result = (
        TestClient(create_app(db=db, start_scheduler=False)).get("/api/v1/stats/outages").json()
    )
    assert result[0]["out_since"] == NOW.isoformat()
    assert result[0]["status"]["value"] == "out_of_service"


def test_ingestion_metadata_round_trips():
    db = fixture_db()
    with db() as tx:
        tx.add_run(
            source="osm",
            started_at=NOW,
            finished_at=NOW,
            success=True,
            records_received=1,
            records_created=1,
            records_updated=0,
            error_message=None,
            metadata={"coverage": "partial_downtown_sample"},
        )
    with db() as tx:
        assert tx.runs()[0]["metadata"]["coverage"] == "partial_downtown_sample"


def test_source_health_keeps_last_success_after_many_failed_attempts():
    from datetime import timedelta

    db = fixture_db()
    with db() as tx:
        for index in range(102):
            successful = index == 0
            when = NOW + timedelta(minutes=index)
            tx.add_run(
                source="stm",
                started_at=when,
                finished_at=when,
                success=successful,
                records_received=1 if successful else 0,
                records_created=0,
                records_updated=0,
                error_message=None if successful else "unavailable",
                metadata={},
            )
    with db() as tx:
        runs = tx.runs()
    assert len(runs) == 101
    assert runs[0]["success"] is False
    assert next(run for run in runs if run["success"])["finished_at"] == NOW.isoformat()


def test_unknown_city_membership_stm_remains_visible():
    from dataclasses import replace

    db = fixture_db()
    with db() as tx:
        tx.ingest(replace(record(), within_montreal=None))
    with db() as tx:
        assert tx.list_escalators(EscalatorQuery(within_montreal=True)) == []
        assert len(tx.list_escalators(EscalatorQuery(within_montreal=None))) == 1
        assert tx.list_escalators(EscalatorQuery(within_montreal=False)) == []


def test_availability_history_uses_observed_intervals():
    db = fixture_db()
    now = datetime.now(UTC)
    from datetime import timedelta

    with db() as tx:
        tx.ingest(record(observed_at=now - timedelta(minutes=20)))
    with db() as tx:
        tx.ingest(record(observed_at=now - timedelta(minutes=10)))
    client = TestClient(create_app(db=db, start_scheduler=False))
    data = client.get("/api/v1/stats/availability?range=24h").json()
    assert data["points"]
    assert any(point["availability"] == 100.0 for point in data["points"])


def test_api_empty_and_populated():
    db = fixture_db()
    client = TestClient(create_app(db=db, start_scheduler=False))
    health_response = client.get("/api/health")
    assert health_response.json()["status"] == "ok"
    assert health_response.json()["database"] == "ok"
    assert health_response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/v1/stats/summary").json()["availability"] is None
    with db() as tx:
        tx.ingest(record())
    listing = client.get("/api/v1/escalators").json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert client.get("/api/v1/escalators/" + item["id"]).json()["status"]["value"] == "operational"
    assert (
        client.get("/api/v1/escalators/" + item["id"] + "/history").json()[0]["status"]
        == "operational"
    )
    assert client.get("/api/v1/stats/summary").json()["availability"] == 100.0
    assert client.get("/api/v1/escalators?status=out_of_service").json()["total"] == 0
    assert len(client.get("/api/v1/escalators.geojson").json()["features"]) == 1
    assert client.get("/api/v1/stations").json()[0]["name"] == "Berri-UQAM"
    assert client.get("/api/v1/escalators/missing").status_code == 404
