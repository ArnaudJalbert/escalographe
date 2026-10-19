"""Framework-free status and reliability rules."""

from datetime import datetime, timedelta
from enum import StrEnum


class Status(StrEnum):
    OPERATIONAL = "operational"
    OUT_OF_SERVICE = "out_of_service"
    VERIFICATION_NEEDED = "verification_needed"
    UNKNOWN = "unknown"


def availability(statuses):
    known = [status for status in statuses if status != Status.UNKNOWN]
    operational = sum(status == Status.OPERATIONAL for status in known)
    return operational, len(known), round(100 * operational / len(known), 1) if known else None


def is_stale(
    observed_at: datetime | None, now: datetime, threshold: timedelta = timedelta(minutes=15)
) -> bool:
    return observed_at is None or now - observed_at > threshold


def interval_availability(intervals, start: datetime, end: datetime) -> float | None:
    """Observed operational time divided by covered known-status time."""
    operational = covered = 0.0
    for status, observed_at, ended_at in intervals:
        if status == Status.UNKNOWN:
            continue
        seconds = max(0.0, (min(end, ended_at) - max(start, observed_at)).total_seconds())
        covered += seconds
        if status == Status.OPERATIONAL:
            operational += seconds
    return round(100 * operational / covered, 1) if covered else None


def transition(previous: Status | None, current: Status) -> bool:
    return previous != current
