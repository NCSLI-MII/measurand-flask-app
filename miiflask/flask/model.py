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
                        Float
                        )
from sqlalchemy.orm import relationship, Mapped, mapped_column

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

from typing import Optional
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
scaledimension_table = Table(
    "scaledimension_table",
    Base.metadata,
    Column("systematic_scale_id", ForeignKey("scale.id"), primary_key=True),
    Column("dimension_id", ForeignKey("dimension.id"), primary_key=True),
)


class Conversion(Base):
    __tablename__ = "conversion"
    src_scale_id = Column("src_scale_id",
                          ForeignKey("scale.id"),
                          primary_key=True)
    dst_scale_id = Column("dst_scale_id",
                          ForeignKey("scale.id"),
                          primary_key=True)
    aspect_id = Column("aspect_id",
                       ForeignKey("aspect.id"),
                       primary_key=True)
    transform_id = Column("transform_id",
                          ForeignKey("transform.id"))
    parameters = Column(UnicodeText)
    
    src_scale = relationship('Scale', foreign_keys=[src_scale_id])
    dst_scale = relationship('Scale', foreign_keys=[dst_scale_id])
    aspect = relationship('Aspect', foreign_keys=[aspect_id])
    transform = relationship('Transform', foreign_keys=[transform_id])
    
    def __str__(self):
        return "{}.{}.{}".format(self.src_scale_id,
                                 self.dst_scale_id,
                                 self.aspect_id)


class Cast(Base):
    __tablename__ = "cast"
    src_scale_id = Column("src_scale_id",
                          ForeignKey("scale.id"),
                          primary_key=True)
    src_aspect_id = Column("src_aspect_id",
                           ForeignKey("aspect.id"),
                           primary_key=True)
    dst_scale_id = Column("dst_scale_id",
                          ForeignKey("scale.id"),
                          primary_key=True)
    dst_aspect_id = Column("dst_aspect_id",
                           ForeignKey("aspect.id"),
                           primary_key=True)
    transform_id = Column("transform_id",
                          ForeignKey("transform.id"))
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


class System(Base):
    __tablename__ = 'system'
    id = Column(String(10), primary_key=True)
    ml_name = Column(String(10))
    symbol = Column(String(10))
    n = Column(Integer)
    basis = Column(String(200))
    reference = Column(String(50))

    def __str__(self):
        return self.symbol


class Dimension(Base):
    __tablename__ = 'dimension'
    id = Column(String(10), primary_key=True)
    formal_system_id = Column('formal_system_id',
                              ForeignKey('system.id'),
                              nullable=True)
    systematic_scale_id = Column('systematic_scale_id',
                                 ForeignKey('scale.id'),
                                 nullable=True)
    exponents = Column(String(40), nullable=True)
    systematic_scales = relationship("Scale",
                                     secondary=scaledimension_table,
                                     back_populates="system_dimensions")
    formal_system = relationship("System")

    def __str__(self):
        # SI Brochure dimensions
        # dimQ = T^alphaL^betaM^gammaI^deltaTheta^epsilonN^psiJ^eta
        # m-layer encoding
        # dimQ = M^gammaL^betaT^alphaI^deltaTheta^epsilonN^psiJ^eta
        # Time Length Mass Current Temperature AmountOfSubstance LuminousIntensity
        return self.id


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
    # Conversions should be related to the scale,
    # aspect only disambiguates the expression
    # conversions = relationship('Conversion', back_populates='aspect')

    def __str__(self):
        return f'{self.name}'


class Prefix(Base):
    __tablename__ = "prefix"
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    ml_name = Column(String(100))
    symbol = Column(String(50))
    numerator = Column(Float)
    denominator = Column(Float)
    reference = Column(String(50))

    def __str__(self):
        return f'{self.name}'


class Unit(Base):
    __tablename__ = "unit"
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    ml_name = Column(String(100))
    symbol = Column(String(50))
    reference = Column(String(50))

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


