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

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

from typing import Optional

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

# M-Layer Model
scaleaspect_table = Table(
    "scaleaspect_table",
    Base.metadata,
    Column("scale_id", ForeignKey("scale.id"), primary_key=True),
    Column("aspect_id", ForeignKey("aspect.id"), primary_key=True),
)


class Conversion(Base):
    __tablename__ = "conversion"
    src_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True)
    dst_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True)
    aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                           primary_key=True)
    transform_id: Mapped[str] = mapped_column(ForeignKey("transform.id"))
    parameters: Mapped[str] = mapped_column(UnicodeText)

    src_scale: Mapped['Scale'] = relationship(foreign_keys=[src_scale_id])
    dst_scale: Mapped['Scale'] = relationship(foreign_keys=[dst_scale_id])
    aspect: Mapped['Aspect'] = relationship(foreign_keys=[aspect_id])
    transform: Mapped['Transform'] = relationship(foreign_keys=[transform_id])

    # Investigate whether to use PrimaryKeyConstraint.
    # The PrimaryKeyConstraint object provides
    # explicit access to this constraint,
    # which includes the option of being configured directly:

    def __str__(self):
        return "{}.{}.{}".format(self.src_scale_id,
                                 self.dst_scale_id,
                                 self.aspect_id)


class Cast(Base):
    __tablename__ = "cast"
    src_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True)
    dst_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True)
    src_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                               primary_key=True)
    dst_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                               primary_key=True)
    transform_id: Mapped[str] = mapped_column(ForeignKey("transform.id"))
    parameters: Mapped[str] = mapped_column(UnicodeText)

    src_scale: Mapped['Scale'] = relationship(foreign_keys=[src_scale_id])
    dst_scale: Mapped['Scale'] = relationship(foreign_keys=[dst_scale_id])
    src_aspect: Mapped['Aspect'] = relationship(foreign_keys=[src_aspect_id])
    dst_aspect: Mapped['Aspect'] = relationship(foreign_keys=[dst_aspect_id])
    transform: Mapped['Transform'] = relationship(foreign_keys=[transform_id])

    def __str__(self):
        return "{}.{}.{}.{}".format(self.src_scale_id,
                                    self.src_aspect_id,
                                    self.dst_scale_id,
                                    self.dst_aspect_id)


class System(Base):
    __tablename__ = 'system'
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    ml_name: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(10))
    n: Mapped[Optional[int]] = mapped_column(Integer)
    basis: Mapped[Optional[str]] = mapped_column(String(200))
    reference: Mapped[Optional[str]] = mapped_column(String(200))

    def __str__(self):
        return f'{self.symbol}'


class Dimension(Base):
    __tablename__ = 'dimension'
    id: Mapped[str] = mapped_column(String(10), primary_key=True)

    formal_system_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('system.id'))

    # systematic_scale_id: Mapped[Optional[str]] = \
    #    mapped_column(ForeignKey('scale.id'))

    exponents: Mapped[Optional[str]] = mapped_column(String(40))

    systematic_scales: Mapped[list['Scale']] = \
        relationship(back_populates="system_dimensions")

    formal_system: Mapped['System'] = relationship()

    def __str__(self):
        # SI Brochure dimensions
        # dimQ = T^alphaL^betaM^gammaI^deltaTheta^epsilonN^psiJ^eta
        # m-layer encoding
        # dimQ = M^gammaL^betaT^alphaI^deltaTheta^epsilonN^psiJ^eta
        # Time Length Mass Current Temperature
        # AmountOfSubstance LuminousIntensity
        return f'{self.id}'


class Transform(Base):
    __tablename__ = "transform"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    ml_name: Mapped[str] = mapped_column(String(50))
    py_function: Mapped[Optional[str]] = mapped_column(UnicodeText)
    py_names_in_scope: Mapped[Optional[str]] = mapped_column(UnicodeText)
    comments: Mapped[Optional[str]] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.ml_name}'


