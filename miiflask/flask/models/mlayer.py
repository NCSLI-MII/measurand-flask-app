#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""
SQLAlchemy M-Layer Data Model
"""
from miiflask.flask.db import Base

from sqlalchemy import and_, select, union_all, literal
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
from sqlalchemy.orm import relationship, foreign, Mapped, mapped_column

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

# Scale-Aspect Association table describing a quantity
# scaleaspect_table with additional attributes
# table_name  | column_name |                                                         comment                                                          
# --------------+-------------+--------------------------------------------------------------------------------------------------------------------------
# aspect_scale | aspect_id   | [core] Aspect identifier
# aspect_scale | scale_id    | [core] Scale identifier
# aspect_scale | name        | [core] Conventional name of the aspect-scale pair itself (not a quantity or unit); NULL if there is no established name.
# aspect_scale | symbol      | [core] Conventional symbol of the aspect-scale pair (e.g. 'pH'); NULL if there is no established symbol.
# aspect_scale | source      | [core] Reference to an authoritative definition of the aspect-scale.
class QuantityObject(Base):
    __tablename__ = "quantityobject_table"
    
    scale_id: Mapped[int] = \
        mapped_column(ForeignKey('scale.id'),
                primary_key=True,
                comment="scale identifier",
                doc="core")
    
    aspect_id: Mapped[int] = \
        mapped_column(ForeignKey('aspect.id'),
                primary_key=True,
                comment="aspect identifier",
                doc="core")
    
    #transformations: Mapped[list["Conversion"]] = relationship(
    #        "Conversion",
    #        primaryjoin=lambda: and_(
    #            QuantityObject.scale_id == foreign(Conversion.src_scale_id),
    #            QuantityObject.aspect_id == foreign(Conversion.aspect_id)
    #            ),
     #       viewonly=True
     #       )
    
    transformations: Mapped[list["ConversionCast"]] = relationship(
        "ConversionCast",
        primaryjoin=lambda: and_(
            QuantityObject.scale_id == foreign(ConversionCast.src_scale_id),
            QuantityObject.aspect_id == foreign(ConversionCast.src_aspect_id)
        ),
        viewonly=True
    )

    # Name and symbol convention - 
    # name and symbol obtained from 
    # aspect-scale
    # scale, 
    # unit tables (in that order) until name-symbol entries are found

    name: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Preferred name for the quantity expression",
            doc="core")
    
    symbol: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Preferred symbol for the quantity expression",
            doc="core")
    
    quantity_name: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Conventional name for the quantity expression",
            doc="core")
    
    quantity_symbol: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Conventional symbol for the quantity expression",
            doc="core")
    
    system_symbol: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Preferred symbol of the Unit system associated with the quantity expression",
            doc="core")
    
    # aspect-scale | source | [core] Reference to an authoritative definition of the aspect.
    reference: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Reference to an authoritative definition of the aspect-scale.",
            doc="core"
            )
    scale: Mapped['Scale'] = relationship(back_populates="scale_aspect_associations")
    
    aspect: Mapped['Aspect'] = relationship(back_populates="scale_aspect_associations")
    
    def __str__(self):
        return f'{self.quantity_name}'


# M-Layer Aspect
class Aspect(Base):
    # Aspect will be referenced by many tables
    # Do not keep relationship to other tables
    __tablename__ = "aspect"
    # aspect | id | [core] The M-layer unique identifier for an aspect.
    id: Mapped[str] = mapped_column(String(10),
            primary_key=True,
            comment="The M-layer unique identifier for an aspect.",
            doc="core")
    
    # aspect | ml_name | [impl] Internal identifier for the aspect
    ml_name: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Internal identifier for the aspect",
            doc="impl")
    
    # aspect | name | [core] Conventional name for the aspect
    name: Mapped[str] = mapped_column(String(50),
            comment="Conventional name for the aspect",
            doc="core")
    
    # aspect | symbol | [core] Conventional symbol for the aspect
    symbol: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Conventional symbol for the aspect",
            doc="core"
            )
    
    # aspect | source | [core] Reference to an authoritative definition of the aspect.
    reference: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Reference to an authoritative definition of the aspect.",
            doc="core"
            )
    
    # Association inferred from conversion or cast table
    #scales: Mapped[list['Scale']] = \
    #    relationship(secondary=scaleaspect_table, back_populates="aspects")
    scales: Mapped[list['Scale']] = \
        relationship(secondary="quantityobject_table", viewonly=True)
    # Conversions should be related to the scale,
    # aspect only disambiguates the expression
    # conversions = relationship('Conversion', back_populates='aspect')
    
    scale_aspect_associations: Mapped[list['QuantityObject']] = \
            relationship(back_populates="aspect", cascade="all, delete-orphan")
    
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
    # scale | is_augmented  | [extd] True for a ratio scale with a compound unit combining system base units and named dimensionless units.    # scale | id | [core] The M-layer unique identifier for a scale.
    
    # Comments - system_id equivalent to system_dimensions.formal_system_id
    id: Mapped[str] = mapped_column(String(10), 
            primary_key=True, 
            comment="The M-layer unique identifier for a scale.",
            doc="core")

    # scale | ml_name | [impl] 
    ml_name: Mapped[Optional[str]] = mapped_column(String(50), 
            comment="Canonical form of scale-type, system, and unit symbols.",
            doc="impl")

    # scale | name | [core] Conventional name for the scale
    name: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Conventional name for the scale",
            doc="core")
    
    # scale | symbol | [core] Conventional symbol for the scale
    symbol: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Conventional symbol for the scale",
            doc="core"
            )
    
    # scale | type | [extd] Scale type (ratio, interval, ordinal, etc.).
    scale_type: Mapped[str] = mapped_column(String(20), 
            comment="Scale type (ratio, interval, ordinal, etc.).",
            doc="extd")

    # scale | unit_id | [core] Unit defining the size of one scale division.
    unit_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("unit.id"),
                comment="Unit defining the size of one scale division.",
                doc="core")  # One-to-one
    unit: Mapped['Unit'] = relationship()
    
    # scale | prefix_id | [impl] Metric prefix applied to the root-scale unit.
    prefix_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey("prefix.id"),
                comment="Metric prefix applied to the root-scale unit.",
                doc="impl")  # One-to-one
    prefix: Mapped['Prefix'] = relationship()
    
    # scale | root_scale_id | [impl] Canonical scale without prefixes; NULL for root scales.
    root_scale_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey('scale.id'),
                comment="Canonical scale without prefixes; NULL for root scales.",
                doc="impl")
    root_scale: Mapped['Scale'] = relationship(remote_side=[id])

    # scale | system_dimensions_id | [extd] System dimensions associated with scale.
    system_dimensions_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('dimension.id'),
                comment="System dimensions associated with scale.",
                doc="extd")
    system_dimensions: Mapped['Dimension'] = relationship("Dimension", foreign_keys=[system_dimensions_id])
        # Remove view on all scales that share dimension
        # Only point to the dimension that define the scale
        #relationship(back_populates="systematic_scales")

    # scale | is_systematic | [extd] True for a ratio scale associated with a compound unit expressed in system base units.
    is_systematic: Mapped[Optional[bool]] = mapped_column(Boolean, 
            comment="True for a ratio scale associated with a compound unit expressed in system base units.",
            doc="extd"
            )

    # scale | is_special | [extd] True when the scale's unit has a special name in the unit system.
    is_special: Mapped[Optional[bool]] = mapped_column(Boolean,
            comment="True when the scale's unit has a special name in the unit system.",
            doc="extd")

    # Deprecated - replaced with in_point
    ref_point: Mapped[Optional[str]]

    # Deprecated - replaced with bi_point_l
    ref_point_l: Mapped[Optional[str]]

    # Deprecated - replaced with bi_point_h
    ref_point_h: Mapped[Optional[str]]

    # Using secondary scaleaspect_table
    #aspects: Mapped[list['Aspect']] = \
    #    relationship(secondary=scaleaspect_table,
    #                 back_populates="scales")

    # Using QuantityObject and view only
    aspects: Mapped[list['Aspect']] = relationship(secondary="quantityobject_table", viewonly=True)
    conversions: Mapped[list['Conversion']] = \
        relationship(primaryjoin="(Scale.id == Conversion.src_scale_id)",
                     viewonly=True)

    casts: Mapped[list['Cast']] = \
        relationship(primaryjoin="(Scale.id == Cast.src_scale_id)",
                     viewonly=True)
    # src_scales = relationship('Conversion', back_populates='src_scale')
    # dst_scales = relationship('Conversion', back_populates='dst_scale')

    scale_aspect_associations: Mapped[list['QuantityObject']] = \
            relationship(back_populates="scale", cascade="all,delete-orphan")
    def __str__(self):
        return f'{self.ml_name}'

    def __unicode__(self):
        return self.ml_name

###
# table_name | column_name | comment
# -----------------+---------------+------------------------------------------------
# conversion_cast | is_cast | [core] True when the transformation is a cast.
# conversion_cast | src_scale_id | [core] Initial scale identifier
# conversion_cast | src_aspect_id | [core] Initial aspect identifier
# conversion_cast | dst_scale_id | [core] Final scale identifier
# conversion_cast | dst_aspect_id | [core] Final aspect identifier
# conversion_cast | function_id | [core] Transformation function
# conversion_cast | parameters | [core] Transformation function arguments
####
class Conversion(Base):
    __tablename__ = "conversion"
    
    # conversion_cast | src_scale_id | [core] Initial scale identifier
    src_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True,
                                              comment="Initial scale identifier",
                                              doc="core")

    # conversion_cast | dst_scale_id | [core] Final scale identifier
    dst_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True,
                                              comment="Final scale identifier",
                                              doc="core")

    # conversion | aspect_id | [core] aspect identifier common to src and dst scale
    #aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
    #                                       primary_key=True,
    #                                       comment="aspect identifier common to src and dst scale",
    #                                       doc="core")
    
    # conversion | src_aspect_id | [core] Initial aspect identifier 
    src_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                           primary_key=True,
                                           comment="Initial aspect identifier",
                                           doc="core")
    
    # conversion | dst_aspect_id | [core] Final aspect identifier 
    dst_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                           primary_key=True,
                                           comment="Final aspect identifier", 
                                           doc="core")

    # conversion_cast | function_id | [core] Transformation function
    transform_id: Mapped[str] = mapped_column(ForeignKey("transform.id"),
            comment="Transformation function" )
    
    # conversion_cast | parameters | [core] Transformation function arguments
    parameters: Mapped[str] = mapped_column(UnicodeText, comment="Transformation function arguments")

    src_scale: Mapped['Scale'] = relationship(foreign_keys=[src_scale_id])
    dst_scale: Mapped['Scale'] = relationship(foreign_keys=[dst_scale_id])
    #aspect: Mapped['Aspect'] = relationship(foreign_keys=[aspect_id])
    src_aspect: Mapped['Aspect'] = relationship(foreign_keys=[src_aspect_id])
    dst_aspect: Mapped['Aspect'] = relationship(foreign_keys=[dst_aspect_id])
    transform: Mapped['Transform'] = relationship(foreign_keys=[transform_id])

    # Investigate whether to use PrimaryKeyConstraint.
    # The PrimaryKeyConstraint object provides
    # explicit access to this constraint,
    # which includes the option of being configured directly:

    def __str__(self):
        return "{}.{}.{}.{}".format(self.src_scale_id,
                                 self.dst_scale_id,
                                 self.src_aspect_id,
                                 self.dst_aspect_id)


class Cast(Base):
    __tablename__ = "cast"
    
    # conversion_cast | is_cast | [core] True when the transformation is a cast.
    
    # conversion_cast | src_scale_id | [core] Initial scale identifier
    src_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True,
                                              comment="Initial scale identifier",
                                              doc="core")
    
    # conversion_cast | dst_scale_id | [core] Final scale identifier
    dst_scale_id: Mapped[str] = mapped_column(ForeignKey("scale.id"),
                                              primary_key=True,
                                              comment="Final scale identifier",
                                              doc="core")
    
    # conversion_cast | src_aspect_id | [core] Initial aspect identifier
    src_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                               primary_key=True,
                                               comment="Initial aspect identifier",
                                               doc="core")
    
    # conversion_cast | dst_aspect_id | [core] Final aspect identifier
    dst_aspect_id: Mapped[str] = mapped_column(ForeignKey("aspect.id"),
                                               primary_key=True,
                                               comment="Final aspect identifier",
                                               doc="core")

    # conversion_cast | function_id | [core] Transformation function
    transform_id: Mapped[str] = mapped_column(ForeignKey("transform.id"))
    
    # conversion_cast | parameters | [core] Transformation function arguments
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


conversion_cast_select = union_all(
        select(
            Conversion.src_scale_id.label("src_scale_id"),
            Conversion.src_aspect_id.label("src_aspect_id"),
            Conversion.dst_scale_id.label("dst_scale_id"),
            Conversion.dst_aspect_id.label("dst_aspect_id"),
            literal("conversion").label("type")
        ),
        select(
            Cast.src_scale_id.label("src_scale_id"),
            Cast.src_aspect_id.label("src_aspect_id"),
            Cast.dst_scale_id.label("dst_scale_id"),
            Cast.dst_aspect_id.label("dst_aspect_id"),
            literal("cast").label("type")
        )
    ).subquery()

class ConversionCast(Base):
    __table__ = conversion_cast_select

    __mapper_args__ = {
        "primary_key": [
            conversion_cast_select.c.src_scale_id,
            conversion_cast_select.c.src_aspect_id,
            conversion_cast_select.c.dst_scale_id,
            conversion_cast_select.c.dst_aspect_id,
            conversion_cast_select.c.type
        ]
    }

class Unit(Base):
    __tablename__ = "unit"
    
    # unit | id | [core] The M-layer unique identifier for a unit.
    id: Mapped[str] = mapped_column(String(50), 
            primary_key=True,
            comment="The M-layer unique identifier for a unit.",
            doc="core"
            )
    
    # unit | name | [core] Conventional name of the unit
    name: Mapped[Optional[str]] = mapped_column(String(100),
            comment=" Conventional name of the unit",
            doc="core")
    
    # unit | ml_name | [impl] Canonical form for unit.
    ml_name: Mapped[Optional[str]] = mapped_column(String(100),
            comment="Canonical form for unit.",
            doc="impl")
    
    # unit | symbol | [core] Conventional symbol of the unit
    symbol: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Conventional symbol of the unit",
            doc="core")
    
    # unit | source | [core] Reference to an authoritative definition of the unit. 
    reference: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Reference to an authoritative definition of the unit.",
            doc="core")

    def __str__(self):
        return f'{self.name or self.symbol}'

    def __unicode__(self):
        return self.name


class System(Base):
    __tablename__ = 'system'
    
    # system | id | [core] The M-layer unique identifier for a unit system.
    id: Mapped[str] = mapped_column(String(10),
            primary_key=True,
            comment="The M-layer unique identifier for a unit system.",
            doc="core"
            )
    
    # system | ml_name | [impl] Internal identifier for the system name
    ml_name: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Internal identifier for the system name",
            doc="impl")
    
    # system | symbol | [core] A textual symbol (abbreviation) for the unit system
    symbol: Mapped[str] = mapped_column(String(10),
            comment="A textdual symbol (abbreviation) for the unit system",
            doc="core"
            )
    
    # system | n | [extd] Number of system base units.
    n: Mapped[Optional[int]] = mapped_column(Integer,
            comment="Number of system base units.",
            doc="extd"
            )
    
    # system | basis | [extd] Sequence of (aspect, scale) id pairs defining the system's base quantities and units.
    basis: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Sequence of (aspect, scale) id pairs defining the system's base quantities and units.",
            doc="extd")
    
    # system | source | [core] Reference to an authoritative definition of the unit system. 
    reference: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Reference to an authoritative definition of the unit system. ",
            doc="core"
            )

    def __str__(self):
        return f'{self.symbol}'


class Dimension(Base):
    __tablename__ = 'dimension'
     # dimension  | id                  | [extd] The M-layer unique identifier for the dimension
    id: Mapped[str] = mapped_column(String(10), 
            primary_key=True,
            comment="The M-layer unique identifier for the dimension",
            doc="extd")

    # dimension  | formal_system_id    | [extd] Unit system in which this system dimension is defined.
    formal_system_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('system.id'),
                comment="Unit system in which this system dimension is defined.",
                doc="extd")
    
    # Dimensions only points back to the systematic scale
    # dimension  | systematic_scale_id | [extd] Systematic scale with the same dimension
    systematic_scale_id: Mapped[Optional[str]] = \
        mapped_column(ForeignKey('scale.id'),
                comment="Systematic scale with the same dimension",
                doc="extd")
 
    # dimension  | exponents           | [extd] Integer or rational exponent sequence for this system dimension.
    exponents: Mapped[Optional[str]] = mapped_column(String(40),
            comment="Integer or rational exponent sequence for this system dimension.",
            doc="extd")

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
    
    # function | id | [core] The M-layer unique identifier for a transformation function.
    id: Mapped[str] = mapped_column(String(10),
            primary_key=True,
            comment="The M-layer unique identifier for a transformation function.",
            doc="core"
            )
    
    # function | ml_name | [impl] Internal identifier for the transformation function
    ml_name: Mapped[Optional[str]] = mapped_column(String(50),
            comment="Internal identifier for the transformation function",
            doc="impl")
    
    # function | py_function | [core] Python expression defining the transformation function.
    py_function: Mapped[Optional[str]] = mapped_column(UnicodeText,
            comment="Python expression defining the transformation function.",
            doc="core")
    
    # function | py_names_in_scope | [core] Parameter names required by the transformation function.
    py_names_in_scope: Mapped[Optional[str]] = mapped_column(UnicodeText,
            comment="Parameter names required by the transformation function.",
            doc="core"
            )
    
    # function | comments | [core] Free-text notes. 
    comments: Mapped[Optional[str]] = mapped_column(UnicodeText,
            comment="Free-text notes. ",
            doc="core")

    def __str__(self):
        return f'{self.ml_name}'



class Prefix(Base):
    __tablename__ = "prefix"

    # prefix     | id          | [impl] The M-layer unique identifier for a prefix.
    id: Mapped[str] = mapped_column(String(50), 
            primary_key=True,
            comment="The M-layer unique identifier for a prefix.",
            doc="impl")
    
    # prefix     | name        | [impl] Conventional name of the prefix.
    name: Mapped[str] = mapped_column(String(100),
            comment="Conventional name of the prefix.",
            doc="impl")
    
    # prefix     | ml_name     | [impl] The M-layer unique identifier for a prefix
    ml_name: Mapped[Optional[str]] = mapped_column(String(100),
            comment="The M-layer unique identifier for a prefix",
            doc="impl")
    
    # prefix     | symbol      | [impl] Conventional symbol of the prefix.
    symbol: Mapped[str] = mapped_column(String(50),
            comment="Conventional symbol of the prefix.",
            doc="impl")
    
    # prefix     | numerator   | [impl] Numerator of the prefix factor, stored as an integer string.
    numerator: Mapped[float] = mapped_column(comment="Numerator of the prefix factor, stored as an integer string.")
    
    # prefix     | denominator | [impl] Denominator of the prefix factor, stored as an integer string.
    denominator: Mapped[float] = mapped_column(comment="Denominator of the prefix factor, stored as an integer string.")
    
    # prefix     | source      | [impl] Reference to an authoritative definition of the prefix.
    reference: Mapped[Optional[str]] = mapped_column(String(200),
            comment="Reference to an authoritative definition of the prefix.",
            doc="impl")

    def __str__(self):
        return f'{self.name}'

# Undefined table 
# table_name | column_name |                        comment
# ------------+-------------+--------------------------------------------------------
# reference  | id          | [core] The M-layer unique identifier for the reference
# reference  | ml_name     | [impl] Internal identifier for the reference
# reference  | name        | [core] Conventional name for the reference
# reference  | symbol      | [core] M-layer symbol for the reference
# reference  | source      | [core] Source defining or documenting this entry.
# class Reference(Base):
#     __tablename__ = "reference"



