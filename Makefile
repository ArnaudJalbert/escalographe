PYTHON := apps/api/.venv/bin/python
RUFF := apps/api/.venv/bin/ruff
PYTEST := apps/api/.venv/bin/pytest
UVICORN := apps/api/.venv/bin/uvicorn
DB_URL := sqlite:///../../data/escalators.db

.PHONY: install dev api web migrate ingest-stm ingest-osm ingest-all reconcile test lint build docker

install:
	python3 -m venv apps/api/.venv
	$(PYTHON) -m pip install -e './apps/api[dev]'
	cd apps/web && npm ci

# One local API worker and one Vite server. Ctrl-C stops both.
dev:
	@mkdir -p data
	@trap 'kill $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	 (cd apps/api && DATABASE_URL=$(DB_URL) ENVIRONMENT=development .venv/bin/python -m app.cli migrate && DATABASE_URL=$(DB_URL) ENVIRONMENT=development .venv/bin/uvicorn app.main:app --reload --port 8000) & api_pid=$$!; \
	 (cd apps/web && npm run dev -- --host 0.0.0.0) & web_pid=$$!; wait

api:
	@mkdir -p data
	cd apps/api && DATABASE_URL=$(DB_URL) .venv/bin/python -m app.cli migrate && DATABASE_URL=$(DB_URL) .venv/bin/uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev -- --host 0.0.0.0

migrate:
	@mkdir -p data
	cd apps/api && DATABASE_URL=$(DB_URL) .venv/bin/python -m app.cli migrate

ingest-stm ingest-osm ingest-all: ingest-%:
	cd apps/api && DATABASE_URL=$(DB_URL) .venv/bin/python -m app.cli ingest $*

reconcile:
	cd apps/api && DATABASE_URL=$(DB_URL) .venv/bin/python -m app.cli reconcile

test:
	cd apps/api && .venv/bin/pytest
	cd apps/web && npm test -- --run

lint:
	cd apps/api && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd apps/web && npm run lint && npm run typecheck

build:
	cd apps/web && npm run build

docker:
	docker compose up --build