class Scale(Base):
    __tablename__ = "scale"
    id = Column(String(10), primary_key=True)
    ml_name = Column(String(50))
    scale_type = Column(String(20))
    root_scale_id: Mapped[Optional[int]] = mapped_column(ForeignKey('scale.id'),
                                                         nullable=True)
    root_scale: Mapped['Scale'] = relationship(remote_side=[id])
    prefix_id = Column(String(50),
                       ForeignKey("prefix.id"),
                       nullable=True)  # One-to-one
    prefix = relationship("Prefix")
    unit_id = Column(String(50),
                     ForeignKey("unit.id"),
                     nullable=True)  # One-to-one
    unit = relationship("Unit")
    
    system_dimensions_id = Column(String(10),
                                  ForeignKey('dimension.id'),
                                  nullable=True)
    system_dimensions = relationship("Dimension",
                                     secondary=scaledimension_table,
                                     back_populates="systematic_scales")
    is_systematic = Column(Boolean)
    aspects = relationship("Aspect",
                           secondary=scaleaspect_table,
                           back_populates="scales")
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
        return f'{self.ml_name}'

    def __unicode__(self):
        return self.ml_name


# MII Taxonomy Model
# Attempt to model MII Taxon
# One-to-one NRC Service to Measurand (CMC)
# Measurands are unique but the taxon does not ensure uniqueness
# Measurands may have same taxon but different parameters

class Measurand(Base):
    __tablename__ = "measurand"
    id = Column(Integer, primary_key=True, index=True)
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
        return f'{self.name}'


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
        return f'{self.name}'


class Taxon(Base):
    __tablename__ = "taxon"
    # id = Column(UnicodeText, primary_key=True)
    id: Mapped[str] = mapped_column(UnicodeText, primary_key=True)
    supertaxon_id: Mapped[Optional[str]] = mapped_column(ForeignKey('taxon.id'))
    subtaxons: Mapped[list['Taxon']] = relationship(back_populates='supertaxon',
                                                        remote_side=[id])
    supertaxon: Mapped['Taxon'] = relationship(back_populates='subtaxons')
    name = Column(
        String(50)
    )  # Name should be constructor from init with Taxon attributes following BNF grammar
    deprecated = Column(Boolean)
    quantitykind = Column(String(50))
    processtype = Column(String(10))  # Source | Measure
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
        return f'{self.id}'


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
        return f'{self.label}'




# Disciplines should be one to many aspects or quantity kinds in taxonomy
class Discipline(Base):
    __tablename__ = "discipline"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50))
    taxon = relationship("Taxon", back_populates="discipline")

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
        "measurand_id",
        ForeignKey("measurand.id"),
        primary_key=True,
    ),
)

# MRA SIM Calibration and Measurement Capabilities entries in the KCDB
class KcdbCmc(Base):
    __tablename__ = "kcdbcmc"
    id = Column(Integer, primary_key=True)
    kcdbCode = Column(String(50))
    
    area_id = Column(
        Integer, ForeignKey("kcdbarea.id"), nullable=True
    )
    area = relationship("KcdbArea")
    
    branch_id = Column(
        Integer, ForeignKey("kcdbbranch.id"), nullable=True
    )
    branch = relationship("KcdbBranch")
    
    service_id = Column(
        Integer, ForeignKey("kcdbservice.id"), nullable=True
    )
    service = relationship("KcdbService")
    
    subservice_id = Column(
        Integer, ForeignKey("kcdbsubservice.id"), nullable=True
    )
    subservice = relationship("KcdbSubservice")

    individualservice_id = Column(
        Integer, ForeignKey("kcdbindividualservice.id"), nullable=True
    )
    individualservice = relationship("KcdbIndividualService")
    
    quantity_id = Column(
        Integer, ForeignKey("kcdbquantity.id"), nullable=True
    )
    quantity = relationship("KcdbQuantity")
    
    instrument_id = Column(
        Integer, ForeignKey("kcdbinstrument.id"), nullable=True
    )
    instrument = relationship("KcdbInstrument")
    
    instrumentmethod_id = Column(
        Integer, ForeignKey("kcdbinstrumentmethod.id"), nullable=True
    )
    instrumentmethod = relationship("KcdbInstrumentMethod")

    tags = relationship(
        "ClassifierTag", secondary=kcdb_classifier_map, backref="kcdbcmcs"
    )
    
    measurands = relationship(
        "Measurand", secondary=kcdb_measurand_map, backref="kcdbcmcs"
    )
    # parents = relationship("Parent", secondary=association_table, back_populates="children")
    # parent_id = Column(String(50), ForeignKey("parent_table.id"))
    # parents = relationship("Parent", back_populates='discipline') # bidirectional relationship

    def __str__(self):
        return f'{self.kcdbCode}'


