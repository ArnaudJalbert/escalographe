"""One in-process scheduling task per application worker."""

import asyncio
import logging

from .application import Reconcile
from .bootstrap import use_cases

logger = logging.getLogger(__name__)


async def run_scheduler(db):
    async def ingest(source):
        try:
            await use_cases(db, source)[source].execute()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ingestion_failed source=%s", source)

    async def reconcile():
        try:
            await asyncio.to_thread(Reconcile(db).execute)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("reconciliation_failed")

    async def loop():
        next_osm = 0.0
        while True:
            await ingest("stm")
            now = asyncio.get_running_loop().time()
            if now >= next_osm:
                await ingest("osm")
                await reconcile()
                next_osm = now + 86400
            await asyncio.sleep(300)

    return asyncio.create_task(loop(), name="escalator-ingestion")
