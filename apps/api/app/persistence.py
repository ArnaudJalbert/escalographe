"""SQLAlchemy outbound adapter. ORM classes and sessions never cross this boundary."""

import json
import os
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .domain import is_stale
from .ports import ExternalEscalatorRecord


class Base(DeclarativeBase):
    pass


class StationRow(Base):
    __tablename__ = "stations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    coordinate_source: Mapped[str | None] = mapped_column(String)
    coordinate_version: Mapped[str | None] = mapped_column(String)


class EscalatorRow(Base):
    __tablename__ = "escalators"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    station_id: Mapped[str | None] = mapped_column(ForeignKey("stations.id"), index=True)
    station: Mapped[StationRow | None] = relationship()
    location_description: Mapped[str | None] = mapped_column(String)
    municipality: Mapped[str | None] = mapped_column(String)
    within_montreal: Mapped[bool | None] = mapped_column(Boolean, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str | None] = mapped_column(String)
    from_level: Mapped[str | None] = mapped_column(String)
    to_level: Mapped[str | None] = mapped_column(String)


class SourceRow(Base):
    __tablename__ = "source_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    escalator_id: Mapped[str] = mapped_column(ForeignKey("escalators.id"), index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(String)
    raw_data_json: Mapped[str] = mapped_column(Text, default="{}")
    first_seen_at: Mapped[str] = mapped_column(String)
    last_seen_at: Mapped[str] = mapped_column(String)
    __table_args__ = (Index("ix_source_identity", "source", "external_id", unique=True),)


