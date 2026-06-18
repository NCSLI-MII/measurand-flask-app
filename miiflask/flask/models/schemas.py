#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""
Marshmallow schemas for serialization
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

from miiflask.flask.models.mlayer import (
        Prefix,
        Unit,
        System,
        Dimension,
        Scale,
        Aspect,
        Transform,
        Conversion
        )

from miiflask.flask.models.taxonomy import (
        Reference,
        Parameter,
        Discipline,
        MeasurandTaxon
        )



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
    basis_pairs = fields.Method("get_basis_representation")
    class Meta:
        model = System
        load_instance = True
        ordered = True

    def get_basis_representation(self, obj):
        if(obj.basis is None):
            return None
        items = []
        pairs = re.findall(r'\(([^)]+)\)', obj.basis)
        resulting_pairs = [pair.split(',') for pair in pairs]
        for item in resulting_pairs:
            items.append({"system_aspect": item[0],
                "system_scale": item[1]})
        return items


class DimensionSchema(SQLAlchemyAutoSchema):
    formal_system = Nested(SystemSchema)

    class Meta:
        model = Dimension
        include_relationships = True
        load_instance = True
        ordered = True


class ScaleSchema(SQLAlchemyAutoSchema):
    #unit = Nested(UnitSchema)
    prefix = Nested(PrefixSchema)
    system_dimensions = Nested(lambda:DimensionSchema(only=("id","exponents","formal_system.id")))
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


#class TaxonSchema(SQLAlchemyAutoSchema#):
#    class Meta:
#        model = Taxon
#        include_relationships = True
#        load_instance = True
#        ordered = True


#class MeasurandSchema(SQLAlchemyAutoSchema):
#    parameters = Nested(ParameterSchema, many=True)
#    taxon = Nested(TaxonSchema)
#
#    class Meta:
#        model = Measurand
#        include_relatiohsips = True
#        load_instance = True
       # ordered = True
