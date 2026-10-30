#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""
Define the SQLAlchemy base
Stackoverflow 51106264
Modified based on Opus AI
Ensures no module level session, 1 session scoped per flask app
"""
# db.py
from sqlalchemy import MetaData, select
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from flask import abort, make_response, current_app

metadata_obj = MetaData()
Base = declarative_base(metadata=metadata_obj)


def create_schema(engine):
    """Create all tables. Safe to call from any context (Flask or CLI)."""
    Base.metadata.create_all(engine)


def attach_session(app, engine):
    """Attach a per-app scoped_session. Call from Flask's create_app()."""
    app.extensions.setdefault("miiflask", {})
    app.extensions["miiflask"]["engine"] = engine
    app.extensions["miiflask"]["session_factory"] = scoped_session(
        sessionmaker(bind=engine, future=True)
    )


def get_session():
    """Scoped session for the current Flask app."""
    return current_app.extensions["miiflask"]["session_factory"]


def remove_session():
    factory = current_app.extensions.get("miiflask", {}).get("session_factory")
    if factory is not None:
        factory.remove()


def get_or_404(model, id):
    obj = get_session().get(model, id)
    if obj is None:
        abort(404)
    return obj


def obj_serialize_json(model, model_schema, id):
    obj = get_or_404(model, id)
    schema = model_schema.dumps(obj, indent=2)
    response = make_response(schema)
    response.mimetype = "application/json"
    return response


def objs_serialize_json(model, model_schema):
    objs = get_session().scalars(select(model)).all()
    if objs is None:
        abort(404)
    schemas = model_schema.dumps(objs, indent=2)
    response = make_response(schemas)
    response.mimetype = "application/json"
    return response

