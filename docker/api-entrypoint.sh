#!/bin/sh
set -e

echo "Applying database migrations..."
migrated=0
for attempt in $(seq 1 15); do
    if uv run --frozen --no-dev --extra api alembic upgrade head; then
        migrated=1
        break
    fi
    echo "Database not ready (attempt ${attempt}/15); retrying in 2s..."
    sleep 2
done

if [ "$migrated" -ne 1 ]; then
    echo "Could not apply migrations — giving up." >&2
    exit 1
fi

exec uv run --frozen --no-dev --extra api uvicorn banditbrain.api.main:app --host 0.0.0.0 --port 8000
