import ast
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.persistence import create_database


def test_import_boundaries():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    forbidden = {
        "fastapi",
        "sqlalchemy",
        "httpx",
        "alembic",
        "persistence",
        "adapters",
        "bootstrap",
        "main",
        "scheduler",
        "cli",
    }
    for name in ("domain.py", "application.py", "ports.py", "reconciliation.py"):
        tree = ast.parse((app_dir / name).read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module.removeprefix("app."))
            elif isinstance(node, ast.Import):
                imports.extend(alias.name.removeprefix("app.") for alias in node.names)
        assert not any(module.split(".")[0] in forbidden for module in imports), name
        if name in ("domain.py", "reconciliation.py"):
            assert not any(module.split(".")[0] in ("application", "ports") for module in imports)


def test_alembic_initial_upgrade_is_repeatable(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    assert {
        "escalators",
        "stations",
        "source_records",
        "current_status",
        "status_history",
        "ingestion_runs",
    } <= set(inspect(create_database(url).engine).get_table_names())


def test_station_coordinate_migration_preserves_existing_rows(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "existing.db")
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "1c8e1e44a928")
    engine = create_database(url).engine
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO stations (id, name) VALUES ('s1', 'Berri-UQAM')"))
        conn.execute(
            text(
                "INSERT INTO escalators (id, name, station_id, latitude, longitude) "
                "VALUES ('e1', 'device', 's1', 45.5, -73.5)"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as conn:
        station = conn.execute(
            text("SELECT name, latitude, longitude, coordinate_source FROM stations WHERE id='s1'")
        ).one()
        device = conn.execute(
            text("SELECT latitude, longitude, station_id FROM escalators WHERE id='e1'")
        ).one()
    assert station == ("Berri-UQAM", None, None, None)
    assert device == (45.5, -73.5, "s1")
