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
"""
from sqlalchemy import MetaData, select
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from flask import abort, make_response
# from sqlalchemy.ext.declarative import declarative_base

metadata_obj = MetaData()
Base = declarative_base(metadata=metadata_obj)
Session = scoped_session(sessionmaker())

def bind_engine(engine):
    metadata_obj.bind = engine
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)

def get_session():
    return Session()

def get_or_404(model, id):
    session = get_session()
    obj = session.get(model, id)
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