# M-Layer Aspect
class Aspect(Base):
    # Aspect will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "aspect"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    ml_name: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[Optional[str]] = mapped_column(String(50))
    reference: Mapped[Optional[str]] = mapped_column(String(200))

    scales: Mapped[list['Scale']] = \
        relationship(secondary=scaleaspect_table, back_populates="aspects")
    # Conversions should be related to the scale,
    # aspect only disambiguates the expression
    # conversions = relationship('Conversion', back_populates='aspect')

    def __str__(self):
        return f'{self.name}'


class Prefix(Base):
    __tablename__ = "prefix"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    ml_name: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(50))
    numerator: Mapped[float] = mapped_column()
    denominator: Mapped[float] = mapped_column()
    reference: Mapped[Optional[str]] = mapped_column(String(200))

    def __str__(self):
        return f'{self.name}'


class Unit(Base):
    __tablename__ = "unit"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    ml_name: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[Optional[str]] = mapped_column(String(50))
    reference: Mapped[Optional[str]] = mapped_column(String(200))

    def __str__(self):
        return f'{self.name}'

    def __unicode__(self):
        return self.name


class Node(Base):
    __tablename__ = 'node'

    id: Mapped[int] = mapped_column(String(50), primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('node.id'))
    children: Mapped[list['Node']] = relationship(back_populates='parent',
                                                  remote_side=[id])
    parent: Mapped['Node'] = relationship(back_populates='children')

# Scale class gives access to all related scale information
# Composite scales reference a root scale
# Self-referencing relation to root_scale only from child using remote_side
# Establishes many-to-one relation
# See https://docs.sqlalchemy.org/en/20/orm/self_referential.html


class Scale(Base):
    __tablename__ = "scale"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)

    ml_name: Mapped[str] = mapped_column(String(50))

    scale_type: Mapped[str] = mapped_column(String(20))

    root_scale_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey('scale.id'))

    root_scale: Mapped['Scale'] = relationship(remote_side=[id])

    prefix_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("prefix.id"))  # One-to-one

    prefix: Mapped['Prefix'] = relationship()

    unit_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("unit.id"))  # One-to-one

    unit: Mapped['Unit'] = relationship()

    system_dimensions_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('dimension.id'))

    system_dimensions: Mapped['Dimension'] = \
        relationship(back_populates="systematic_scales")

    is_systematic: Mapped[Optional[bool]]

    aspects: Mapped[list['Aspect']] = \
        relationship(secondary=scaleaspect_table,
                     back_populates="scales")

    conversions: Mapped[list['Conversion']] = \
        relationship(primaryjoin="(Scale.id == Conversion.src_scale_id)",
                     viewonly=True)

    casts: Mapped[list['Cast']] = \
        relationship(primaryjoin="(Scale.id == Cast.src_scale_id)",
                     viewonly=True)
    # src_scales = relationship('Conversion', back_populates='src_scale')
    # dst_scales = relationship('Conversion', back_populates='dst_scale')

    def __str__(self):
        return f'{self.ml_name}'

    def __unicode__(self):
        return self.ml_name


# MII Taxonomy Model
# Attempt to model MII Taxon
# One-to-one NRC Service to Measurand (CMC)
# Measurands are unique but the taxon does not ensure uniqueness
# Measurands may have same taxon but different parameters
# To resolve this, the canonical definition is defined
# in the MeasurandTaxon class
# User defined instances, Measurands, would inherit from the MeasurandTaxon
# what is required is to map parameters between the two?
# For example, when user defines a CMC and selects the MeasurandTaxon to create
# their Measurand, parameters associated with the MeasurandTaxon are provided
# User needs to remove those not required, but be able to define new parameters
# New parameters need to be added (and approved) to the canonical definition

