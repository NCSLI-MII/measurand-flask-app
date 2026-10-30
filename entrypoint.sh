#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${APP_DATA_DIR:-/home/data/mii}"
mkdir -p "$DATA_DIR"

echo "Starting miiflask container"
echo "APP_DATA_DIR=$DATA_DIR"
echo "Contents of /app:"
ls -la /app

# Seed/refresh data if DB file is missing (empty volume on fresh deploy)
if [ ! -f "$DATA_DIR/miiflask.db" ]; then
    echo "Database not found at $DATA_DIR/miiflask.db — running init.sh"
    bash /app/init.sh "$DATA_DIR"
else
    echo "Database present at $DATA_DIR/miiflask.db — skipping init"
fi

echo "Starting gunicorn"
exec gunicorn --bind 0.0.0.0:8000 -w 1 wsgi:application
