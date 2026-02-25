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
        #miimapper.extractTaxonomy()
        miimapper.extractTaxonomy_v2()
        miimapper.loadTaxonomy()
        miimapper.roundtrip()

        #kcdbmapper = KcdbMapper(session, parms)
        #kcdbmapper.loadServices()
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
    parser.add_argument("-p", "--parameters", help="Input json job parameters")
    args = parser.parse_args()
    print(args)
    parms = None
    with Path(args.parameters).resolve().open() as f:
        parms = json.load(f)
    print(parms)
    if "path" in parms.keys():
        if not Path(parms["path"]).resolve().exists():
            Path(parms["path"]).mkdir(parents=True, exist_ok=True)

    if args.inmemory is True:
        engine = create_engine("sqlite://")
    elif args.database is True:
        print("Requires db file path")
        engine = create_engine(
            "sqlite:///" + os.path.abspath(parms["database"])
        )

    bind_engine(engine)
    main(parms)
