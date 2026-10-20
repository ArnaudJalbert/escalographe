"""Station centroids from STM GTFS and city membership from OSM relation 1634158.

GTFS station points locate stations, never individual escalators. Unmatched names
stay unknown instead of being assigned a nearby or guessed coordinate.
"""

import json
import re
import unicodedata
from functools import lru_cache
from importlib.resources import files
from itertools import pairwise


def normalize_station_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).casefold()
    name = "".join(char for char in name if not unicodedata.combining(char))
    name = re.sub(r"[^a-z0-9]+", " ", name).strip()
    name = re.sub(r"^station\s+", "", name)
    name = re.sub(r"\s+zone b$", "", name)
    name = re.sub(r"\bsaint\b", "st", name)
    return re.sub(r"\bsainte\b", "ste", name)


# Confirmed spelling expansions, not fuzzy or proximity-based matches.
_ALIASES = {
    "longueuil universite de sherbrooke": "longueuil u de sherbrooke",
    "longueuil universite de sherbrooke metro": "longueuil u de sherbrooke",
    "parc": "du parc",
    "assomption": "de l assomption",
    "d iberville": "iberville",
}


def _on_segment(x, y, ax, ay, bx, by):
    return (
        min(ax, bx) <= x <= max(ax, bx)
        and min(ay, by) <= y <= max(ay, by)
        and abs((bx - ax) * (y - ay) - (by - ay) * (x - ax)) < 1e-10
    )


def _in_ring(longitude, latitude, ring):
    inside = False
    for a, b in pairwise(ring):
        ax, ay = a
        bx, by = b
        if _on_segment(longitude, latitude, ax, ay, bx, by):
            return True
        if (ay > latitude) != (by > latitude):
            crossing = ax + (latitude - ay) * (bx - ax) / (by - ay)
            if longitude < crossing:
                inside = not inside
    return inside


def _in_geometry(longitude, latitude, geometry):
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError("Expected a polygonal city boundary")
    return any(
        _in_ring(longitude, latitude, rings[0])
        and not any(_in_ring(longitude, latitude, hole) for hole in rings[1:])
        for rings in polygons
    )


@lru_cache(maxsize=1)
def geography_snapshot():
    data = json.loads(files(__package__).joinpath("station_geography.json").read_text())
    if len(data["stations"]) != 68 or data["boundary"]["relation_id"] != 1634158:
        raise ValueError("Unexpected station geography snapshot")
    return data


@lru_cache(maxsize=1)
def _stations():
    index = {}
    for stop_id, name, latitude, longitude in geography_snapshot()["stations"]:
        key = normalize_station_name(name)
        if key in index:
            raise ValueError(f"Ambiguous GTFS station name: {name}")
        index[key] = (latitude, longitude, stop_id)
    return index


def station_location(name: str):
    """Return (station latitude, longitude, in-city) or None for no exact match."""
    key = normalize_station_name(name)
    match = _stations().get(_ALIASES.get(key, key))
    if match is None:
        return None
    latitude, longitude, _ = match
    return latitude, longitude, _in_geometry(longitude, latitude, geography_snapshot()["geometry"])
