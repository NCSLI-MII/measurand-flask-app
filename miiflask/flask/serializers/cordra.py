#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

# miiflask/flask/serializers/cordra.py

"""
Cordra serialization helpers for mlayer objects.

This module intentionally contains pure functions so that the Cordra
serialization contract can be tested independently of Flask routes,
database sessions, and the external Cordra API.
"""

from __future__ import annotations

import ast
import json
from typing import Any


CORDRA_SCHEMA_VERSION = "1.0.0"
CORDRA_OBJECT_TYPE = "MlayerQuantityObject"
MLAYER_SOURCE_SYSTEM = "mlayer"


def parse_transform_parameters(parameters: Any) -> Any:
    """
    Normalize transformation parameters into a JSON-compatible structure.

    Existing mlayer data may represent parameters as:
      - None
      - dict
      - valid JSON string, e.g. '{"a": "1E+3"}'
      - Python literal dict string, e.g. "{'a': '1E+3'}"

    For Cordra serialization, parameters should ideally be a JSON object,
    represented in Python as a dict.

    If parsing fails, return the original value. This keeps the serializer
    non-destructive while allowing tests to enforce expected cases.
    """
    if parameters is None:
        return None

    if isinstance(parameters, dict):
        return parameters

    if isinstance(parameters, str):
        value = parameters.strip()

        if not value:
            return None

        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        return parameters

    return parameters



def normalize_transforms_to(transforms_to: Any) -> list[dict[str, Any]]:
    if not transforms_to:
        return []

    normalized = []

    for transform in transforms_to:
        transform_data = dict(transform)
        transform_data["parameters"] = parse_transform_parameters(
            transform_data.get("parameters")
        )
        normalized.append(transform_data)

    return sorted(
        normalized,
        key=lambda item: (
            item.get("aspect_id") or "",
            item.get("scale_id") or "",
            item.get("kind") or "",
        ),
    )


def quantity_object_to_cordra_content(data: dict[str, Any]) -> dict[str, Any]:
    """
    Map a flattened QuantityObjectSchema-style dictionary to the Cordra
    MlayerQuantityObject content model.

    Expected input resembles the current mlayer API serialization:

        {
            "aspect_id": "AS2",
            "scale_id": "SC1",
            "name": "mass ratio kilogram",
            ...
        }

    Output is Cordra-ready object content. The external synchronization
    application can send this dictionary to Cordra as the object content.
    """
    aspect_id = data.get("aspect_id")
    scale_id = data.get("scale_id")

    natural_id = data.get("natural_id") or f"{aspect_id}:{scale_id}"

    return {
        "schema_version": CORDRA_SCHEMA_VERSION,
        "object_type": CORDRA_OBJECT_TYPE,
        "mlayer": {
            "natural_id": natural_id,
            "aspect_id": aspect_id,
            "scale_id": scale_id,
            "source_system": MLAYER_SOURCE_SYSTEM,
            "source_endpoint": f"/api/represented_quantity/{aspect_id}/{scale_id}/",
        },
        "quantity": {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "sources": data.get("sources"),
        },
        "aspect": {
            "id": aspect_id,
            "name": data.get("aspect_name"),
            "symbol": data.get("aspect_symbol"),
            "reference": data.get("aspect_reference"),
        },
        "scale": {
            "id": scale_id,
            "name": data.get("scale_name"),
            "symbol": data.get("scale_symbol"),
            "type": data.get("scale_type"),
        },
        "unit": {
            "id": data.get("unit_id"),
            "name": data.get("unit_name"),
            "symbol": data.get("unit_symbol"),
            "reference": data.get("unit_reference"),
        },
        "system": {
            "symbol": data.get("system"),
            "dimensions": data.get("dimensions"),
        },
        "transforms_to": normalize_transforms_to(data.get("transforms_to")),
    }

