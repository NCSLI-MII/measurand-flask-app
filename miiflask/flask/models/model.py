#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""
SQLAlchemy Data Model
"""
from miiflask.flask.db import Base
from sqlalchemy import (ForeignKey,
                        Column,
                        Integer,
                        String,
                        Table,
                        Text,
                        UnicodeText,
                        Boolean,
                        Float,
                        )
from sqlalchemy.orm import relationship, Mapped, mapped_column

from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

from typing import Optional
import re

# ##########################################
# Managing SQLAlchemy model outside of Flask
# stackoverflow 28789063
# github/flask-sqlalchemy issue "Manage external declarative bases"
#
# Use Declarative mapping styles with type hints
# https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html
# Stackoverflow explanation
# https://stackoverflow.com/questions/76498857/what-is-the-difference-between-mapped-column-and-column-in-sqlalchemy
#
##############################################
# Administrative Model
# Contains general details of the application and data model
# License, comments, etc..




class Node(Base):
    __tablename__ = 'node'

    id: Mapped[int] = mapped_column(String(50), primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('node.id'))
    children: Mapped[list['Node']] = relationship(back_populates='parent',
                                                  remote_side=[id])
    parent: Mapped['Node'] = relationship(back_populates='children')





# Parent table represents an NRC service, index is NRC Service Code
# Children are KCDB codes (or complete KCDB CMC data)
# Seperate tables for domain labels and quantity kinds
# Quantity kinds to be replaced by MII Taxon
# MII Taxon quantity kind will be an M-layer identifier for Aspect
# Complete table may include the NRC Service Code, MII Taxon and Aspect id
# along with the data we want to store for each Service

###############################################################
# Classification mappings
# Need a way to store and map existing classifications or "tags"
# NRC and KCDB describe services and CMCs with various "tags"
# KCDB classification system differs for the different domains of Physics,
# Ionising Radiation and Biology/Chemistry
# NRC has a separate (but similar) way to classify their services
# which is used on the website to organise human-readable html
#
# The measurands impose a structure with a unique and controlled taxon name
# Use a third normal form with an adjacency table to map services, CMCs and measurands to tags
# Allow us to consume any tag and map to any object
# object table
# tag table
# object-tag map - single adjacency table will have problems with foreign keys unless all tables have GUID
# Described as Toxi solution, see http://howto/philippkeller/2005/04/24/Tags-Database-schemas
class ClassifierTag(Base):
    __tablename__ = "classifiertag_table"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    type = Column(String(50))

    def __str__(self):
        return self.name


# May require multiple association tables (tag maps)
# If Taxon qualitfiers are stored as well
kcdb_classifier_map = Table(
    "kcdb_classifier_map",
    Base.metadata,
    Column("kcdbcmc_id", ForeignKey("kcdbcmc.id"), primary_key=True),
    Column(
        "classifiertag_id",
        ForeignKey("classifiertag_table.id"),
        primary_key=True,
    ),
)

kcdb_measurand_map = Table(
    "kcdb_measurand_map",
    Base.metadata,
    Column("kcdbcmc_id",
           ForeignKey("kcdbcmc.id"),
           primary_key=True),
    Column(
        "measurandtaxon_id",
        ForeignKey("measurandtaxon.id"),
        primary_key=True,
    ),
)


class Domain(Base):
    # Traditional CC areas and team labels
    # Domains should be one to many disciplines
    __tablename__ = "domain"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(10))
    title = Column(String(50))
    description = Column(Text)
    title_fr = Column(String(50))
    description_fr = Column(Text)

    def __str__(self):
        return f'{self.label}'




# KCDB quantityValue description
# Requires mapper from KCDB quantity Value to quantity kind
class QuantityValue(Base):
    # QuantityKind will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "quantityvalue_table"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    #aspect = Column(
    #    String(50), ForeignKey("aspect_table.id"), nullable=True
    #)
    #aspect = relationship("Aspect")


###############################################################

# Self-referential table
# Required for linking
# Documentary traceability mapping - calibration records
# Representation mapping - m-later ScaleAspect associations
# docs/sqlalchemy.org/.../orm/join_conditions.html#self-referential-many-to_many
#
# node-to-node = Table("node-to-node",
#        Base.metadata,
#        Column("left_node_id", Integer, ForeignKey("node.id"), primary_key=True),
#        Column("right_node_id", Integer, ForeignKey("node.id"), primary_key=True))
#
# class Node(Base):
#    __tablename__ = "node"
#    id = Column(Integer, primary_key=True)
#    label = Column(String),
#    right_nodes = relationship("Node",
#            secondary=node-to-node,
#            primaryjoin=id==node-to-node.c.left_node_id,
#            secondaryjoin=id==node-to-node.c.right_node_id,
#            backref="left_nodes")
#

# Generate marshmallow schemas


