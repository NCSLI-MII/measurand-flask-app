#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine, Base
from miiflask.flask import model
engine = create_engine('sqlite://')
bind_engine(engine)
for table in Base.metadata.sorted_tables:
    print(table)
    print(CreateTable(table).compile(engine))