class KcdbInstrument(Base):
    __tablename__ = "kcdbinstrument"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(200))
    value = Column(UnicodeText)

    def __str__(self):
        return self.value


class KcdbInstrumentMethod(Base):
    __tablename__ = "kcdbinstrumentmethod"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(200))
    value = Column(UnicodeText)

    def __str__(self):
        return self.value

class KcdbQuantity(Base):
    __tablename__ = "kcdbquantity"
    id = Column(Integer, primary_key=True)
    label = Column(String(200))
    value = Column(UnicodeText)

    def __str__(self):
        return self.value


class KcdbArea(Base):
    __tablename__ = "kcdbarea"
    id = Column(Integer, primary_key=True)
    label = Column(String(50))
    value = Column(UnicodeText)
    
    def __str__(self):
        return self.label


class KcdbBranch(Base):
    __tablename__ = "kcdbbranch"
    id = Column(Integer, primary_key=True)
    label = Column(String(50))
    value = Column(UnicodeText)
    
    def __str__(self):
        return self.value

    
class KcdbService(Base):
    __tablename__ = "kcdbservice"
    id = Column(Integer, primary_key=True)
    label = Column(String(50))
    value = Column(UnicodeText)
    
    def __str__(self):
        return self.value


class KcdbSubservice(Base):
    __tablename__ = "kcdbsubservice"
    id = Column(Integer, primary_key=True)
    label = Column(String(50))
    value = Column(UnicodeText)
    
    def __str__(self):
        return self.value


class KcdbIndividualService(Base):
    __tablename__ = "kcdbindividualservice"
    id = Column(Integer, primary_key=True)
    label = Column(String(50))
    value = Column(UnicodeText)
    
    def __str__(self):
        return self.value


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



class KcdbInstrumentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbInstrument
        include_relationships = True
        load_instance = True


class KcdbInstrumentMethodSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbInstrumentMethod
        include_relationships = True
        load_instance = True

class KcdbAreaSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbArea
        include_relationships = True
        load_instance = True


class KcdbBranchSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbBranch
        include_relationships = True
        load_instance = True


class KcdbServiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbService
        include_relationships = True
        load_instance = True


class KcdbSubserviceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbSubservice
        include_relationships = True
        load_instance = True


class KcdbIndividualServiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbIndividualService
        include_relationships = True
        load_instance = True


class KcdbQuantitySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbQuantity
        include_relationships = True
        load_instance = True


class KcdbServiceClassSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbServiceClass
        include_relationships = True
        load_instance = True


class PrefixSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Prefix
        load_instance = True


class UnitSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Unit
        include_relationships = True
        load_instance = True


class SystemSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = System
        load_instance = True


class DimensionSchema(SQLAlchemyAutoSchema):
    formal_system = Nested(SystemSchema)

    class Meta:
        model = Dimension
        include_relationships = True
        load_instance = True


class ScaleSchema(SQLAlchemyAutoSchema):
    unit = Nested(UnitSchema)
    prefix = Nested(PrefixSchema)
    dimension = Nested(DimensionSchema)
    # root_scale = Nested(ScaleSchema, many=True)

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


class KcdbCmcSchema(SQLAlchemyAutoSchema):
    measurands = Nested(MeasurandSchema, many=True)
    area = Nested(KcdbAreaSchema)
    branch = Nested(KcdbBranchSchema)
    service = Nested(KcdbServiceSchema)
    subservice = Nested(KcdbSubserviceSchema)
    individualservice = Nested(KcdbIndividualServiceSchema)
    instrument = Nested(KcdbInstrumentSchema)
    instrumentmethod = Nested(KcdbInstrumentMethodSchema)
    quantity = Nested(KcdbQuantitySchema)
    class Meta:
        model = KcdbCmc
        include_relationships = True
        load_instance = True
