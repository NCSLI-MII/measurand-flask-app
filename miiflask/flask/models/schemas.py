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

from marshmallow import Schema, fields
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
        Conversion,
        QuantityObject
        )

from miiflask.flask.models.taxonomy import (
        Reference,
        Parameter,
        Discipline,
        MeasurandTaxon
        )

from miiflask.flask.models.kcdb import (
        KcdbParameter,
        KcdbInstrument,
        KcdbInstrumentMethod,
        KcdbArea,
        KcdbBranch,
        KcdbService,
        KcdbSubservice,
        KcdbIndividualService,
        KcdbQuantity,
        KcdbCmc,
        KcdbServiceClass
        )


class QuantityObjectSchema(Schema):
    scale_id = fields.String()
    aspect_id = fields.String()

    name = fields.Method("get_name")
    symbol = fields.Method("get_symbol")

    scale_name = fields.Method("get_scale_name")
    scale_symbol = fields.Method("get_scale_symbol")
    scale_type = fields.Method("get_scale_type")

    aspect_name = fields.Method("get_aspect_name")
    aspect_symbol = fields.Method("get_aspect_symbol")
    aspect_reference = fields.Method("get_aspect_reference")

    unit_id = fields.Method("get_unit_id")
    unit_name = fields.Method("get_unit_name")
    unit_symbol = fields.Method("get_unit_symbol")
    unit_reference = fields.Method("get_unit_reference")

    def get_name(self, obj):
        return obj.quantity_name

    def get_symbol(self, obj):
        return obj.quantity_symbol

    def get_scale_name(self, obj):
        return obj.scale.name if obj.scale else None

    def get_scale_symbol(self, obj):
        return obj.scale.symbol if obj.scale else None

    def get_scale_type(self, obj):
        return obj.scale.scale_type if obj.scale else None
    
    def get_aspect_name(self, obj):
        return obj.aspect.name if obj.aspect else None

    def get_aspect_symbol(self, obj):
        return obj.aspect.symbol if obj.aspect else None
    
    def get_aspect_reference(self, obj):
        return obj.aspect.sources if obj.aspect else None

    def get_unit_id(self, obj):
        return obj.scale.unit.id if obj.scale and obj.scale.unit else None

    def get_unit_name(self, obj):
        return obj.scale.unit.name if obj.scale and obj.scale.unit else None

    def get_unit_symbol(self, obj):
        return obj.scale.unit.symbol if obj.scale and obj.scale.unit else None
    
    def get_unit_reference(self, obj):
        return obj.scale.unit.sources if obj.scale and obj.scale.unit else None

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
        include_relationships = True
        load_instance = True
        ordered = True

    parameters = Nested(ParameterSchema, many=True)
    external_references = Nested(ReferenceSchema, many=True)
    aspect = Nested(AspectSchema(only=("name", "id",)))
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


class KcdbServiceClassSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = KcdbServiceClass
        include_relationships = True
        load_instance = True
        ordered = True
