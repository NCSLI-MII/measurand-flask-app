#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import os
import argparse

from sqlalchemy import create_engine

from flask import Flask
from flask import url_for
from flask_sqlalchemy import SQLAlchemy

# This is vanilla SQLAlchemy declarative base

from miiflask.flask.db import Base, bind_engine, Session
from miiflask.flask.admin.init import init_admin
from miiflask.flask.main.init import bp as main_bp 
from miiflask.flask.api.init import bp as api_bp 
from miiflask.flask.config import (
        TestingConfig, 
        DevelopmentConfig,
        DemoConfig,
        ProductionConfig
        )

print('Creating app ', __name__)

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    print(f"Creating app with DB Path {config.SQLALCHEMY_DATABASE_URI}")
    print("Database path exists:", os.path.exists(config.DB_PATH))
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, future=True)
    bind_engine(engine)
    init_admin(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        Session.remove()


    return app

if __name__ == "miiflask.flask.app":

    app = create_app(ProductionConfig)
    print("Running the App and using views")
    

    #with app.app_context():
    #    db = SQLAlchemy(app, model_class=Base)
        # App needs to be configured before importing views