class MeasurandTaxon(Base):
    __tablename__ = "measurandtaxon"
    id: Mapped[str] = mapped_column(UnicodeText, primary_key=True)
    
    name: Mapped[str] = mapped_column(String(50))

    definition: Mapped[Optional[str]] = mapped_column(UnicodeText)
    
    deprecated: Mapped[bool] 

    replacement: Mapped[str] = mapped_column(String(50))
    
    quantitykind: Mapped[Optional[str]] = mapped_column(String(50))

    aspect_id: Mapped[Optional[str]] = mapped_column(ForeignKey("aspect.id"))

    aspect: Mapped['Aspect'] = relationship(foreign_keys=[aspect_id]) #, primaryjoin=aspect_id == Aspect.id)
    
    processtype: Mapped[str] = mapped_column(String(10))  # Source | Measure
    
    qualifier: Mapped[Optional[str]] = mapped_column(String(50))
    
    result: Mapped[str] = mapped_column(String(50))
    
    result_quantity: Mapped[Optional[str]] = mapped_column(String(50))

    result_aspect_id: Mapped[Optional[str]] = mapped_column(ForeignKey("aspect.id"))

    result_aspect: Mapped['Aspect'] = relationship(foreign_keys=[result_aspect_id]) #, primaryjoin=result_aspect_id == Aspect.id)

    discipline_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("discipline.id"))
    discipline: Mapped['Discipline'] = relationship(back_populates="measurandtaxon")
   
    # One to many parameters
    parameters: Mapped[list['Parameter']] = \
        relationship(back_populates="measurandtaxon")
    
    # One to many parameters
    external_references: Mapped[list['Reference']] = \
        relationship(back_populates="measurandtaxon")

    def __str__(self):
        return f'{self.name}'


class Measurand(Base):
    __tablename__ = "measurand"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    taxon_id: Mapped[str] = mapped_column(ForeignKey("measurandtaxon.id"))

    name: Mapped[str] = mapped_column(String(50))

    # Will be deprecated
    # Result should be replaced by aspect and scale
    result: Mapped[str] = mapped_column(String(50))

    definition: Mapped[Optional[str]] = mapped_column(UnicodeText)
    
    quantitykind: Mapped[Optional[str]] = mapped_column(String(50))

    aspect_id: Mapped[Optional[str]] = mapped_column(ForeignKey("aspect.id"))

    # Reference only to canonical definition
    taxon: Mapped['MeasurandTaxon'] = relationship()
    
    aspect: Mapped['Aspect'] = relationship()
   
    # One to many parameters
    parameters: Mapped[list['Parameter']] = \
        relationship(back_populates="measurand")

    def __str__(self):
        return f'{self.name}'


class Parameter(Base):
    # many-to-one
    # Reference a quantity for each parameter
    __tablename__ = "parameter"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    measurand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("measurand.id"))
    measurand: Mapped['Measurand'] = relationship(back_populates="parameters")
    
    measurandtaxon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("measurandtaxon.id"))
    measurandtaxon: Mapped['MeasurandTaxon'] = relationship(back_populates="parameters")
    
    name: Mapped[str] = mapped_column(String(50))
    quantitykind: Mapped[Optional[str]] = mapped_column(String(50))
    definition: Mapped[Optional[str]] = mapped_column(UnicodeText)
    optional: Mapped[bool] = mapped_column()

    # One-to-one
    aspect_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("aspect.id"))
    aspect: Mapped['Aspect'] = relationship()

    def __str__(self):
        return f'{self.name}'


class Reference(Base):
    __tablename__ = "reference"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category_name = mapped_column(String(50))
    category_value = mapped_column(String(50))
    reference_name = mapped_column(String(50))
    reference_url = mapped_column(String(100))
    measurandtaxon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("measurandtaxon.id"))
    measurandtaxon: Mapped['MeasurandTaxon'] = relationship(back_populates="external_references")


