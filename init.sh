#! /bin/sh
#
# init.sh
# Copyright (C) 2026 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.
#
set -e

NAME1=measurand-taxonomy
VERSION1=0.2.0-beta
NAME2=m-layer
VERSION2=0.3.0-beta

FILENAME1="$NAME1-$VERSION1.tar.gz"
FILENAME2="$NAME2-$VERSION2.tar.gz"

URL1="https://github.com/NCSLI-MII/$NAME1/archive/refs/tags/v$VERSION1.tar.gz"
URL2="https://github.com/NCSLI-MII/$NAME2/archive/refs/tags/v$VERSION2.tar.gz"

TMP_DIR=$(mktemp -d)
INSTALL_PREFIX=resources/repo

if [ -z "$1" ]; then
    echo "No input directory provided, exiting"
    exit 1
fi
DATA_DIR="$1"

echo "Using data directory $DATA_DIR"
echo "$NAME1 Url: $URL1"
echo "$NAME2 Url: $URL2"

mkdir -p "$DATA_DIR"

if [ "$2" = true ]; then
    echo "Removing $DATA_DIR"
    rm -rf "$DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

echo "Data directory $DATA_DIR contents:"
ls -la "$DATA_DIR"

rm -rf "$INSTALL_PREFIX"
mkdir -p "$INSTALL_PREFIX"


# Initialize db
if [ ! -f "$DATA_DIR"/miiflask.db ]; then
   
  echo "Database file not found. Checking out resources..."
  # Checkout resources
  wget -O "$TMP_DIR/$FILENAME1" "$URL1" 
  wget -O "$TMP_DIR/$FILENAME2" "$URL2" 

  tar xzf "$TMP_DIR/$FILENAME1" -C "$INSTALL_PREFIX" 
  tar xzf "$TMP_DIR/$FILENAME2" -C "$INSTALL_PREFIX" 
  mv "$PWD/$INSTALL_PREFIX/$NAME1-$VERSION1/" "$PWD/$INSTALL_PREFIX/$NAME1" 
  mv "$PWD/$INSTALL_PREFIX/$NAME2-$VERSION2/" "$PWD/$INSTALL_PREFIX/$NAME2" 
  echo "Initializing database..."
  python dbinit.py "$DATA_DIR" 
fi

# Clean up
rm -r "$TMP_DIR"
