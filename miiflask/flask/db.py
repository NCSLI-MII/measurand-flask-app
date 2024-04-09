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
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_schemadisplay import create_schema_graph

metadata_obj = MetaData()
Base = declarative_base(metadata=metadata_obj)
Session = sessionmaker()


def bind_engine(engine):
    Base.metadata.bind = engine
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    graph = create_schema_graph(
        metadata=metadata_obj,
        show_datatypes=False,
        show_indexes=False,
        rankdir="LR",
        concentrate=False,
    )
    # graph.write_png("taxonomyschema.png")