class CurrentRow(Base):
    __tablename__ = "current_status"
    escalator_id: Mapped[str] = mapped_column(ForeignKey("escalators.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String)
    source_status: Mapped[str | None] = mapped_column(String)
    observed_at: Mapped[str] = mapped_column(String)
    last_successful_refresh: Mapped[str] = mapped_column(String)


class HistoryRow(Base):
    __tablename__ = "status_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    escalator_id: Mapped[str] = mapped_column(ForeignKey("escalators.id"), index=True)
    status: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    source_status: Mapped[str | None] = mapped_column(String)
    observed_at: Mapped[str] = mapped_column(String, index=True)
    ended_at: Mapped[str | None] = mapped_column(String)
    last_seen_at: Mapped[str] = mapped_column(String)


class RunRow(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, index=True)
    started_at: Mapped[str] = mapped_column(String)
    finished_at: Mapped[str] = mapped_column(String)
    success: Mapped[bool] = mapped_column(Boolean)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


def instant(value):
    return value.isoformat() if isinstance(value, datetime) else value


def parse(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class Database:
    def __init__(self, engine):
        self.engine = engine
        self.sessions = sessionmaker(engine, expire_on_commit=False)

    def __call__(self):
        return Transaction(self.sessions())


class Transaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        try:
            if kind is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

    def ingest(self, record: ExternalEscalatorRecord):
        s = self.session
        existing = s.scalar(
            select(SourceRow).where(
                SourceRow.source == record.source, SourceRow.external_id == record.external_id
            )
        )
        created = existing is None
        if existing is None:
            escalator = EscalatorRow(
                id=str(uuid4()), name=record.name or record.location_description or "Escalator"
            )
            s.add(escalator)
            existing = SourceRow(
                escalator_id=escalator.id,
                source=record.source,
                external_id=record.external_id,
                first_seen_at=instant(record.observed_at),
                last_seen_at=instant(record.observed_at),
            )
            s.add(existing)
        else:
            escalator = s.get(EscalatorRow, existing.escalator_id)
        if record.station_name:
            station_id = str(uuid5(NAMESPACE_URL, "station:" + record.station_name.casefold()))
            station = s.get(StationRow, station_id)
            if station is None:
                station = StationRow(id=station_id, name=record.station_name)
                s.add(station)
            if record.station_latitude is not None and record.station_longitude is not None:
                station.latitude = record.station_latitude
                station.longitude = record.station_longitude
                station.coordinate_source = record.station_coordinate_source
                station.coordinate_version = record.station_coordinate_version
            # Relationship tracks the insert dependency, even if a status lookup autoflushes.
            escalator.station = station
        escalator.name = record.name or escalator.name
        # A missing GTFS match is unknown, not the previous snapshot's city verdict.
        if record.source == "stm":
            escalator.within_montreal = record.within_montreal
        for field in (
            "location_description",
            "municipality",
            "latitude",
            "longitude",
            "direction",
            "from_level",
            "to_level",
        ):
            value = getattr(record, field)
            if value is not None:
                setattr(escalator, field, value)
        if record.source != "stm" and record.within_montreal is not None:
            escalator.within_montreal = record.within_montreal
        existing.source_url = record.source_url
        existing.raw_data_json = json.dumps(record.raw_data, ensure_ascii=False)
        existing.last_seen_at = instant(record.observed_at)
        if record.source == "stm":
            current = s.get(CurrentRow, escalator.id)
            if current is None or parse(current.observed_at) <= record.observed_at:
                if (
                    current is None
                    or current.status != record.status
                    or current.source != record.source
                ):
                    active = s.scalar(
                        select(HistoryRow).where(
                            HistoryRow.escalator_id == escalator.id, HistoryRow.ended_at.is_(None)
                        )
                    )
                    if active:
                        active.ended_at = instant(record.observed_at)
                    s.add(
                        HistoryRow(
                            escalator_id=escalator.id,
                            status=record.status,
                            source=record.source,
                            source_status=record.source_status,
                            observed_at=instant(record.observed_at),
                            last_seen_at=instant(record.observed_at),
                        )
                    )
                else:
                    active = s.scalar(
                        select(HistoryRow).where(
                            HistoryRow.escalator_id == escalator.id, HistoryRow.ended_at.is_(None)
                        )
                    )
                    if active:
                        active.last_seen_at = instant(record.observed_at)
                if current is None:
                    current = CurrentRow(escalator_id=escalator.id)
                    s.add(current)
                current.status, current.source, current.source_status = (
                    record.status,
                    record.source,
                    record.source_status,
                )
                current.observed_at = current.last_successful_refresh = instant(record.observed_at)
        s.flush()
        return created

    def reconciliation_stm_devices(self):
        """STM escalators with the spatial/level/direction evidence to match on."""
        s = self.session
        ids = s.scalars(select(SourceRow.escalator_id).where(SourceRow.source == "stm")).all()
        devices = []
        for escalator_id in ids:
            row = s.get(EscalatorRow, escalator_id)
            if row is None:
                continue
            station = s.get(StationRow, row.station_id) if row.station_id else None
            devices.append(
                {
                    "id": row.id,
                    "station_name": station.name if station else None,
                    "station_latitude": station.latitude if station else None,
                    "station_longitude": station.longitude if station else None,
                    "from_level": row.from_level,
                    "to_level": row.to_level,
                    "direction": row.direction,
                }
            )
        return devices

    def reconciliation_osm_devices(self):
        """Unmerged OSM escalators with their coordinates and mapping tags."""
        s = self.session
        ids = s.scalars(select(SourceRow.escalator_id).where(SourceRow.source == "osm")).all()
        devices = []
        for escalator_id in ids:
            row = s.get(EscalatorRow, escalator_id)
            if row is None:
                continue
            # Already reconciled into an STM device: not a standalone candidate.
            has_stm = s.scalar(
                select(SourceRow).where(
                    SourceRow.escalator_id == escalator_id, SourceRow.source == "stm"
                )
            )
            if has_stm is not None:
                continue
            osm_source = s.scalar(
                select(SourceRow).where(
                    SourceRow.escalator_id == escalator_id, SourceRow.source == "osm"
                )
            )
            raw = (
                json.loads(osm_source.raw_data_json)
                if osm_source is not None and osm_source.raw_data_json
                else {}
            )
            devices.append(
                {
                    "id": row.id,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "level": raw.get("level"),
                    "incline": raw.get("incline"),
                    "conveying": raw.get("conveying"),
                }
            )
        return devices

    def merge_into(self, keep_id, absorbed_id):
        """Collapse ``absorbed_id`` into ``keep_id``; keep the STM status authority.

        Repoints the absorbed device's source/status/history rows at the kept
        device, adopts device geometry the kept row lacks, then deletes the
        absorbed row. OSM carries no live status, so STM levels/direction are
        never overwritten.
        """
        s = self.session
        keep = s.get(EscalatorRow, keep_id)
        absorbed = s.get(EscalatorRow, absorbed_id)
        if keep is None or absorbed is None or keep_id == absorbed_id:
            return False
        for row in s.scalars(select(SourceRow).where(SourceRow.escalator_id == absorbed_id)):
            row.escalator_id = keep_id
        for row in s.scalars(select(CurrentRow).where(CurrentRow.escalator_id == absorbed_id)):
            row.escalator_id = keep_id
        for row in s.scalars(select(HistoryRow).where(HistoryRow.escalator_id == absorbed_id)):
            row.escalator_id = keep_id
        if keep.latitude is None and absorbed.latitude is not None:
            keep.latitude = absorbed.latitude
            keep.longitude = absorbed.longitude
        s.delete(absorbed)
        s.flush()
        return True

    def add_run(self, **fields):
        metadata = fields.pop("metadata", {})
        self.session.add(
            RunRow(
                metadata_json=json.dumps(metadata),
                **{key: instant(value) for key, value in fields.items()},
            )
        )

    def _serialize(self, row):
        s = self.session
        station = s.get(StationRow, row.station_id) if row.station_id else None
        current = s.get(CurrentRow, row.id)
        sources = s.scalars(select(SourceRow).where(SourceRow.escalator_id == row.id)).all()
        return {
            "id": row.id,
            "name": row.name,
            "station": self._station(station) if station else None,
            "location": {
                "latitude": row.latitude,
                "longitude": row.longitude,
                "from_level": row.from_level,
                "to_level": row.to_level,
            },
            "latitude": row.latitude,
            "longitude": row.longitude,
            "direction": row.direction,
            "location_description": row.location_description,
            "municipality": row.municipality,
            "within_montreal": row.within_montreal,
            "status": {
                "value": current.status if current else "unknown",
                "source": current.source if current else None,
                "source_status": current.source_status if current else None,
                "observed_at": current.observed_at if current else None,
                "last_successful_refresh": current.last_successful_refresh if current else None,
                "is_stale": is_stale(
                    parse(current.observed_at) if current else None, datetime.now(UTC)
                ),
            },
            "sources": [
                {
                    "source": src.source,
                    "external_id": src.external_id,
                    "source_url": src.source_url,
                    "first_seen_at": src.first_seen_at,
                    "last_seen_at": src.last_seen_at,
                }
                for src in sources
            ],
        }

    def list_escalators(self, query):
        stmt = select(EscalatorRow).order_by(EscalatorRow.name, EscalatorRow.id)
        if query.within_montreal is True:
            stmt = stmt.where(EscalatorRow.within_montreal.is_(True))
        elif query.within_montreal is False:
            stmt = stmt.where(EscalatorRow.within_montreal.is_(False))
        if query.municipality:
            stmt = stmt.where(EscalatorRow.municipality == query.municipality)
        if query.status:
            stmt = stmt.outerjoin(CurrentRow).where(
                CurrentRow.status == query.status
                if query.status != "unknown"
                else (CurrentRow.status == "unknown") | CurrentRow.escalator_id.is_(None)
            )
        if query.station:
            stmt = stmt.join(StationRow).where(StationRow.name.ilike(f"%{query.station}%"))
        if query.source:
            stmt = stmt.join(SourceRow).where(SourceRow.source == query.source)
        if query.search:
            stmt = stmt.outerjoin(StationRow).where(
                EscalatorRow.name.ilike(f"%{query.search}%")
                | StationRow.name.ilike(f"%{query.search}%")
            )
        if query.bbox:
            west, south, east, north = query.bbox
            stmt = stmt.where(
                EscalatorRow.longitude.between(west, east),
                EscalatorRow.latitude.between(south, north),
            )
        return [
            self._serialize(row)
            for row in self.session.scalars(stmt.offset(query.offset).limit(query.limit)).all()
        ]

    def get_escalator(self, escalator_id):
        row = self.session.get(EscalatorRow, escalator_id)
        return self._serialize(row) if row else None

    def history(self, escalator_id):
        rows = self.session.scalars(
            select(HistoryRow)
            .where(HistoryRow.escalator_id == escalator_id)
            .order_by(HistoryRow.observed_at)
        ).all()
        return [
            {
                "status": r.status,
                "source": r.source,
                "source_status": r.source_status,
                "observed_at": r.observed_at,
                "ended_at": r.ended_at,
                "last_seen_at": r.last_seen_at,
            }
            for r in rows
        ]

    def all_history(self):
        rows = self.session.scalars(select(HistoryRow).order_by(HistoryRow.observed_at)).all()
        return [
            {
                "status": r.status,
                "observed_at": r.observed_at,
                "last_seen_at": r.last_seen_at,
                "ended_at": r.ended_at,
            }
            for r in rows
        ]

    def list_stations(self):
        return [
            self._station(r)
            for r in self.session.scalars(select(StationRow).order_by(StationRow.name))
        ]

    @staticmethod
    def _station(row):
        return {
            "id": row.id,
            "name": row.name,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_source": row.coordinate_source,
            "coordinate_version": row.coordinate_version,
        }

    def runs(self):
        rows = self.session.scalars(
            select(RunRow).order_by(RunRow.started_at.desc()).limit(100)
        ).all()
        # A prolonged source failure must not hide the last known good refresh.
        for source in ("stm", "osm"):
            last_success = self.session.scalar(
                select(RunRow)
                .where(RunRow.source == source, RunRow.success.is_(True))
                .order_by(RunRow.started_at.desc())
                .limit(1)
            )
            if last_success and all(row.id != last_success.id for row in rows):
                rows.append(last_success)
        rows.sort(key=lambda row: row.started_at, reverse=True)
        return [
            {
                "source": r.source,
                "success": r.success,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "records_received": r.records_received,
                "records_created": r.records_created,
                "records_updated": r.records_updated,
                "error_message": r.error_message,
                "metadata": json.loads(r.metadata_json),
            }
            for r in rows
        ]


def create_database(url=None):
    url = url or os.environ.get("DATABASE_URL", "sqlite:///./data/escalators.db")
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        os.makedirs(os.path.dirname(url.removeprefix("sqlite:///")) or ".", exist_ok=True)
    engine = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return Database(engine)
