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
                        Boolean
                        )
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
    Column("scale_id", ForeignKey("scale.id"), primary_key=True),
    Column("aspect_id", ForeignKey("aspect.id"), primary_key=True),
)


class Conversion(Base):
    __tablename__ = "conversion"
    src_scale_id = Column("src_scale_id", ForeignKey("scale.id"), primary_key=True)
    dst_scale_id = Column("dst_scale_id", ForeignKey("scale.id"), primary_key=True)
    aspect_id = Column("aspect_id", ForeignKey("aspect.id"), primary_key=True)
    transform_id = Column("transform_id", ForeignKey("transform.id"))
    parameters = Column(UnicodeText)
    
    src_scale = relationship('Scale', foreign_keys=[src_scale_id])
    dst_scale = relationship('Scale', foreign_keys=[dst_scale_id])
    aspect = relationship('Aspect', foreign_keys=[aspect_id]) #, back_populates='conversions')
    transform = relationship('Transform', foreign_keys=[transform_id])
    
    def __str__(self):
        return "{}.{}.{}".format(self.src_scale_id, 
                                 self.dst_scale_id, 
                                 self.aspect_id)


class Cast(Base):
    __tablename__ = "cast"
    src_scale_id = Column("src_scale_id", ForeignKey("scale.id"), primary_key=True)
    src_aspect_id = Column("src_aspect_id", ForeignKey("aspect.id"), primary_key=True)
    dst_scale_id = Column("dst_scale_id", ForeignKey("scale.id"), primary_key=True)
    dst_aspect_id = Column("dst_aspect_id", ForeignKey("aspect.id"), primary_key=True)
    transform_id = Column("transform_id", ForeignKey("transform.id"))
    parameters = Column(UnicodeText)

    src_scale = relationship('Scale', foreign_keys=[src_scale_id])
    src_aspect = relationship('Aspect', foreign_keys=[src_aspect_id]) 
    dst_scale = relationship('Scale', foreign_keys=[dst_scale_id])
    dst_aspect = relationship('Aspect', foreign_keys=[dst_aspect_id]) 
    transform = relationship('Transform', foreign_keys=[transform_id])

    def __str__(self):
        return "{}.{}.{}.{}".format(self.src_scale_id, 
                                 self.src_aspect_id,
                                 self.dst_scale_id, 
                                 self.dst_aspect_id)


class Transform(Base):
    __tablename__ = "transform"
    id = Column(String(10), primary_key=True)
    ml_name = Column(String(50))
    py_function = Column(UnicodeText)
    py_names_in_scope = Column(UnicodeText)
    comments = Column(UnicodeText)
    
    def __str__(self):
        return self.ml_name
    
# M-Layer Aspect
class Aspect(Base):
    # Aspect will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "aspect"
    id = Column(String(10), primary_key=True)
    name = Column(String(50))
    ml_name = Column(String(50))
    symbol = Column(String(50))
    reference = Column(String(50))
    scales = relationship(
        "Scale", secondary=scaleaspect_table, back_populates="aspects"
    )
    # Conversions should be related to the scale, aspect only disambiguates the expression
    # conversions = relationship('Conversion', back_populates='aspect')

    def __str__(self):
        return self.name


class Unit(Base):
    __tablename__ = "unit"
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    ml_name = Column(String(100))
    symbol = Column(String(50))
    # special = Column(String(50))
    reference = Column(String(50))
    # systems = Column(String(50))
    # ucum = relationship("UCUM")
    # qudt = relationship("QUDT")
    # system = relationship("System")
    # dimensions = Column(String(10))
    # prefix

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class Scale(Base):
    __tablename__ = "scale"
    id = Column(String(10), primary_key=True)
    ml_name = Column(String(50))
    # scale_type = Column(
    #    Enum("ratio", "interval", "bounded", "ordinal", "nominal"),
    #    nullable=False,
    # )
    unit_id = Column(
        String(50), ForeignKey("unit.id"), nullable=True
    )  # One-to-one
    unit = relationship("Unit")
    aspects = relationship(
        "Aspect", secondary=scaleaspect_table, back_populates="scales"
    )
    conversions = relationship('Conversion', 
                               primaryjoin="(Scale.id == Conversion.src_scale_id)",
                               viewonly=True
                               )
    casts = relationship('Cast', 
                         primaryjoin="(Scale.id == Cast.src_scale_id)",
                         viewonly=True
                        )
    #src_scales = relationship('Conversion', back_populates='src_scale')
    #dst_scales = relationship('Conversion', back_populates='dst_scale')

    def __str__(self):
        return self.ml_name

    def __unicode__(self):
        return self.ml_name




