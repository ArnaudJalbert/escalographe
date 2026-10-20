"""Conservative STM/OSM reconciliation rules.

Framework-free domain logic that decides whether an OSM-mapped escalator and an
STM-reported escalator are the same physical device. The bias is deliberately
toward keeping records separate: a false merge (collapsing two different
devices) is worse than a duplicate (one device shown twice). A merge is only
proposed when a single, unambiguous STM candidate survives every filter.

Evidence evaluated, in order:

1. Spatial: the OSM device must lie within ``station_radius_m`` of an STM
   station centroid. STM records carry no device coordinates, so the station
   centroid is the only reliable anchor.
2. Direction: STM operating direction (up/down) is compared against the OSM
   ``incline`` tag. A contradiction rules a candidate out; agreement or a
   missing value never rules one in.
3. Levels: only a clear numeric contradiction between STM level labels and the
   OSM ``level`` tag rules a candidate out. The two sources use different
   vocabularies, so level comparison is intentionally coarse.
4. Uniqueness: exactly one STM candidate must remain. Ambiguity — several
   candidates, or several OSM devices competing for one STM device — keeps
   duplicates rather than guessing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
_DIRECTIONS = {DIRECTION_UP, DIRECTION_DOWN}

# OSM escalators inside a station usually sit within this distance of the GTFS
# station centroid. A larger radius risks attributing a device to the wrong
# station at dense interchanges, so the default is deliberately small.
DEFAULT_STATION_RADIUS_M = 200.0

_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class StmDevice:
    id: str
    station_name: str | None
    station_latitude: float | None
    station_longitude: float | None
    from_level: str | None
    to_level: str | None
    direction: str | None


@dataclass(frozen=True)
class OsmDevice:
    id: str
    latitude: float | None
    longitude: float | None
    level: str | None
    incline: str | None
    conveying: str | None


@dataclass(frozen=True)
class ReconciliationConfig:
    station_radius_m: float = DEFAULT_STATION_RADIUS_M


@dataclass(frozen=True)
class Merge:
    keep_id: str
    absorbed_id: str
    reason: str


@dataclass(frozen=True)
class Skip:
    osm_id: str
    reason: str


@dataclass(frozen=True)
class ReconciliationPlan:
    merges: tuple[Merge, ...]
    skipped: tuple[Skip, ...]


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres, or None when any coordinate is missing."""
    if any(value is None for value in (lat1, lon1, lat2, lon2)):
        return None
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _direction(value):
    """Normalize a free-text direction to up/down/None."""
    if not isinstance(value, str):
        return None
    direction = value.strip().casefold()
    return direction if direction in _DIRECTIONS else None


def directions_conflict(stm_direction, osm_incline) -> bool:
    """True only when both sides name an opposite vertical direction."""
    stm, osm = _direction(stm_direction), _direction(osm_incline)
    if stm is None or osm is None:
        return False
    return stm != osm


def _numeric_levels(*labels) -> set[float]:
    numbers: set[float] = set()
    for label in labels:
        if not label:
            continue
        for token in re.findall(r"-?\d+(?:\.\d+)?", str(label)):
            numbers.add(float(token))
    return numbers


def levels_conflict(stm_from, stm_to, osm_level) -> bool:
    """True only when both sources give numeric levels and none overlap.

    STM level labels (``Quai``, ``Mezzanine``) and OSM ``level`` tags (``0;-1``)
    rarely share a vocabulary, so this is deliberately coarse: it can rule a
    candidate out on a clear numeric contradiction, never rule one in.
    """
    osm_numbers = _numeric_levels(osm_level)
    if not osm_numbers:
        return False
    stm_numbers = _numeric_levels(stm_from, stm_to)
    if not stm_numbers:
        return False
    return osm_numbers.isdisjoint(stm_numbers)


def _stations_with_devices(stm_devices):
    stations: dict[tuple[float, float], list[StmDevice]] = {}
    for device in stm_devices:
        if device.station_latitude is None or device.station_longitude is None:
            continue
        key = (device.station_latitude, device.station_longitude)
        stations.setdefault(key, []).append(device)
    return stations


def plan_reconciliation(stm_devices, osm_devices, config=None) -> ReconciliationPlan:
    """Propose merges that are safe; skip everything ambiguous.

    Each STM device absorbs at most one OSM device. Two OSM devices competing
    for the same STM device are both kept separate rather than picking one.
    """
    config = config or ReconciliationConfig()
    stations = _stations_with_devices(stm_devices)
    merges: list[Merge] = []
    skipped: list[Skip] = []
    claimed: set[str] = set()

    for osm in osm_devices:
        if osm.latitude is None or osm.longitude is None:
            skipped.append(Skip(osm.id, "no-osm-coordinates"))
            continue
        nearby = [
            device
            for (station_lat, station_lon), devices in stations.items()
            for device in devices
            if (
                (distance := haversine_m(osm.latitude, osm.longitude, station_lat, station_lon))
                is not None
                and distance <= config.station_radius_m
            )
        ]
        if not nearby:
            skipped.append(Skip(osm.id, "no-nearby-station"))
            continue
        candidates = [
            device
            for device in nearby
            if not directions_conflict(device.direction, osm.incline)
            and not levels_conflict(device.from_level, device.to_level, osm.level)
        ]
        if not candidates:
            skipped.append(Skip(osm.id, "evidence-conflict"))
            continue
        if len(candidates) > 1:
            skipped.append(Skip(osm.id, "ambiguous-multiple-candidates"))
            continue
        candidate = candidates[0]
        if candidate.id in claimed:
            skipped.append(Skip(osm.id, "ambiguous-competing-osm"))
            continue
        claimed.add(candidate.id)
        merges.append(Merge(candidate.id, osm.id, "unique-station-match"))

    return ReconciliationPlan(tuple(merges), tuple(skipped))
