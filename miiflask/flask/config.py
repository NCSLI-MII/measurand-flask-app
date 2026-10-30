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




class Config:
    DEBUG = False
    TESTING = False
    DB_PATH = None
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FLASK_ADMIN_SWATCH = "cerulean"
    SECRET_KEY = "secret"
    VERSION = "0.11.3"


class TestingConfig(Config):
    TESTING = True
    LOG_LEVEL = "DEBUG"
    # SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/miiflask/miiflask.db"


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/miiflask/miiflask.db"


class DemoConfig(Config):
    PRODUCTION = True
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/miiflask/miiflask_workshop_2024_demo.db"

class ProductionConfig(Config):
    PRODUCTION = True
    LOG_LEVEL = "INFO"
    APP_DATA_DIR = os.getenv("APP_DATA_DIR", "/var/lib/miiflask")
    DB_PATH = os.path.join(APP_DATA_DIR, "miiflask.db") 
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DB_PATH

