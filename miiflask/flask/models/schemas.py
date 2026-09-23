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
        QuantityObject,
        Reference
        )

from miiflask.flask.models.taxonomy import (
        ExternalReference,
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

    system = fields.Method("get_system")
    dimensions = fields.Method("get_dimensions")

    transforms_to = fields.Method("get_transforms_to")
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

    def get_system(self, obj):
        return obj.scale.system.symbol if obj.scale and obj.scale.system else None

    def get_dimensions(self, obj):
        return obj.scale.system_dimensions.exponents if obj.scale and obj.scale.system_dimensions else None


    def get_transforms_to(self, obj):
        """
        Serialize destination QuantityObjects reachable from this QuantityObject
        by conversion or cast.

        The transformation expression is taken from:
            transformation.transform.py_function

        and rendered as a display string resembling a mathematical relation.
        """

        items = []

        for transformation in getattr(obj, "transformations", []) or []:
            dst_aspect_id = getattr(transformation, "dst_aspect_id", None)
            dst_scale_id = getattr(transformation, "dst_scale_id", None)
            if not dst_aspect_id or not dst_scale_id:
                continue
            dst_scale = getattr(transformation, "dst_scale", None)
            dst_aspect = getattr(transformation, "dst_aspect", None)
            
            dst_quantity_object = self._get_destination_quantity_object(
                transformation
            )

            if dst_quantity_object is not None:
                dst_name = getattr(dst_quantity_object, "quantity_name", None)
                dst_symbol = getattr(dst_quantity_object, "quantity_symbol", None)
            else:
                dst_name = self._compose_quantity_object_name(
                    getattr(transformation, "dst_aspect", None),
                    getattr(transformation, "dst_scale", None),
                )
                dst_symbol = self._compose_quantity_object_symbol(
                    getattr(transformation, "dst_aspect", None),
                    getattr(transformation, "dst_scale", None),
                )

            src_symbol = (
                getattr(obj, "quantity_symbol", None)
                or getattr(obj, "symbol", None)
                or "x"
            )

            dst_symbol_for_relation = dst_symbol or "y"

            py_function = self._get_transform_py_function(transformation)

            items.append(
                {
                    "kind": getattr(transformation, "kind", None),
                    "is_cast": getattr(transformation, "is_cast", None),

                    "aspect_id": dst_aspect_id,
                    "aspect_name": getattr(dst_aspect, "name", None)
                                        if dst_aspect
                                        else None,
                    "scale_id": dst_scale_id,
                    "scale_name": getattr(dst_scale, "name", None)
                                        if dst_scale
                                        else None,

                    "name": dst_name,
                    "symbol": dst_symbol,

                    "function": py_function,
                    "relation": self._render_transform_relation(
                        src_symbol=src_symbol,
                        dst_symbol=dst_symbol_for_relation,
                        py_function=py_function,
                        parameters=getattr(transformation, "parameters", None),
                    ),
                    "parameters": getattr(transformation, "parameters", None),
                }
            )

        return items

    def _get_destination_quantity_object(self, transformation):
        """
        Resolve the destination QuantityObject from the destination scale's
        scale_aspect_associations relationship.

        There is no direct dst_quantity_object relationship in the model, so
        we resolve by matching the destination aspect_id and scale_id pair.
        """

        dst_scale = getattr(transformation, "dst_scale", None)

        if dst_scale is None:
            return None

        dst_aspect_id = getattr(transformation, "dst_aspect_id", None)
        dst_scale_id = getattr(transformation, "dst_scale_id", None)

        for quantity_object in (
            getattr(dst_scale, "scale_aspect_associations", []) or []
        ):
            if (
                getattr(quantity_object, "aspect_id", None) == dst_aspect_id
                and getattr(quantity_object, "scale_id", None) == dst_scale_id
            ):
                return quantity_object

        return None

    def _get_transform_py_function(self, transformation):
            """
            Return the Python expression associated with the transformation function.
            """

            transform = getattr(transformation, "transform", None)

            if transform is None:
                return None

            return getattr(transform, "py_function", None)
    
    def _render_transform_relation(
            self,
            src_symbol,
            dst_symbol,
            py_function,
            parameters=None,
        ):
            """
            Render the Python transformation expression as a display-oriented
            mathematical relation string.

            This intentionally does not evaluate the expression. It only formats
            the stored expression for serialization/display.
            """

            if not py_function:
                return None

            expression = str(py_function).strip()

            # Light display cleanup for common Python operators.
            expression = expression.replace("**", "^")
            expression = expression.replace("*", "·")

            # If the stored expression is a lambda, make the display relation less
            # Python-specific.
            #
            # Example:
            #   lambda x, a, b: a*x + b
            # becomes:
            #   y = a·x + b
            if expression.startswith("lambda ") and ":" in expression:
                expression = expression.split(":", 1)[1].strip()
                expression = expression.replace("*", "·")

            relation = f"{dst_symbol} = {expression}"

            if parameters:
                relation = f"{relation}; parameters: {parameters}"

            return relation
    
    def _compose_quantity_object_name(self, aspect, scale):
        """
        Fallback name construction if the destination QuantityObject association
        was not loaded.
        """

        aspect_name = getattr(aspect, "name", None) if aspect else None
        scale_name = getattr(scale, "name", None) if scale else None

        unit = getattr(scale, "unit", None) if scale else None
        unit_name = getattr(unit, "name", None) if unit else None

        if aspect_name and scale_name:
            return f"{aspect_name} {scale_name}"

        if aspect_name and unit_name:
            return f"{aspect_name} {unit_name}"

        if scale_name:
            return scale_name

        if unit_name:
            return unit_name

        return None

    def _compose_quantity_object_symbol(self, aspect, scale):
        """
        Fallback symbol construction if the destination QuantityObject association
        was not loaded.
        """

        aspect_symbol = getattr(aspect, "symbol", None) if aspect else None
        scale_symbol = getattr(scale, "symbol", None) if scale else None

        unit = getattr(scale, "unit", None) if scale else None
        unit_symbol = getattr(unit, "symbol", None) if unit else None

        if aspect_symbol and scale_symbol:
            return f"{aspect_symbol} {scale_symbol}"

        if aspect_symbol and unit_symbol:
            return f"{aspect_symbol} {unit_symbol}"

        if scale_symbol:
            return scale_symbol

        if unit_symbol:
            return unit_symbol

        return None

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


class ReferenceSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = Reference
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


class ExternalReferenceSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = ExternalReference
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
    external_references = Nested(ExternalReferenceSchema, many=True)
    aspect = Nested(AspectSchema(only=("name", "id",)))
    discipline = Nested(DisciplineSchema(only=("label",)))


class QuantityObjectSchema_v1(SQLAlchemyAutoSchema):
    scale = Nested(ScaleSchema)
    aspect = Nested(AspectSchema)

    class Meta:
        model = QuantityObject
        include_relationships = True
        load_instance = True
        ordered = True

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
