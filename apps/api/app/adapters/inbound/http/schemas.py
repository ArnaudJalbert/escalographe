"""Public HTTP schemas. Domain and application layers do not import these models."""

from typing import Literal

from pydantic import BaseModel, Field


class StationRef(BaseModel):
    id: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    coordinate_source: str | None = None


class Location(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    from_level: str | None = None
    to_level: str | None = None


class CurrentStatus(BaseModel):
    value: Literal["operational", "out_of_service", "verification_needed", "unknown"]
    source: str | None = None
    source_status: str | None = None
    observed_at: str | None = None
    last_successful_refresh: str | None = None
    is_stale: bool


class SourceRecord(BaseModel):
    source: str
    external_id: str
    source_url: str | None = None
    first_seen_at: str
    last_seen_at: str


class Escalator(BaseModel):
    id: str
    name: str
    station: StationRef | None = None
    location: Location
    latitude: float | None = None
    longitude: float | None = None
    direction: str | None = None
    location_description: str | None = None
    municipality: str | None = None
    within_montreal: bool | None = None
    status: CurrentStatus
    sources: list[SourceRecord]


class EscalatorPage(BaseModel):
    items: list[Escalator]
    total: int = Field(description="Count after filtering, before pagination")
    limit: int
    offset: int


class Summary(BaseModel):
    total: int
    operational: int
    out_of_service: int
    verification_needed: int
    unknown: int
    live_status_coverage: int = Field(
        description="Operational + out of service + needs verification"
    )
    availability: float | None = Field(
        description="Percent operational among records with known live status"
    )
    last_successful_stm_refresh: str | None = None


class SourceHealth(BaseModel):
    last_attempt: str | None = None
    last_success: str | None = None
    healthy: bool | None = None
    is_stale: bool
    coverage: str | None = None


class Health(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    version: str
    git_sha: str | None = None
    sources: dict[str, SourceHealth]
