#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2025 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper_v2 import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper


class ValidateDbTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite://")
        bind_engine(self.engine)

    def tearDown(self):
        pass

    def test_validate(self):
        parms = {
            "path":"/tmp/miiflask",
            "database":"/tmp/miiflask/miiflask.db",
            "usertables":"/tmp/miiflask/tables_",
            "measurands": "resources/repo/MeasurandTaxonomyCatalog.xml",
            "mlayer": "resources/m-layer",
            "kcdb": "resources/kcdb",
            "kcdb_cmc_data": "kcdb_cmc_physics.json",
            "kcdb_cmc_api_countries": ["CA"],
            "api_mlayer": "https://api.mlayer.org",
            "use_api": False,
            "use_cmc_api": False,
            "update_resources": False
        }
        with Session(self.engine) as session:
            mapper = MlayerMapper(session, parms)
            mapper.getCollections()
            mapper.getScaleAspectAssociations()

            miimapper = TaxonomyMapper(session, parms)
            miimapper.extractTaxonomy_v2()
            miimapper.loadTaxonomy()


if __name__ == '__main__':
    unittest.main()
