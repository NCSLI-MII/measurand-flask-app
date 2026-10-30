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
import logging

from sqlalchemy import create_engine

from flask import Flask
from flask import url_for

# This is vanilla SQLAlchemy declarative base

from miiflask.flask.db import create_schema, attach_session, remove_session
from miiflask.flask.admin.init import init_admin
from miiflask.flask.main.init import bp as main_bp 
from miiflask.flask.api.init import bp as api_bp 
from miiflask.flask.config import (
        TestingConfig, 
        DevelopmentConfig,
        DemoConfig,
        ProductionConfig
        )

log = logging.getLogger(__name__)

CONFIG_MAP = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "test": TestingConfig,
}

def _select_config():
    name = os.getenv("FLASK_CONFIG", "production").lower()
    try:
        return CONFIG_MAP[name]
    except KeyError:
        raise RuntimeError(
            f"Unknown FLASK_CONFIG={name!r}. "
            f"Expected one of: {', '.join(CONFIG_MAP)}"
        )

print('Creating app ', __name__)

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(_select_config())
    log.info("Creating app with DB URI %s", config.SQLALCHEMY_DATABASE_URI)

    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, future=True)
    create_schema(engine)
    attach_session(app, engine)

    init_admin(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        remove_session()

    return app


if __name__ == "miiflask.flask.app":

    app = create_app(_select_config())
    print("Running the App and using views")
    

    #with app.app_context():
    #    db = SQLAlchemy(app, model_class=Base)
        # App needs to be configured before importing views




