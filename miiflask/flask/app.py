#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# This is vanilla SQLAlchemy declarative base
# 
from miiflask.flask.db import Base

from miiflask.flask.model import (
    Measurand,
    Aspect,
    Unit,
    Scale,
    KcdbCmc,
    KcdbQuantity,
    KcdbService,
    Domain
)


app = Flask(__name__)

# TBD
# Configure with environment variables
# FLASK_APP = app
# FLASK_ENV = testing
# FLASK_ENV = development

app.config.from_object('miiflask.flask.config.TestingConfig')

# Difference between flask sqlalchemy declarative base and vanilla sqlalchemcy
# Ability to use query.Model
# Stackoverflow 22698478 

# The following model_class is customizing the flask db.Model
# Which is there to include the metadata object in flask.db
# Flask is just used to connect to db, not create db
db = SQLAlchemy(app, model_class=Base)

print("Running the App and using views")

# App needs to be configured before importing views

from miiflask.flask.views import (
        MeasurandView,
        CMCView,
        MyModelView
        )

admin = Admin(app, name="qms", template_mode="bootstrap3")
admin.add_view(ModelView(Domain, db.session))
admin.add_view(MyModelView(Aspect, db.session))
admin.add_view(MyModelView(Scale, db.session))
admin.add_view(MyModelView(Unit, db.session))
admin.add_view(MeasurandView(Measurand, db.session))
admin.add_view(MyModelView(KcdbService, db.session))
admin.add_view(MyModelView(KcdbQuantity, db.session))
admin.add_view(CMCView(KcdbCmc, db.session))