# MII Taxonomy Model
# Attempt to model MII Taxon
# One-to-one NRC Service to Measurand (CMC)
# Measurands are unique but the taxon does not ensure uniqueness
# Measurands may have same taxon but different parameters
class Measurand(Base):
    __tablename__ = "measurand"
    id = Column(String(100), primary_key=True, index=True)
    taxon_id = Column(String(100), ForeignKey("taxon.id"))
    name = Column(String(50))
    result = Column(String(50))
    quantitykind = Column(String(50))
    aspect_id = Column(
        String(50), ForeignKey("aspect.id"), nullable=True
    )  # One-to-one
    taxon = relationship("Taxon", back_populates="measurand")
    aspect = relationship("Aspect")
    definition = Column(UnicodeText)
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
    quantitykind = Column(String(50))
    definition = Column(UnicodeText)
    optional = Column(Boolean)
    aspect_id = Column(
        String(50), ForeignKey("aspect.id"), nullable=True
    )  # One-to-one
    aspect = relationship("Aspect")

    def __str__(self):
        return self.name


class Taxon(Base):
    __tablename__ = "taxon"
    id = Column(String(100), primary_key=True, index=True)
    name = Column(
        String(50)
    )  # Name should be constructor from init with Taxon attributes following BNF grammar
    deprecated = Column(Boolean)
    
    quantitykind = Column(String(50))
    process = Column(String(10))  # Source | Measure
    aspect_id = Column(
        String(50), ForeignKey("aspect.id"), nullable=True
    )  # One-to-one
    aspect = relationship("Aspect")
    qualifier = Column(String(50))
    # Individual taxon may be used in many measurands
    # With bakc_populates if no id for taxon is given
    # SQLAlchemy will create a new one
    measurand = relationship("Measurand", back_populates="taxon")
    discipline_id = Column(
        Integer, ForeignKey("discipline.id"), nullable=True
    )
    discipline = relationship("Discipline", back_populates="taxon")

    def __str__(self):
        return self.id


# Traditional CC areas and team labels
# Domains should be one to many disciplines


class Domain(Base):
    __tablename__ = "domain"
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
    __tablename__ = "discipline"
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

kcdb_measurand_map = Table(
    "kcdb_measurand_map",
    Base.metadata,
    Column("kcdb_service_id", ForeignKey("kcdbservice.id"), primary_key=True),
    Column(
        "measurand_id",
        ForeignKey("measurand.id"),
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
    __tablename__ = "kcdbquantity"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))


class KcdbService(Base):
    __tablename__ = "kcdbservice"
    id = Column(String(50), primary_key=True)
    area_id = Column(String(10))
    area = Column(String(50))
    branch_id = Column(String(20))
    branch = Column(String(50))
    service = Column(String(200))
    subservice = Column(String(200))
    individualservice = Column(String(200))
    measurands = relationship(
        "Measurand", secondary=kcdb_measurand_map, backref="kcdbservices"
    )
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


class UnitSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Unit
        include_relationships = True
        load_instance = True


class ScaleSchema(SQLAlchemyAutoSchema):
    # requires serializing enum
    #scale_type = marshmallow_sqlalchemy.fields.Method("get_scale_type")
    unit = Nested(UnitSchema)
    class Meta:
        model = Scale
        include_relationships = True
        load_instance = True


class AspectSchema(SQLAlchemyAutoSchema):
    scales = Nested(ScaleSchema, many=True)
    
    class Meta:
        model = Aspect
        include_relationships = True
        load_instance = True

class TransformSchema(SQLAlchemyAutoSchema):
    
    class Meta:
        model = Transform
        include_relationships = True
        load_instance = True

class ConversionSchema(SQLAlchemyAutoSchema):
    src_scale = Nested(ScaleSchema)
    dst_scale = Nested(ScaleSchema)
    aspect = Nested(AspectSchema)
    transform = Nested(TransformSchema)
    
    class Meta:
        model = Conversion
        include_relationships = True
        load_instance = True




class ParameterSchema(SQLAlchemyAutoSchema):
    
    class Meta:
        model = Parameter
        include_relationships = True
        load_instance = True


class TaxonSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Taxon
        include_relationships = True
        load_instance = True


class MeasurandSchema(SQLAlchemyAutoSchema):
    parameters = Nested(ParameterSchema, many=True)
    taxon = Nested(TaxonSchema)
    
    class Meta:
        model = Measurand
        include_relatiohsips = True
        load_instance = True




class DisciplineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Discipline
        include_relationships = True
        load_instance = True
