#! /bin/sh
#
# init.sh
# Copyright (C) 2026 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.
#


#!/bin/bash

files=$(ls)
echo "$files"
# Create data directory
# Checkout resources
# Initialize db
if [ ! -f data/miiflask.db ]; then
  echo "Database file not found. Initializing database..."
  python dbinit_v3.py 
fi

