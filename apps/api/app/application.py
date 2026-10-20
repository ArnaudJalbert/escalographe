"""Use cases; no transport, persistence or source-specific imports."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .domain import Status, availability
from .ports import EscalatorSource, UnitOfWorkFactory


@dataclass(frozen=True)
class EscalatorQuery:
    status: str | None = None
    station: str | None = None
    source: str | None = None
    municipality: str | None = None
    within_montreal: bool | None = True
    bbox: tuple[float, float, float, float] | None = None
    search: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class Summary:
    total: int
    operational: int
    out_of_service: int
    verification_needed: int
    unknown: int
    live_status_coverage: int
    availability: float | None

    @classmethod
    def from_statuses(cls, statuses):
        statuses = list(statuses)
        operating, coverage, percentage = availability(statuses)
        return cls(
            len(statuses),
            operating,
            statuses.count(Status.OUT_OF_SERVICE),
            statuses.count(Status.VERIFICATION_NEEDED),
            statuses.count(Status.UNKNOWN),
            coverage,
            percentage,
        )


class RefreshSource:
    def __init__(
        self, source: EscalatorSource, uow: UnitOfWorkFactory, clock: Callable[[], datetime]
    ):
        self.source, self.uow, self.clock = source, uow, clock

    async def execute(self) -> dict:
        started = self.clock()
        try:
            snapshot = await self.source.fetch()
            # An empty source response is not evidence that all escalators disappeared.
            if not snapshot.records:
                raise ValueError(f"{snapshot.source} returned no escalators")
            if any(r.source != snapshot.source or not r.external_id for r in snapshot.records):
                raise ValueError("source snapshot contains inconsistent identifiers")
            with self.uow() as tx:
                created = sum(tx.ingest(record) for record in snapshot.records)
                result = {
                    "source": snapshot.source,
                    "success": True,
                    "started_at": started,
                    "finished_at": self.clock(),
                    "records_received": len(snapshot.records),
                    "records_created": created,
                    "records_updated": len(snapshot.records) - created,
                    "error_message": None,
                    "metadata": snapshot.metadata,
                }
                tx.add_run(**result)
            return result
        except Exception as exc:
            # A separate transaction records failure without touching previously observed statuses.
            with self.uow() as tx:
                tx.add_run(
                    source=getattr(self.source, "name", "unknown"),
                    success=False,
                    started_at=started,
                    finished_at=self.clock(),
                    records_received=0,
                    records_created=0,
                    records_updated=0,
                    error_message=str(exc),
                )
            raise


class Catalogue:
    def __init__(self, uow: UnitOfWorkFactory, clock: Callable[[], datetime]):
        self.uow, self.clock = uow, clock

    def list(self, query: EscalatorQuery):
        with self.uow() as tx:
            return tx.list_escalators(query)

    def get(self, escalator_id: str):
        with self.uow() as tx:
            return tx.get_escalator(escalator_id)

    def history(self, escalator_id: str):
        with self.uow() as tx:
            return tx.history(escalator_id)

    def stations(self):
        with self.uow() as tx:
            return tx.list_stations()

    def sources(self):
        with self.uow() as tx:
            return tx.runs()

    def source_health(self):
        # Reading runs also proves that the database is reachable and migrated.
        runs = self.sources()
        now = self.clock()
        result = {}
        for name in ("stm", "osm"):
            attempts = [run for run in runs if run["source"] == name]
            successes = [run for run in attempts if run["success"]]
            latest = attempts[0] if attempts else None
            last_success = successes[0]["finished_at"] if successes else None
            freshness = (
                (now - datetime.fromisoformat(last_success)).total_seconds()
                if last_success
                else None
            )
            result[name] = {
                "last_attempt": latest["finished_at"] if latest else None,
                "last_success": last_success,
                "healthy": latest["success"] if latest else None,
                "is_stale": freshness is None or freshness > (900 if name == "stm" else 172800),
                "coverage": successes[0]["metadata"].get("coverage") if successes else None,
            }
        return result

    def outages(self):
        rows = self.list(EscalatorQuery(status="out_of_service", limit=100000))
        for row in rows:
            transitions = self.history(row["id"])
            active = transitions[-1] if transitions else None
            row["out_since"] = (
                active["observed_at"] if active and active["status"] == "out_of_service" else None
            )
        return sorted(
            rows, key=lambda row: (row["out_since"] is None, row["out_since"] or "", row["name"])
        )

    def availability_history(self, days: int, bucket_hours: int):
        from datetime import timedelta

        from .domain import interval_availability

        now = self.clock()
        start = now - timedelta(days=days)
        with self.uow() as tx:
            history = tx.all_history()
        intervals = []
        for row in history:
            observed = datetime.fromisoformat(row["observed_at"])
            last_seen = datetime.fromisoformat(row["last_seen_at"])
            # Count only time bounded by actual repeated observations, not indefinite stale time.
            if last_seen > observed:
                intervals.append((Status(row["status"]), observed, last_seen))
        points = []
        cursor = start
        while cursor < now:
            end = min(cursor + timedelta(hours=bucket_hours), now)
            value = interval_availability(intervals, cursor, end)
            if value is not None:
                points.append({"observed_at": cursor.isoformat(), "availability": value})
            cursor = end
        return {
            "points": points,
            "collection_started_at": history[0]["observed_at"] if history else None,
        }

    @staticmethod
    def summary_for(rows):
        return Summary.from_statuses(Status(row["status"]["value"]) for row in rows)

    def summary(self, within_montreal=True):
        rows = self.list(EscalatorQuery(within_montreal=within_montreal, limit=100000))
        return self.summary_for(rows)
