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

class Administrative(Base):
    __tablename__ = "administrative"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    mii_comment: Mapped[Optional[str]] = mapped_column(UnicodeText)



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

# MRA SIM Calibration and Measurement Capabilities entries in the KCDB
class KcdbCmc(Base):
    __tablename__ = "kcdbcmc"
    id: Mapped[int] = mapped_column(primary_key=True)
    kcdbCode: Mapped[str] = mapped_column(String(50))
    baseUnit: Mapped[str] = mapped_column(UnicodeText)
    uncertaintyBaseUnit: Mapped[str] = mapped_column(UnicodeText)
    internationalStandard: Mapped[Optional[str]] = mapped_column(UnicodeText)
    comments: Mapped[str] = mapped_column(UnicodeText)

    area_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbarea.id"))
    area: Mapped['KcdbArea'] = relationship()

    branch_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbbranch.id"))
    branch: Mapped['KcdbBranch'] = relationship()

    service_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbservice.id"))
    service: Mapped['KcdbService'] = relationship()

    subservice_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbsubservice.id"))
    subservice: Mapped['KcdbSubservice'] = relationship()

    individualservice_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbindividualservice.id"))
    individualservice: Mapped['KcdbIndividualService'] = relationship()

    quantity_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbquantity.id"))
    quantity: Mapped['KcdbQuantity'] = relationship()

    instrument_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbinstrument.id"))
    instrument: Mapped["KcdbInstrument"] = relationship()

    instrumentmethod_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbinstrumentmethod.id"))
    instrumentmethod: Mapped["KcdbInstrumentMethod"] = relationship()

    parameters: Mapped[list['KcdbParameter']] = \
        relationship(back_populates='kcdbcmc')

    tags: Mapped[list['ClassifierTag']] = \
        relationship(secondary=kcdb_classifier_map, backref="kcdbcmcs")

    measurands: Mapped[list['MeasurandTaxon']] = \
        relationship(secondary=kcdb_measurand_map, backref="kcdbcmcs")
    # parents = relationship("Parent", secondary=association_table, back_populates="children")
    # parent_id = Column(String(50), ForeignKey("parent_table.id"))
    # parents = relationship("Parent", back_populates='discipline') # bidirectional relationship

    def __str__(self):
        return f'{self.kcdbCode}'


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


class KcdbParameter(Base):
    __tablename__ = "kcdbparameter"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(UnicodeText)
    value = Column(UnicodeText)
    kcdbcmc = relationship('KcdbCmc', back_populates='parameters')
    kcdbcmc_id = Column(Integer, ForeignKey('kcdbcmc.id'))

    def __str__(self):
        return f'name: {self.name} value: {self.value}'


class KcdbInstrument(Base):
    __tablename__ = "kcdbinstrument"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbInstrumentMethod(Base):
    __tablename__ = "kcdbinstrumentmethod"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbQuantity(Base):
    __tablename__ = "kcdbquantity"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbArea(Base):
    __tablename__ = "kcdbarea"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbBranch(Base):
    __tablename__ = "kcdbbranch"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'

    
class KcdbService(Base):
    __tablename__ = "kcdbservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbSubservice(Base):
    __tablename__ = "kcdbsubservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbIndividualService(Base):
    __tablename__ = "kcdbindividualservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'

# Deprecated


class KcdbServiceClass(Base):
    __tablename__ = "kcdbserviceclass"
    id = Column(String(50), primary_key=True)
    area_id = Column(String(10))
    area = Column(String(50))
    branch_id = Column(String(20))
    branch = Column(String(50))
    service = Column(String(200))
    subservice = Column(String(200))
    individualservice = Column(String(200))


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


class KcdbParameterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbParameter
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbInstrumentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbInstrument
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbInstrumentMethodSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbInstrumentMethod
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbAreaSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbArea
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbBranchSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbBranch
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbServiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbService
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbSubserviceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbSubservice
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbIndividualServiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbIndividualService
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbQuantitySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbQuantity
        include_relationships = True
        load_instance = True
        ordered = True


class KcdbServiceClassSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbServiceClass
        include_relationships = True
        load_instance = True
        ordered = True




class KcdbCmcSchema(SQLAlchemyAutoSchema):
    #measurands = Nested(MeasurandSchema, many=True, only=('name',),)
    area = Nested(KcdbAreaSchema)
    branch = Nested(KcdbBranchSchema)
    service = Nested(KcdbServiceSchema)
    subservice = Nested(KcdbSubserviceSchema)
    individualservice = Nested(KcdbIndividualServiceSchema)
    instrument = Nested(KcdbInstrumentSchema)
    instrumentmethod = Nested(KcdbInstrumentMethodSchema)
    quantity = Nested(KcdbQuantitySchema)
    parameters = Nested(KcdbParameterSchema, many=True)

    class Meta:
        model = KcdbCmc
        include_relationships = True
        load_instance = True
        ordered = True
