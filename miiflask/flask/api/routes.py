#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from flask import make_response, jsonify
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
        System,
        QuantityObject
        )

from miiflask.flask.models.taxonomy import MeasurandTaxon

from miiflask.flask.models.schemas import (
        MeasurandTaxonSchema, 
        AspectSchema,
        ScaleSchema,
        UnitSchema,
        SystemSchema,
        QuantityObjectSchema
        )

from miiflask.flask.serializers import quantity_object_to_cordra_content

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
quantityobject_schema = QuantityObjectSchema()
quantityobjects_schema = QuantityObjectSchema(many=True)



bp.route("/api/represented_quantities/", methods=["GET"])
def api_represented_quantities():
    """
    List quantity object representations.

    Optional query parameters:
      missing_cordra_id=true
      limit=100
      offset=0
    """
    session = get_session()

    missing_cordra_id = request.args.get("missing_cordra_id", "").lower()
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)

    limit = min(max(limit, 1), 1000)
    offset = max(offset, 0)

    stmt = (
        select(QuantityObject)
        .options(
            selectinload(QuantityObject.scale),
            selectinload(QuantityObject.aspect),
            selectinload(QuantityObject.transformations)
        )
        .order_by(QuantityObject.aspect_id, QuantityObject.scale_id)
        .limit(limit)
        .offset(offset)
    )

    if missing_cordra_id in ("true", "1", "yes"):
        stmt = stmt.where(QuantityObject.cordra_id.is_(None))

    objects = session.scalars(stmt).all()

    return jsonify({
        "limit": limit,
        "offset": offset,
        "count": len(objects),
        "items": quantityobjects_schema.dump(objects)
    })


# Views for API
@bp.route("/api/represented_quantity/<string:aspect_id>/<string:scale_id>/", methods=["GET"])
def api_represented_quantity(aspect_id, scale_id):
    session = get_session()
    qo = session.get(
        QuantityObject,
        {
            "scale_id": scale_id,
            "aspect_id": aspect_id,
        }
    )

    if qo is None:
        abort(404)
    data = quantityobject_schema.dump(qo)
    return data


@bp.route(
    "/api/represented_quantity/<string:aspect_id>/<string:scale_id>/cordra-content/",
    methods=["GET"]
)
def api_represented_quantity_cordra_content(aspect_id, scale_id):
    session = get_session()

    qo = session.get(
        QuantityObject,
        {
            "scale_id": scale_id,
            "aspect_id": aspect_id,
        }
    )

    if qo is None:
        abort(404)

    data = quantityobject_schema.dump(qo)
    cordra_content = quantity_object_to_cordra_content(data)

    return jsonify(cordra_content)


@bp.route(
    "/api/represented_quantity/<string:aspect_id>/<string:scale_id>/cordra/",
    methods=["PATCH"]
)
def api_update_represented_quantity_cordra_id(aspect_id, scale_id):
    """
    Update the Cordra identifier for a represented quantity.

    Expected request body:
      {
        "cordra_id": "..."
      }
    """
    session = get_session()

    payload = request.get_json(silent=True) or {}
    cordra_id = payload.get("cordra_id")

    if not cordra_id:
        return jsonify({
            "error": "Missing required field: cordra_id"
        }), 400

    qo = session.get(
        QuantityObject,
        {
            "scale_id": scale_id,
            "aspect_id": aspect_id,
        }
    )

    if qo is None:
        abort(404)

    qo.cordra_id = cordra_id
    session.add(qo)
    session.commit()

    return jsonify(quantityobject_schema.dump(qo))


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
