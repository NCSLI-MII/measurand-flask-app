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
from sqlalchemy import ForeignKey, Column, Integer, String, Table, Text, Enum
from sqlalchemy.orm import relationship

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

# Managing SQLAlchemy model outside of Flask
# stackoverflow 28789063
# github/flask-sqlalchemy issue "Manage external declarative bases"
#
# M-Layer Model
scaleaspect_table = Table(
    "scaleaspect_table",
    Base.metadata,
    Column("scale_id", ForeignKey("scale_table.id"), primary_key=True),
    Column("aspect_id", ForeignKey("quantitykind_table.id"), primary_key=True),
)


# Populate the QuantityKind table from M-Layer Aspects
class QuantityKind(Base):
    # QuantityKind will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "quantitykind_table"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50))
    uid_name = Column(String(50))
    name = Column(String(50))
    scales = relationship(
        "Scale", secondary=scaleaspect_table, back_populates="aspects"
    )

    def __str__(self):
        return self.name


class Scale(Base):
    __tablename__ = "scale_table"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50))
    uid_name = Column(String(50))
    scale_type = Column(
        Enum("ratio", "interval", "bounded", "ordinal", "nominal"),
        nullable=False,
    )
    reference = Column(String(50))
    aspects = relationship(
        "QuantityKind", secondary=scaleaspect_table, back_populates="scales"
    )

    def __str__(self):
        return self.uid_name


class Reference(Base):
    __tablename__ = "reference_table"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50))
    uid_name = Column(String(50))
    name = Column(String(50))

    # ucum = relationship("UCUM")
    # qudt = relationship("QUDT")
    # system = relationship("System")
    # dimensions = Column(String(10))
    # prefix
    def __str__(self):
        return self.name


# MII Taxonomy Model
# Attempt to model MII Taxon
# One-to-one NRC Service to Measurand (CMC)
# Measurands are unique but the taxon does not ensure uniqueness
# Measurands may have same taxon but different parameters
class Measurand(Base):
    __tablename__ = "measurand"
    id = Column(Integer, primary_key=True, index=True)
    taxon_id = Column(Integer, ForeignKey("taxon.id"))
    name = Column(String(50))
    quantity_id = Column(
        String(50), ForeignKey("quantitykind_table.id"), nullable=True
    )  # One-to-one
    taxon = relationship("Taxon", back_populates="measurand")
    quantitykind = relationship("QuantityKind")
    # One to many parameters
    parameters = relationship("Parameter", back_populates="measurand")

    def __str__(self):
        return self.name


class Parameter(Base):
    # many-to-one
    # Reference a quantity for each parameter
    __tablename__ = "parameter"
    id = Column(Integer, primary_key=True, index=True)
    measurand_id = Column(Integer, ForeignKey("measurand.id"))
    measurand = relationship("Measurand", back_populates="parameters")
    name = Column(String(50))
    quantity_id = Column(
        String(50), ForeignKey("quantitykind_table.id"), nullable=True
    )  # One-to-one
    quantitykind = relationship("QuantityKind")

    def __str__(self):
        return self.name


class Taxon(Base):
    __tablename__ = "taxon"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(50)
    )  # Name should be constructor from init with Taxon attributes following BNF grammar
    process = Column(String(10))  # Source | Measure
    quantity_id = Column(
        String(50), ForeignKey("quantitykind_table.id"), nullable=True
    )  # One-to-one
    quantitykind = relationship("QuantityKind")
    qualifier = Column(String(50))
    # Individual taxon may be used in many measurands
    # With bakc_populates if no id for taxon is given
    # SQLAlchemy will create a new one
    measurand = relationship("Measurand", back_populates="taxon")
    discipline_id = Column(
        Integer, ForeignKey("discipline_table.id"), nullable=True
    )
    discipline = relationship("Discipline", back_populates="taxon")

    def __str__(self):
        return self.name


# Traditional CC areas and team labels
# Domains should be one to many disciplines


class Domain(Base):
    __tablename__ = "domain_table"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(10))
    title = Column(String(50))
    description = Column(Text)
    title_fr = Column(String(50))
    description_fr = Column(Text)

    def __str__(self):
        return self.label




# Disciplines should be one to many aspects or quantity kinds in taxonomy
class Discipline(Base):
    __tablename__ = "discipline_table"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50))
    taxon = relationship("Taxon", back_populates="discipline")




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
# KCDB classification system differs for the different domains of Physics, Ionising Radiation and Biology/Chemistry
# NRC has a separate (but similar) way to classify their services which is used on the website to organise human-readable html
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
    Column("kcdbcmc_id", ForeignKey("kcdbcmc_table.id"), primary_key=True),
    Column(
        "classifiertag_id",
        ForeignKey("classifiertag_table.id"),
        primary_key=True,
    ),
)


# MRA SIM Calibration and Measurement Capabilities entries in the KCDB
class KcdbCmc(Base):
    __tablename__ = "kcdbcmc_table"
    id = Column(String(50), primary_key=True)
    tags = relationship(
        "ClassifierTag", secondary=kcdb_classifier_map, backref="kcdbcmcs"
    )
    # parents = relationship("Parent", secondary=association_table, back_populates="children")
    # parent_id = Column(String(50), ForeignKey("parent_table.id"))
    # parents = relationship("Parent", back_populates='discipline') # bidirectional relationship

    def __str__(self):
        return self.id


class KcdbQuantity(Base):
    __tablename__ = "kcdb_quantity"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))

class KcdbService(Base):
    __tablename__ = "kcdb_service"
    id = Column(String(50), primary_key=True)
    area_id = Column(String(10))
    area = Column(String(50))
    branch_id = Column(String(20))
    branch = Column(String(50))
    service = Column(String(200))
    subservice = Column(String(200))

# KCDB quantityValue description
# Requires mapper from KCDB quantity Value to quantity kind
class QuantityValue(Base):
    # QuantityKind will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "quantityvalue_table"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    quantity_kind = Column(
        String(50), ForeignKey("quantitykind_table.name"), nullable=True
    )
    quantitykind = relationship("QuantityKind")


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

class KcdbQuantitySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbQuantity
        include_relationships = True
        load_instance = True

class KcdbServiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbService
        include_relationships = True
        load_instance = True

class ScaleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Scale
        include_relationships = True
        load_instance = True


class QuantityKindSchema(SQLAlchemyAutoSchema):
    scales = Nested(ScaleSchema, many=True)

    class Meta:
        model = QuantityKind
        include_relationships = True
        load_instance = True


class ReferenceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Reference
        include_relationships = True
        load_instance = True


class ParameterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Parameter
        include_relationships = True
        load_instance = True


class MeasurandSchema(SQLAlchemyAutoSchema):
    parameters = Nested(ParameterSchema, many=True)

    class Meta:
        model = Measurand
        include_relatiohsips = True
        load_instance = True


class TaxonSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Taxon
        include_relationships = True
        load_instance = True


class DisciplineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Discipline
        include_relationships = True
        load_instance = True
