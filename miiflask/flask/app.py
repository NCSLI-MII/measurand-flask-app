#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
from os import environ
import argparse

from flask import Flask
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import Bootstrap4Theme

# This is vanilla SQLAlchemy declarative base

from miiflask.flask.db import Base, bind_engine

from miiflask.flask.config import (
        TestingConfig, 
        DevelopmentConfig,
        DemoConfig,
        ProductionConfig
        )

from miiflask.flask.model import (
    Measurand,
    MeasurandTaxon,
    Aspect,
    Unit,
    Scale,
    Parameter,
    KcdbCmc,
    KcdbQuantity,
    KcdbServiceClass,
    KcdbArea,
    KcdbBranch,
    KcdbService,
    KcdbSubservice,
    KcdbIndividualService,
    KcdbInstrument,
    KcdbInstrumentMethod,
    KcdbParameter,
    Domain,
    Conversion,
    Cast,
    Transform,
    Dimension,
    System,
    Prefix
)
app = None
print('Creating app ', __name__)


class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('index')


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    return app

if __name__ == "miiflask.flask.app":

    app = create_app(ProductionConfig)

    print("Running the App and using views")

    with app.app_context():
        db = SQLAlchemy(app, model_class=Base)
        
        # App needs to be configured before importing views

        from miiflask.flask.views import (
                MeasurandView,
                TaxonView,
                MeasurandTaxonView,
                ParameterView,
                CMCView,
                MyModelView,
                KcdbServiceView,
                AspectView,
                ScaleView,
                CastConversionView,
                DimensionView,
                KcdbBranchView
                )

        admin = Admin(app, name="mii", theme=Bootstrap4Theme(swatch="cerulean"))
        admin.add_view(ModelView(Domain, db.session))
        admin.add_view(AspectView(Aspect, db.session, category="Mlayer"))
        admin.add_view(ScaleView(Scale, db.session, category="Mlayer"))
        admin.add_view(MyModelView(Unit, db.session, category="Mlayer"))
        admin.add_view(MyModelView(Prefix, db.session, category="Mlayer"))
        admin.add_view(CastConversionView(Conversion, db.session, category="Mlayer"))
        admin.add_view(CastConversionView(Cast, db.session, category="Mlayer"))
        admin.add_view(MyModelView(Transform, db.session, category="Mlayer"))
        admin.add_view(DimensionView(Dimension, db.session, category="Mlayer"))
        admin.add_view(MyModelView(System, db.session, category="Mlayer"))
        admin.add_view(ParameterView(Parameter, db.session, category="Measurand"))
        # admin.add_view(MeasurandView(Measurand, db.session, category="Measurand"))
        admin.add_view(MeasurandTaxonView(MeasurandTaxon, db.session, category="Measurand"))
        admin.add_view(KcdbServiceView(KcdbServiceClass, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbQuantity, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbArea, db.session, category="KCDB"))
        admin.add_view(KcdbBranchView(KcdbBranch, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbService, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbSubservice, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbIndividualService, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbInstrument, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbInstrumentMethod, db.session, category="KCDB"))
        admin.add_view(MyModelView(KcdbParameter, db.session, category="KCDB"))
        admin.add_view(CMCView(KcdbCmc, db.session, category="KCDB"))
            
        admin.add_link(MainIndexLink(name='Homepage'))



