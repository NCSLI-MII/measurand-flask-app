#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

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

# M-Layer Model
scaleaspect_table = Table(
    "scaleaspect_table",
    Base.metadata,
    Column("scale_id", ForeignKey("scale.id"), primary_key=True),
    Column("aspect_id", ForeignKey("aspect.id"), primary_key=True),
)

# M-Layer Aspect
class Aspect(Base):
    # Aspect will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "aspect"
    # aspect | id | [core] The M-layer unique identifier for an aspect.
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    
    # aspect | name | [core] Conventional name for the aspect
    name: Mapped[str] = mapped_column(String(50))
    
    # aspect | ml_name | [impl] Internal identifier for the aspect
    ml_name: Mapped[str] = mapped_column(String(50))
    
    # aspect | symbol | [core] Conventional symbol for the aspect
    symbol: Mapped[Optional[str]] = mapped_column(String(50))
    
    # aspect | reference | [core] Reference to an authoritative definition of the aspect.
    reference: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Association inferred from conversion or cast table
    scales: Mapped[list['Scale']] = \
        relationship(secondary=scaleaspect_table, back_populates="aspects")
    # Conversions should be related to the scale,
    # aspect only disambiguates the expression
    # conversions = relationship('Conversion', back_populates='aspect')

    def __str__(self):
        return f'{self.name}'

# Scale class gives access to all related scale information
# Composite scales reference a root scale
# Self-referencing relation to root_scale only from child using remote_side
# Establishes many-to-one relation
# See https://docs.sqlalchemy.org/en/20/orm/self_referential.html


class Scale(Base):
    __tablename__ = "scale"
    
    # --- The following reference model attributes are not implemented --- 
    # scale | in_point | [extd] Interval scale reference point
    # scale | bi_point_l | [extd] Bounded interval scale lower reference point
    # scale | bi_point_h | [extd] Bounded interval scale upper reference point
    # scale | system_id | [core] Unit system associated with scale.
    # scale | scale_factor | [impl] Multiplicative scale factor relative to root_scale_id
    # scale | name | [core] Conventional name of the scale itself (not a quantity or unit); NULL if there is no established name.
    # scale | symbol | [core] Conventional symbol of the scale (e.g. 'pH'); NULL if there is no established symbol. 
    # 
    # scale | id | [core] The M-layer unique identifier for a scale.
    id: Mapped[str] = mapped_column(String(10), primary_key=True)

    # scale | ml_name | [impl] Canonical form of scale-type, system, and unit symbols.
    ml_name: Mapped[str] = mapped_column(String(50))

    # scale | type | [extd] Scale type (ratio, interval, ordinal, etc.).
    scale_type: Mapped[str] = mapped_column(String(20))

    # scale | root_scale_id | [impl] Canonical scale without prefixes; NULL for root scales.
    root_scale_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey('scale.id'))

    root_scale: Mapped['Scale'] = relationship(remote_side=[id])

    # scale | prefix_id | [impl] Metric prefix applied to the root-scale unit.
    prefix_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("prefix.id"))  # One-to-one

    prefix: Mapped['Prefix'] = relationship()
    
    # scale | unit_id | [core] Unit defining the size of one scale division.
    unit_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("unit.id"))  # One-to-one

    unit: Mapped['Unit'] = relationship()

    # scale | system_dimensions_id | [extd] System dimensions associated with scale.
    system_dimensions_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('dimension.id'))

    system_dimensions: Mapped['Dimension'] = relationship("Dimension", foreign_keys=[system_dimensions_id])
        # Remove view on all scales that share dimension
        # Only point to the dimension that define the scale
        #relationship(back_populates="systematic_scales")

    # scale | is_systematic | [extd] True for a ratio scale associated with a compound unit expressed in system base units.
    is_systematic: Mapped[Optional[bool]]

    # scale | is_special | [extd] True when the scale's unit has a special name in the unit system.
    is_special: Mapped[Optional[bool]]

    ref_point: Mapped[Optional[str]]

    ref_point_l: Mapped[Optional[str]]

    ref_point_h: Mapped[Optional[str]]

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
    
    # Dimensions only points back to the systematic scale
    systematic_scale_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('scale.id'))

    exponents: Mapped[Optional[str]] = mapped_column(String(40))

    # Dimension is only defined for one systematic_scale
    # Whereas many scales may have the same dimensions 
    # The view of all scales with the same dimension may be useful
    # What is required is the relation between the systematic scale and the dimension
    #systematic_scales: Mapped[list['Scale']] = \
    #    relationship(back_populates="system_dimensions", viewonly=True)

    formal_system: Mapped['System'] = relationship()
    systematic_scale: Mapped['Scale'] = relationship("Scale", foreign_keys=[systematic_scale_id])

        #relationship(primaryjoin="(Scale.id == Cast.src_scale_id)",
        #             viewonly=True)
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


