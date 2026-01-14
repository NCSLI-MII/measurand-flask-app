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


def main():
    
    parms = {
        "path": "var",
        "database": "var/miiflask.db",
        "usertables": "/tmp/miiflask/tables_",
        "measurands": "resources/repo/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
        "mlayer": "resources/repo/m-layer/source/json",
        "kcdb": "resources/kcdb",
        "kcdb_cmc_data": "kcdb_cmc_physics.json",
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

        #kcdbmapper = KcdbMapper(session, parms)
        #kcdbmapper.loadServices()
        session.commit()
        session.close()


if __name__ == "__main__":
    engine = create_engine(
        "sqlite:///" + os.path.abspath("var/miiflask.db")
    )

    bind_engine(engine)
    main()
