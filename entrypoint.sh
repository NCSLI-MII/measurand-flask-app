#!/bin/bash

files=$(ls)
echo "$files"
if [ ! -f data/miiflask.db ]; then
  echo "Database file not found. Initializing database..."
  python dbinit.py 
fi

echo "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:8000 -w 1 wsgi
