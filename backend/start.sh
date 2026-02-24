#!/bin/bash
set -e

echo "=== A-Stats Engine Starting ==="
echo "Environment: ${ENVIRONMENT:-not set}"
echo "Port: ${PORT:-8000}"
echo "Database URL set: $(if [ -n "$DATABASE_URL" ]; then echo 'yes'; else echo 'NO - NOT SET'; fi)"
echo "CORS_ORIGINS: ${CORS_ORIGINS:-not set}"

echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations completed successfully."
else
    echo "ERROR: Migrations failed (exit code $?). Refusing to start on stale schema."
    exit 1
fi

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2}
