#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2024 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper


class InitializeDbTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite://")
        bind_engine(self.engine)

    def tearDown(self):
        pass

    def test_initdb(self):
        parms = {
                "measurands": "resources/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
                "mlayer": "resources/m-layer",
                "kcdb": "resources/kcdb",
                "api_mlayer": "https://dr49upesmsuw0.cloudfront.net",
                "use_api": False,
                "use_cmc_api": False,
                "update_resources": False
            }
        with Session(self.engine) as session:
            mapper = MlayerMapper(session, parms)
            mapper.getCollections()
            mapper.getScaleDimension()
            mapper.getScaleAspectAssociations()

            miimapper = TaxonomyMapper(session, parms)
            miimapper.extractTaxonomy()
            miimapper.loadTaxonomy()

            kcdbmapper = KcdbMapper(session, parms)
            kcdbmapper.loadServices()


if __name__ == '__main__':
    unittest.main()
