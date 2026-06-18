#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from flask import make_response
from miiflask.flask.api.init import bp

from miiflask.flask.db import (
        get_session, 
        get_or_404, 
        obj_serialize_json,
        objs_serialize_json
        )

from miiflask.flask.models.mlayer import ( 
        Aspect,
        Scale,
        Unit,
        System
        )

from miiflask.flask.models.taxonomy import MeasurandTaxon

from miiflask.flask.models.schemas import (
        MeasurandTaxonSchema, 
        AspectSchema,
        ScaleSchema,
        UnitSchema,
        SystemSchema
        )

measurand_schema = MeasurandTaxonSchema()
measurands_schema = MeasurandTaxonSchema(many=True)
aspect_schema = AspectSchema()
aspects_schema = AspectSchema(many=True)
scale_schema = ScaleSchema()
scales_schema = ScaleSchema(many=True)
unit_schema = UnitSchema()
units_schema = UnitSchema(many=True)
system_schema = SystemSchema()
systems_schema = SystemSchema(many=True)


# Views for API
@bp.route("/api/aspect/<string:aspect_id>/", methods=["GET", "POST"])
def api_aspect(aspect_id):
    return obj_serialize_json(Aspect, aspect_schema, aspect_id) 


@bp.route("/api/aspects/")
def api_aspects():
    return objs_serialize_json(Aspect, aspects_schema) 


@bp.route("/api/scale/<string:scale_id>/", methods=["GET", "POST"])
def api_scale(scale_id):
    return obj_serialize_json(Scale, scale_schema, scale_id) 


@bp.route("/api/scales/")
def api_scales():
    return objs_serialize_json(Scale, scales_schema) 


@bp.route("/api/unit/<string:unit_id>/", methods=["GET", "POST"])
def api_unit(unit_id):
    return obj_serialize_json(Unit, unit_schema, unit_id) 


@bp.route("/api/units/")
def api_units():
    return objs_serialize_json(Unit, units_schema) 


@bp.route("/api/systems/")
def api_systems():
    return objs_serialize_json(System, systems_schema) 


@bp.route("/api/system/<string:system_id>/", methods=["GET", "POST"])
def api_system(system_id):
    return obj_serialize_json(System, system_schema, system_id) 


@bp.route("/api/measurand/<string:measurand_id>/", methods=["GET", "POST"])
def api_measurand(measurand_id):
    return obj_serialize_json(MeasurandTaxon, measurand_schema, measurand_id) 


@bp.route("/api/measurands/")
def api_measurands():
    return objs_serialize_json(MeasurandTaxon, measurands_schema) 
