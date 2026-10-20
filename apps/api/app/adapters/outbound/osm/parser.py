"""Normalize Overpass JSON without turning mapped infrastructure into live status."""

from __future__ import annotations

import math


def _point(value):
    if not isinstance(value, dict):
        return None
    lat, lon = value.get("lat"), value.get("lon")
    if (
        isinstance(lat, (int, float))
        and not isinstance(lat, bool)
        and isinstance(lon, (int, float))
        and not isinstance(lon, bool)
        and math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    ):
        return {"lat": float(lat), "lon": float(lon)}
    return None


def parse_overpass(payload: dict) -> list[dict]:
    """Parse valid OSM escalators, preserving exact geometry and useful tags.

    Overpass area uses city boundary relation 1634158. No local rectangle
    filter or assumption that conveying=yes means an operational device.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise TypeError("Overpass response has no elements array")
    records = []
    seen = set()
    for item in payload["elements"]:
        if not isinstance(item, dict):
            continue
        kind, oid, tags = item.get("type"), item.get("id"), item.get("tags")
        if (
            kind not in {"node", "way", "relation"}
            or not isinstance(oid, int)
            or not isinstance(tags, dict)
        ):
            continue
        conveying = tags.get("conveying")
        # Some older mapping uses highway=escalator; conveying=no is not one.
        if not (
            (tags.get("highway") == "steps" and conveying not in (None, "no"))
            or tags.get("highway") == "escalator"
        ):
            continue
        geometry = (
            [_point(p) for p in item.get("geometry", [])]
            if isinstance(item.get("geometry"), list)
            else []
        )
        geometry = [p for p in geometry if p is not None]
        if kind == "node":
            center = _point(item)
            if center and not geometry:
                geometry = [center]
        else:
            center = _point(item.get("center"))
            if not center and geometry:
                # Geographic midpoint of the actual mapped nodes, not a guessed station center.
                center = {
                    "lat": sum(p["lat"] for p in geometry) / len(geometry),
                    "lon": sum(p["lon"] for p in geometry) / len(geometry),
                }
        if center is None or (kind, oid) in seen:
            continue
        seen.add((kind, oid))
        records.append(
            {
                "external_id": f"{kind}/{oid}",
                "source_url": f"https://www.openstreetmap.org/{kind}/{oid}",
                "latitude": center["lat"],
                "longitude": center["lon"],
                "geometry": geometry or None,
                "station": tags.get("station"),
                "station_id": None,
                "location_description": tags.get("name") or tags.get("description"),
                "from_level": None,
                "to_level": None,
                "direction": None,
                "status": "unknown",
                "source_status": None,
                "raw_data": {
                    "tags": tags,
                    "level": tags.get("level"),
                    "indoor": tags.get("indoor"),
                    "incline": tags.get("incline"),
                    "conveying": conveying,
                    "operator": tags.get("operator"),
                    "building": tags.get("building"),
                    "access": tags.get("access"),
                    "geometry": geometry or None,
                },
            }
        )
    return records
