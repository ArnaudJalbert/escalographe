"""Application contracts; source adapters implement EscalatorSource.fetch."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, Self

from .domain import Status


@dataclass(frozen=True)
class ExternalEscalatorRecord:
    source: str
    external_id: str
    name: str | None
    station_name: str | None
    location_description: str | None
    status: Status
    source_status: str | None
    latitude: float | None
    longitude: float | None
    direction: str | None
    from_level: str | None
    to_level: str | None
    municipality: str | None
    within_montreal: bool | None
    source_url: str | None
    raw_data: dict[str, Any]
    observed_at: datetime
    station_latitude: float | None = None
    station_longitude: float | None = None
    station_coordinate_source: str | None = None
    station_coordinate_version: str | None = None


@dataclass(frozen=True)
class SourceSnapshot:
    source: str
    records: tuple[ExternalEscalatorRecord, ...]
    fetched_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class EscalatorSource(Protocol):
    async def fetch(self) -> SourceSnapshot: ...


class UnitOfWork(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> None: ...
    def ingest(self, record: ExternalEscalatorRecord) -> bool: ...
    def add_run(self, **fields: Any) -> None: ...
    def list_escalators(self, query: Any) -> list[Any]: ...
    def get_escalator(self, escalator_id: str) -> Any: ...
    def history(self, escalator_id: str) -> list[Any]: ...
    def all_history(self) -> list[Any]: ...
    def list_stations(self) -> list[Any]: ...
    def runs(self) -> list[Any]: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
