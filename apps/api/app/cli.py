"""CLI inbound adapter using the same application use cases as the scheduler."""

import argparse
import asyncio
import json

from .application import Reconcile
from .bootstrap import migrate, use_cases
from .persistence import create_database
from .reconciliation import ReconciliationConfig


def main():
    parser = argparse.ArgumentParser(description="Montréal Escalator Atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    sub.add_parser("init-db")
    sub.add_parser("health")
    sub.add_parser("ingest").add_argument("source", choices=["stm", "osm", "all"])
    sub.add_parser("reconcile").add_argument(
        "--radius",
        type=float,
        default=None,
        help="station attribution radius in metres (default 200)",
    )
    args = parser.parse_args()
    if args.command in ("migrate", "init-db"):
        migrate()
        return
    migrate()
    db = create_database()
    if args.command == "health":
        with db() as tx:
            print(json.dumps(tx.runs(), ensure_ascii=False))
        return
    if args.command == "reconcile":
        config = ReconciliationConfig(station_radius_m=args.radius) if args.radius else None
        print(json.dumps(Reconcile(db, config).execute(), ensure_ascii=False))
        return

    async def ingest():
        for source in ("stm", "osm") if args.source == "all" else (args.source,):
            print(
                json.dumps(
                    await use_cases(db, source)[source].execute(), default=str, ensure_ascii=False
                )
            )

    asyncio.run(ingest())


if __name__ == "__main__":
    main()