class Taxon(Base):
    __tablename__ = "taxon"
    # deprecated class
    # MeasurandTaxon is the canonical defintion
    # Measurand (should) default to the attributes defined in its parent MeasurandTaxon

    # id = Column(UnicodeText, primary_key=True)
    id: Mapped[str] = mapped_column(UnicodeText, primary_key=True)

    supertaxon_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('taxon.id'))

    subtaxons: Mapped[list['Taxon']] = \
        relationship(back_populates='supertaxon',
                     remote_side=[id])

    supertaxon: Mapped['Taxon'] = relationship(back_populates='subtaxons')
    # Name should be constructor from init
    # Taxon attributes following BNF grammar
    name: Mapped[str] = mapped_column(String(50))
    deprecated: Mapped[bool]
    quantitykind: Mapped[str] = mapped_column(String(50))
    processtype: Mapped[str] = mapped_column(String(10))  # Source | Measure
    # One-to-one
    aspect_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("aspect.id"))
    aspect: Mapped['Aspect'] = relationship()
    qualifier: Mapped[Optional[str]] = mapped_column(String(50))
    
    # discipline_id: Mapped[Optional[int]] = \
    #    mapped_column(ForeignKey("discipline.id"))
    # discipline: Mapped['Discipline'] = relationship(back_populates="taxon")

    def __str__(self):
        return f'{self.id}'


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


class Discipline(Base):
    # Disciplines should be one to many aspects or quantity kinds in taxonomy
    __tablename__ = "discipline"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50))
    measurandtaxon = relationship("MeasurandTaxon", back_populates="discipline")

    def __str__(self):
        return f'{self.label}'


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


class PrefixSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Prefix
        load_instance = True
        ordered = True


class UnitSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Unit
        include_relationships = True
        load_instance = True
        ordered = True


class SystemSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = System
        load_instance = True
        ordered = True


class DimensionSchema(SQLAlchemyAutoSchema):
    formal_system = Nested(SystemSchema)

    class Meta:
        model = Dimension
        include_relationships = True
        load_instance = True
        ordered = True


class ScaleSchema(SQLAlchemyAutoSchema):
    # unit = Nested(UnitSchema)
    prefix = Nested(PrefixSchema)
    dimension = Nested(DimensionSchema)
    # root_scale = Nested(ScaleSchema)

    class Meta:
        model = Scale
        include_relationships = True
        load_instance = True
        ordered = True


class AspectSchema(SQLAlchemyAutoSchema):
    scales = Nested(ScaleSchema, many=True)

    class Meta:
        model = Aspect
        include_relationships = True
        load_instance = True
        ordered = True


class TransformSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Transform
        include_relationships = True
        load_instance = True
        ordered = True


class ConversionSchema(SQLAlchemyAutoSchema):
    src_scale = Nested(ScaleSchema)
    dst_scale = Nested(ScaleSchema)
    aspect = Nested(AspectSchema)
    transform = Nested(TransformSchema)

    class Meta:
        model = Conversion
        include_relationships = True
        load_instance = True
        ordered = True


class ReferenceSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Reference
        include_relationships = True
        load_instance = True
        ordered = True


class ParameterSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Parameter
        include_relationships = True
        load_instance = True
        ordered = True
    aspect = Nested(AspectSchema(only=("name", "ml_name", "id",)))


class DisciplineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Discipline
        include_relationships = True
        load_instance = True
        ordered = True


class MeasurandTaxonSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = MeasurandTaxon
        include_relatiohsips = True
        load_instance = True
        ordered = True

    parameters = Nested(ParameterSchema, many=True)
    external_references = Nested(ReferenceSchema, many=True)
    aspect = Nested(AspectSchema(only=("name", "ml_name", "id",)))
    scale = Nested(ScaleSchema(only=("ml_name", "id",)))
    discipline = Nested(DisciplineSchema(only=("label",)))


class TaxonSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Taxon
        include_relationships = True
        load_instance = True
        ordered = True


class MeasurandSchema(SQLAlchemyAutoSchema):
    parameters = Nested(ParameterSchema, many=True)
    taxon = Nested(TaxonSchema)

    class Meta:
        model = Measurand
        include_relatiohsips = True
        load_instance = True
        ordered = True


class KcdbCmcSchema(SQLAlchemyAutoSchema):
    measurands = Nested(MeasurandSchema, many=True, only=('name',),)
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
