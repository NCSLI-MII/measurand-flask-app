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


def main(data_dir, db_path):
   
    print(f"Initialize db with APP DATA DIR {data_dir}")
    print(f"Database path {db_path}")
    parms = {
        "path": data_dir,
        "database": db_path,
        "usertables": os.path.join(data_dir,"tables_"),
        "measurands": "resources/repo/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
        "mlayer": "resources/repo/m-layer/source/json",
        "kcdb": "resources/kcdb",
        "kcdb_cmc_data": "kcdb_cmc_physics_em_taxons_workshop_2024_demo.json",
        "kcdb_cmc_api_countries": ["CA"],
        "api_mlayer": "https://api.mlayer.org",
        "use_api": False,
        "use_cmc_api": False,
        "update_resources": False
    }

    with Session(engine) as session:
        mapper = MlayerMapper(session, parms)
        mapper.getCollections()
        mapper.getScaleAspectAssociations()

        miimapper = TaxonomyMapper(session, parms)
        miimapper.extractTaxonomy_v2()
        miimapper.loadTaxonomy()
        miimapper.roundtrip()

        kcdbmapper = KcdbMapper(session, parms)
        kcdbmapper.loadServices()
        session.commit()
        session.close()


if __name__ == "__main__":
    print(sys.argv[1])
    data_dir = os.path.abspath(sys.argv[1])
    db_path = os.path.join(data_dir, "miiflask.db")
    print(db_path)
    engine = create_engine(
        f"sqlite:///{db_path}" 
    )

    bind_engine(engine)
    main(data_dir, db_path)
