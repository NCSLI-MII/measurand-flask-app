#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import logging
from urllib.parse import urlparse

from sqlalchemy.orm.base import instance_state
from flask import (render_template,
                   redirect,
                   request,
                   url_for,
                   flash
                   )



from miiflask.flask.app import app
from miiflask.flask.app import db
#from miiflask.mappers.taxonomy_mapper import dicttoxml_taxonomy, getTaxonDict
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper_v2 import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper

import pprint as mpprint
import json
import graphviz
import base64







@app.route("/initialize")
def initialize():

    parms = {
            "measurands": "../../resources/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
            "mlayer": "../../resources/m-layer",
            "kcdb": "../../resources/kcdb",
            "api_mlayer": "https://dr49upesmsuw0.cloudfront.net",
            "use_api": False,
            "use_cmc_api": False,
            "update_resources": False,
            "kcdb_cmc_data": "kcdb_cmc_canada.json",
            "kcdb_cmc_api_countries": ["CA"],
        }

    mapper = MlayerMapper(db.session, parms)
    mapper.getCollections()
    mapper.getScaleAspectAssociations()

    miimapper = TaxonomyMapper(db.session, parms)
    miimapper.extractTaxonomy()
    miimapper.loadTaxonomy()

    kcdbmapper = KcdbMapper(db.session, parms)
    kcdbmapper.loadServices()
    
    db.session.commit()
    return redirect(url_for('index'))


