#!/bin/bash

echo "Creating database directory if necessary..."
mkdir -p /tmp/miiflask

if [ ! -f /tmp/miiflask/miiflask.db ]; then
  echo "Database file not found. Initializing database..."
  conda run --no-capture-output -n mlayer python dbinit.py -p builder.json -d
fi

echo "Starting Gunicorn..."
conda run --no-capture-output -n mlayer gunicorn --bind 0.0.0.0:8000 -w 1 miiflask.flask.app:app
