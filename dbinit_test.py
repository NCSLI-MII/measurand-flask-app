#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper_v2 import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper


def main(parms):
    with Session(engine) as session:
        mapper = MlayerMapper(session, parms)
        mapper.getCollections()
        mapper.getScaleAspectAssociations()

        miimapper = TaxonomyMapper(session, parms)
        miimapper.extractTaxonomy_v2()
        miimapper.loadTaxonomy()
        miimapper.roundtrip()

        session.commit()
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--inmemory",
        action=argparse.BooleanOptionalAction,
        help="in-memory database",
    )
    parser.add_argument(
        "-d",
        "--database",
        action=argparse.BooleanOptionalAction,
        help="local database",
    )
    parser.add_argument(
        "-p",
        "--path",
        help="Input path for database and resources",
    )

    args = parser.parse_args()
    print(args)
    parms = {
        "path":args.path,
        "database":args.path+"/miiflask.db",
        "usertables":args.path+"/tables_",
        "measurands": args.path+"/resources/repo/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
        "mlayer": args.path+"/resources/repo/m-layer/source/json",
        "api_mlayer": "https://api.mlayer.org",
        "use_api": False,
        "use_cmc_api": False,
        "update_resources": False
    }
    
    engine = create_engine(
        "sqlite:///" + os.path.abspath(parms["database"])
    )

    bind_engine(engine)
    main(parms)
