#!/bin/bash

files=$(ls)
echo "$files"
DATA_DIR=${APP_DATA_DIR:-/home/data/mii}
mkdir -p "$DATA_DIR"
#if [ ! -f data/miiflask.db ]; then
#  echo "Database file not found. Initializing database..."
#  python dbinit.py 
#fi
sh init.sh "$DATA_DIR"

echo "Starting Gunicorn..."
gunicorn --bind 0.0.0.0:8000 -w 1 wsgi
