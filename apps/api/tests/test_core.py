from datetime import UTC, datetime, timedelta

from app.application import Catalogue, RefreshSource, Summary
from app.domain import Status, availability, is_stale, transition
from app.ports import ExternalEscalatorRecord, SourceSnapshot

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def record(source="stm", external_id="1", status=Status.OPERATIONAL):
    return ExternalEscalatorRecord(
        source=source,
        external_id=external_id,
        name="Escalator 1",
        station_name="Berri-UQAM",
        location_description="platform",
        status=status,
        source_status="working",
        latitude=None,
        longitude=None,
        direction=None,
        from_level=None,
        to_level=None,
        municipality="Montréal",
        within_montreal=True,
        source_url="https://example.org",
        raw_data={},
        observed_at=NOW,
    )


def test_domain_status_and_freshness():
    assert availability([Status.OPERATIONAL, Status.UNKNOWN, Status.OUT_OF_SERVICE]) == (1, 2, 50.0)
    assert availability([Status.UNKNOWN]) == (0, 0, None)
    assert is_stale(NOW, NOW + timedelta(minutes=16))
    assert not is_stale(NOW, NOW + timedelta(minutes=15))
    assert transition(Status.OPERATIONAL, Status.OPERATIONAL) is False
    assert transition(Status.OPERATIONAL, Status.OUT_OF_SERVICE) is True


class FakeUow:
    def __init__(self):
        self.records = {}
        self.statuses = {}
        self.history = []
        self.runs = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def ingest(self, r):
        key = (r.source, r.external_id)
        created = key not in self.records
        self.records[key] = r
        if r.source == "stm":
            if key not in self.statuses or self.statuses[key] != r.status:
                self.history.append((key, r.status))
            self.statuses[key] = r.status
        return created

    def add_run(self, **data):
        self.runs.append(data)

    def list_escalators(self, query):
        return list(self.records.values())


class FakeSource:
    def __init__(self, snapshot=None, error=None):
        self.snapshot, self.error = snapshot, error

    async def fetch(self):
        if self.error:
            raise self.error
        return self.snapshot


import pytest


@pytest.mark.asyncio
async def test_refresh_preserves_status_after_failure():
    db = FakeUow()
    snapshot = SourceSnapshot(
        source="stm", records=(record(),), fetched_at=NOW, metadata={"coverage": "complete"}
    )
    assert (await RefreshSource(FakeSource(snapshot), lambda: db, lambda: NOW).execute())[
        "records_created"
    ] == 1
    assert db.statuses[("stm", "1")] == Status.OPERATIONAL
    assert db.runs[0]["metadata"]["coverage"] == "complete"
    assert len(db.history) == 1
    await RefreshSource(FakeSource(snapshot), lambda: db, lambda: NOW).execute()
    assert len(db.history) == 1
    with pytest.raises(RuntimeError):
        await RefreshSource(
            FakeSource(error=RuntimeError("offline")), lambda: db, lambda: NOW
        ).execute()
    assert db.statuses[("stm", "1")] == Status.OPERATIONAL
    assert db.runs[-1]["success"] is False


def test_interval_availability_excludes_unknown_and_counts_time():
    from app.domain import interval_availability

    intervals = [
        (Status.OPERATIONAL, NOW, NOW + timedelta(hours=2)),
        (Status.OUT_OF_SERVICE, NOW + timedelta(hours=2), NOW + timedelta(hours=3)),
        (Status.UNKNOWN, NOW, NOW + timedelta(hours=10)),
    ]
    assert interval_availability(intervals, NOW, NOW + timedelta(hours=3)) == 66.7
    assert (
        interval_availability(intervals, NOW + timedelta(hours=4), NOW + timedelta(hours=5)) is None
    )


def test_summary_unknown_excluded():
    summary = Summary.from_statuses(
        [Status.OPERATIONAL, Status.UNKNOWN, Status.VERIFICATION_NEEDED]
    )
    assert summary.availability == 50.0
    assert summary.live_status_coverage == 2


def test_source_health_separates_failed_ingestion_from_device_status():
    class HealthUow(FakeUow):
        def __init__(self):
            self.health_runs = []

        def runs(self):
            return self.health_runs

    db = HealthUow()
    db.health_runs = [
        {
            "source": "stm",
            "success": False,
            "finished_at": (NOW + timedelta(minutes=2)).isoformat(),
            "metadata": {},
        },
        {
            "source": "stm",
            "success": True,
            "finished_at": NOW.isoformat(),
            "metadata": {"coverage": "network"},
        },
    ]
    health = Catalogue(lambda: db, lambda: NOW + timedelta(minutes=2)).source_health()
    assert health["stm"]["healthy"] is False
    assert health["stm"]["last_success"] == NOW.isoformat()
    assert health["stm"]["is_stale"] is False
    assert health["osm"]["is_stale"] is True
