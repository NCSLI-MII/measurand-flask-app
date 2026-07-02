#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""
SQLAlchemy Taxonomy Data Model
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


class Administrative(Base):
    __tablename__ = "administrative"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    mii_comment: Mapped[Optional[str]] = mapped_column(UnicodeText)


class MeasurandTaxon(Base):
    __tablename__ = "measurandtaxon"
    id: Mapped[str] = mapped_column(UnicodeText, primary_key=True)
    
    name: Mapped[str] = mapped_column(String(50))

    definition: Mapped[Optional[str]] = mapped_column(UnicodeText)
    
    deprecated: Mapped[bool] 

    replacement: Mapped[str] = mapped_column(String(50), nullable=False, default='')
    
    quantitykind: Mapped[Optional[str]] = mapped_column(String(50))

    aspect_id: Mapped[Optional[str]] = mapped_column(ForeignKey("aspect.id"))

    aspect: Mapped['Aspect'] = relationship(foreign_keys=[aspect_id]) #, primaryjoin=aspect_id == Aspect.id)
    
    processtype: Mapped[str] = mapped_column(String(10), nullable=False, default='')  # Source | Measure
    
    qualifier: Mapped[Optional[str]] = mapped_column(String(50), nullable=False, default='')
    
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



class Parameter(Base):
    # many-to-one
    # Reference a quantity for each parameter
    __tablename__ = "parameter"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
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


class Discipline(Base):
    # Disciplines should be one to many aspects or quantity kinds in taxonomy
    __tablename__ = "discipline"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50))
    measurandtaxon = relationship("MeasurandTaxon", back_populates="discipline")

    def __str__(self):
        return f'{self.label}'
