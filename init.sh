#! /bin/sh
#
# init.sh
# Copyright (C) 2026 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.
#


#!/bin/bash

NAME1=measurand-taxonomy
VERSION1=0.2.0-beta
NAME2=m-layer
VERSION2=0.3.0-beta
FILENAME1="$NAME1-$VERSION1.tar.gz"
FILENAME2="$NAME2-$VERSION2.tar.gz"
URL1="https://github.com/NCSLI-MII/$NAME1/archive/refs/tags/v$VERSION1.tar.gz"
URL2="https://github.com/NCSLI-MII/$NAME2/archive/refs/tags//v$VERSION2.tar.gz"
TMP_DIR=$(mktemp -d)
INSTALL_PREFIX=resources/repo
files=$(ls)

if [ -z "$1" ]; then
    echo "No input directory provided, exiting"
    exit 1
else
    DATA_DIR="$1"
fi

if [ -z "$2" ]; then
    if [[ "$2" == "true" ]]; then
        if [ -d $DATA_DIR]; then
            echo "Removing $DATA_DIR"
            rm -rf $DATA_DIR
        fi
    fi
fi

echo "$files"
echo "$URL1"
echo "$URL2"
echo "$DATA_DIR"
# Symlink data directory
if [ -d data ]; then
    rm -rf data
fi

if [ ! -d "$DATA_DIR" ]; then
    mkdir -p $DATA_DIR
fi

ln -s $DATA_DIR data

if [ -d $INSTALL_PREFIX ]; then
    rm -rf $INSTALL_PREFIX
fi
mkdir -p $INSTALL_PREFIX

files=$(ls $INSTALL_PREFIX)
echo "$files"

# Initialize db
if [ ! -f data/miiflask.db ]; then
  echo "Database file not found. Checking out resources..."
  # Checkout resources
  wget -O "$TMP_DIR/$FILENAME1" "$URL1" 
  wget -O "$TMP_DIR/$FILENAME2" "$URL2" 

  tar xzvf "$TMP_DIR/$FILENAME1" -C "$INSTALL_PREFIX" 
  tar xzvf "$TMP_DIR/$FILENAME2" -C "$INSTALL_PREFIX" 
  mv "$PWD/$INSTALL_PREFIX/$NAME1-$VERSION1/" "$PWD/$INSTALL_PREFIX/$NAME1" 
  mv "$PWD/$INSTALL_PREFIX/$NAME2-$VERSION2/" "$PWD/$INSTALL_PREFIX/$NAME2" 
  echo "Initializing database..."
  python dbinit_v3.py 
fi

