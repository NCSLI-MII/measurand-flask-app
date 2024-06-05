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

from flask import Flask
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView

# This is vanilla SQLAlchemy declarative base

from miiflask.flask.db import Base, bind_engine

from miiflask.flask.config import (
        TestingConfig, 
        DevelopmentConfig,
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

print('Creating app ', __name__)


class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('index')


def create_app(config=TestingConfig):
    app = Flask(__name__)

# TBD
# Configure with environment variables
# FLASK_APP = app
# FLASK_ENV = testing
# FLASK_ENV = development

    app.config.from_object(config)
    return app

# Difference between flask sqlalchemy declarative base and vanilla sqlalchemcy
# Ability to use query.Model
# Stackoverflow 22698478 

# The following model_class is customizing the flask db.Model
# Which is there to include the metadata object in flask.db
# Flask is just used to connect to db, not create db

env = environ['FLASK_ENV']
print('ENVIRONMENT: ', env)
if(env == 'testing'):
    app = create_app()
elif(env=='development'):
    app = create_app(DevelopmentConfig)
elif(env == 'production'):
    app = create_app(ProductionConfig)
else:
    print("App not configured")

print('Testing ', app.config.get('TESTING'))
print('DEBUG ', app.config.get('DEBUG'))
print('URI ', app.config.get('SQLALCHEMY_DATABASE_URI')) 
if app.config.get('TESTING') is True: 
    print("TESTING: create db for in-memory")
    db = SQLAlchemy(app, model_class=Base)
    with app.app_context():
        db.create_all() 
else:    
    db = SQLAlchemy(app, model_class=Base)

print("Running the App and using views")

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

admin = Admin(app, name="qms", template_mode="bootstrap3")
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
admin.add_view(MeasurandView(Measurand, db.session, category="Measurand"))
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



