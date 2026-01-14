#!/bin/bash

if [ ! -f var/miiflask.db ]; then
  echo "Database file not found. Initializing database..."
  python dbinit_v3.py 
fi

echo "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:8000 -w 1 miiflask.flask.app:app
