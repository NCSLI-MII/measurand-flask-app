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
import re
from typing import Any
from urllib.parse import urlsplit

CORDRA_SCHEMA_VERSION = "1.0.0"
MLAYER_SOURCE_SYSTEM = "mlayer"
REPRESENTED_QUANTITY_CONTEXT = {
    "@vocab": "https://example.org/mlayer/represented-quantity#",
    "mlayer": "https://example.org/mlayer/",
    "quantity": "https://example.org/mlayer/quantity/",
    "aspect": "https://example.org/mlayer/aspect/",
    "scale": "https://example.org/mlayer/scale/",
    "unit": "https://example.org/mlayer/unit/",
    "system": "https://example.org/mlayer/system/",
    "transforms_to": {"@id": "https://example.org/mlayer/transformsTo", "@type": "@id"},
}


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
    aspect_sources = split_references_and_sources(data.get("aspect_reference"))
    unit_sources = split_references_and_sources(data.get("unit_reference"))


    return {
        "schema_version": CORDRA_SCHEMA_VERSION,
        "object_type": "RepresentedQuantity",
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
            "sources": aspect_sources,
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
            "sources": unit_sources,
        },
        "system": {
            "symbol": data.get("system"),
            "dimensions": data.get("dimensions"),
        },
        "transforms_to": normalize_transforms_to(data.get("transforms_to")),
    }


_HTTP_URI_PATTERN = re.compile(r"https?://[^\s,;]+")


def _is_http_uri(value: str) -> bool:
    """
    Return True when value is an absolute HTTP or HTTPS URI.
    """
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _unique_strings(values: list[str]) -> list[str]:
    """
    Remove duplicate strings while preserving their original order.
    """
    return list(dict.fromkeys(values))


def split_references_and_sources(
    value: Any,
) -> tuple[list[str] | None, list[str] | None]:
    """
    Separate aspect references into URI references and textual sources.

    Examples:

        "https://example.org/a, https://example.org/b"

    becomes:

        (
            ["https://example.org/a", "https://example.org/b"],
            None,
        )

    and:

        "https://example.org/a, A textual publication citation"

    becomes:

        (
            ["https://example.org/a"],
            ["A textual publication citation"],
        )

    A list or tuple is also accepted.
    """
    if value is None:
        return None, None

    values = value if isinstance(value, (list, tuple)) else [value]

    references: list[str] = []
    citations: list[str] = []

    for raw_value in values:
        if raw_value is None:
            continue

        text = str(raw_value).strip()

        if not text:
            continue

        # Extract all HTTP/HTTPS URLs from the value.
        matches = list(_HTTP_URI_PATTERN.finditer(text))

        for match in matches:
            uri = match.group(0).rstrip(".,)")

            if _is_http_uri(uri):
                references.append(uri)

        # Remove the extracted URLs. Anything left is treated as a
        # bibliographic or textual source rather than as a URI.
        remaining_text = _HTTP_URI_PATTERN.sub("", text)
        remaining_text = remaining_text.strip(" \t\r\n,;")

        if remaining_text:
            citations.append(remaining_text)

    references = _unique_strings(references)
    citations = _unique_strings(citations)
    combined = [
        *(references or []),
        *(citations or []),
    ]

    return list(dict.fromkeys(combined)) or None
