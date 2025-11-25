#! /bin/sh
#
# setup.sh
# Copyright (C) 2025 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.
#


if [ -z "$1" ]; then
    echo "Usage: $0 <directory_path>"
    exit 1
fi

DIR_PATH="$1"

echo $DIR_PATH

# Check if path exists
if [ ! -d "$DIR_PATH" ]; then
    mkdir "$DIR_PATH"
else
    echo "Directory $DIR_PATH exists, clean-up"
    rm -rf "$DIR_PATH"
    mkdir "$DIR_PATH"
fi

echo "Setting up running directory"


ls -l "$DIR_PATH"
mkdir -p $DIR_PATH/resources/repo

git clone --depth=1 https://github.com/NCSLI-MII/measurand-taxonomy.git $DIR_PATH/resources/repo/measurand-taxonomy
git clone --depth=1 https://github.com/NCSLI-MII/m-layer.git $DIR_PATH/resources/repo/m-layer
python dbinit_test.py -d -p "$DIR_PATH" 
# gunicorn -w 1 'miiflask.flask.app:app'
