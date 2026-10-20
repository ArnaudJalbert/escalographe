"""Outermost wiring; source adapters are delivered independently."""

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from .application import RefreshSource
from .persistence import create_database


def migrate():
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")


def use_cases(db=None, source=None):
    db = db or create_database()
    cases = {}
    # Import only the requested provider: the other source can be unavailable.
    if source in (None, "stm"):
        from .adapters.outbound.stm.source import StmEscalatorSource

        cases["stm"] = RefreshSource(StmEscalatorSource(), db, lambda: datetime.now(UTC))
    if source in (None, "osm"):
        from .adapters.outbound.osm.source import OsmEscalatorSource

        cases["osm"] = RefreshSource(OsmEscalatorSource(), db, lambda: datetime.now(UTC))
    return cases
