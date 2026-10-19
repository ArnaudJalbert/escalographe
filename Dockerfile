# Build the Vite app once, then serve its static files from FastAPI.
FROM node:22-bookworm-slim AS web-build
WORKDIR /build/web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS api-build
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
WORKDIR /build/api
COPY apps/api/pyproject.toml ./
COPY apps/api/app/ ./app/
RUN uv venv /opt/venv && uv pip install --python /opt/venv/bin/python .

FROM python:3.12-slim-bookworm
ARG GIT_SHA=unknown
RUN apt-get update && apt-get install -y --no-install-recommends gosu ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 app && useradd -u 10001 -g app -m app
COPY --from=api-build /opt/venv /opt/venv
COPY --from=web-build /build/web/dist /app/static
COPY apps/api/ /app/api/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data /app/web \
    && ln -s /app/static /app/web/dist \
    && chown app:app /data /app -R
WORKDIR /app/api
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    DATABASE_URL=sqlite:////data/escalators.db \
    ENVIRONMENT=production \
    APP_VERSION=0.1.0 \
    GIT_SHA=${GIT_SHA}
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
