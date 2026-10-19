#!/bin/sh
set -eu

# Fly mounts the persistent volume after image build. It starts owned by root.
if [ "$(id -u)" -eq 0 ]; then
    mkdir -p /data
    chown -R app:app /data
    exec gosu app "$0" "$@"
fi

# The Fly release command has no volume, so migrations must run here.
python -m app.cli migrate
exec "$@"
