#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

""" """
# tests/test_quantity_object_cordra_serialization.py
#! /usr/bin/env python3
# vim:fenc=utf-8

"""
Tests for converting mlayer quantity object serializations into Cordra
MlayerQuantityObject content.

These tests do not require a Flask test client, a running API endpoint, or
a live Cordra instance. They validate the serialization contract that the
future API and external Cordra synchronization application will rely on.
"""

import unittest

from miiflask.flask.serializers.cordra import (
    REPRESENTED_QUANTITY_CONTEXT,
    parse_transform_parameters,
    quantity_object_to_cordra_content,
    split_references_and_sources,
)


def mass_ratio_kilogram_serialized_quantity_object(transforms_to=None):
    """
    Return a representative flattened QuantityObjectSchema-style dictionary
    for mass ratio kilogram.

    This mirrors the shape currently emitted by the mlayer quantity object
    JSON serialization rather than the final Cordra content structure.
    """
    return {
        "natural_id": "AS2:SC1",
        "aspect_id": "AS2",
        "scale_id": "SC1",
        "aspect_name": "mass",
        "aspect_reference": "https://si-digital-framework.org/quantities/MASS",
        "aspect_symbol": None,
        "dimensions": "[0,1,0,0,0,0,0]",
        "name": "mass ratio kilogram",
        "scale_name": "ratio kilogram",
        "scale_symbol": "ratio kg",
        "scale_type": "ratio",
        "symbol": "ratio kg",
        "system": "SI",
        "sources": None,
        "unit_id": "UN1",
        "unit_name": "kilogram",
        "unit_reference": "https://si-digital-framework.org/SI/units/kilogram",
        "unit_symbol": "kg",
        "cordra_id": None,
        "transforms_to": transforms_to if transforms_to is not None else [],
    }


def mass_ratio_gram_transform(parameters=None):
    """
    Return a representative transform from kilogram to gram.
    """
    return {
        "aspect_scale": {
            "aspect_id": "AS2",
            "scale_id": "SC86",
        },
        "aspect_name": "mass",
        "function": "lambda x: a*x",
        "is_cast": False,
        "kind": "conversion",
        "name": "mass ratio gram",
        "parameters": parameters if parameters is not None else {"a": "1E+3"},
        "relation": "ratio g = a·x; parameters: {'a':'1E+3'}",
        "scale_id": "SC86",
        "scale_name": "ratio gram",
        "symbol": "ratio g",
    }


class QuantityObjectCordraSerializationTestCase(unittest.TestCase):
    def test_parse_transform_parameters_accepts_dict(self):
        parameters = {"a": "1E+3"}

        parsed = parse_transform_parameters(parameters)

        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed, {"a": "1E+3"})

    def test_parse_transform_parameters_accepts_json_string(self):
        parameters = '{"a": "1E+3"}'

        parsed = parse_transform_parameters(parameters)

        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed, {"a": "1E+3"})

    def test_parse_transform_parameters_accepts_python_literal_dict_string(self):
        parameters = "{'a': '1E+3'}"

        parsed = parse_transform_parameters(parameters)

        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed, {"a": "1E+3"})

    def test_quantity_object_to_cordra_content_maps_required_fields(self):
        serialized_quantity_object = mass_ratio_kilogram_serialized_quantity_object(
            transforms_to=[
                mass_ratio_gram_transform(parameters={"a": "1E+3"}),
            ]
        )

        cordra_content = quantity_object_to_cordra_content(serialized_quantity_object)

        self.assertEqual(cordra_content["schema_version"], "1.0.0")
        self.assertEqual(cordra_content["object_type"], "RepresentedQuantity")

        self.assertEqual(
            cordra_content["mlayer"],
            {
                "natural_id": "AS2:SC1",
                "aspect_id": "AS2",
                "scale_id": "SC1",
                "source_system": "mlayer",
                "source_endpoint": "/api/represented_quantity/AS2/SC1/",
            },
        )

        self.assertEqual(
            cordra_content["quantity"],
            {
                "name": "mass ratio kilogram",
                "symbol": "ratio kg",
                "sources": None,
            },
        )

        self.assertEqual(
            cordra_content["aspect"],
            {
                "id": "AS2",
                "name": "mass",
                "symbol": None,
                "sources": [
                    "https://si-digital-framework.org/quantities/MASS",
                ],
            },
        )

        self.assertEqual(
            cordra_content["scale"],
            {
                "id": "SC1",
                "name": "ratio kilogram",
                "symbol": "ratio kg",
                "type": "ratio",
            },
        )

        self.assertEqual(
            cordra_content["unit"],
            {
                "id": "UN1",
                "name": "kilogram",
                "symbol": "kg",
                "sources": [
                    "https://si-digital-framework.org/SI/units/kilogram",
                ],
            },
        )

        self.assertEqual(
            cordra_content["system"],
            {
                "symbol": "SI",
                "dimensions": "[0,1,0,0,0,0,0]",
            },
        )

        self.assertIn("transforms_to", cordra_content)
        self.assertEqual(len(cordra_content["transforms_to"]), 1)

        transform = cordra_content["transforms_to"][0]

        self.assertEqual(transform["kind"], "conversion")
        self.assertFalse(transform["is_cast"])
        self.assertEqual(
            transform["aspect_scale"],
            {
                "aspect_id": "AS2",
                "scale_id": "SC86",
            },
        )

        self.assertEqual(transform["name"], "mass ratio gram")
        self.assertEqual(transform["symbol"], "ratio g")
        self.assertEqual(transform["function"], "lambda x: a*x")
        self.assertEqual(transform["parameters"], {"a": "1E+3"})

    def test_quantity_object_cordra_content_uses_json_object_for_transform_parameters(
        self,
    ):
        serialized_quantity_object = mass_ratio_kilogram_serialized_quantity_object(
            transforms_to=[
                mass_ratio_gram_transform(parameters="{'a': '1E+3'}"),
            ]
        )

        cordra_content = quantity_object_to_cordra_content(serialized_quantity_object)

        parameters = cordra_content["transforms_to"][0]["parameters"]

        self.assertIsInstance(parameters, dict)
        self.assertEqual(parameters, {"a": "1E+3"})
        self.assertEqual(parameters["a"], "1E+3")

    def test_mass_ratio_kilogram_golden_cordra_payload(self):
        serialized_quantity_object = mass_ratio_kilogram_serialized_quantity_object(
            transforms_to=[]
        )

        expected = {
            "schema_version": "1.0.0",
            "object_type": "RepresentedQuantity",
            # "@context": REPRESENTED_QUANTITY_CONTEXT,
            "mlayer": {
                "natural_id": "AS2:SC1",
                "aspect_id": "AS2",
                "scale_id": "SC1",
                "source_system": "mlayer",
                "source_endpoint": "/api/represented_quantity/AS2/SC1/",
            },
            "quantity": {
                "name": "mass ratio kilogram",
                "symbol": "ratio kg",
                "sources": None,
            },
            "aspect": {
                "id": "AS2",
                "name": "mass",
                "symbol": None,
                "sources": [
                    "https://si-digital-framework.org/quantities/MASS",
                ],
            },
            "scale": {
                "id": "SC1",
                "name": "ratio kilogram",
                "symbol": "ratio kg",
                "type": "ratio",
            },
            "unit": {
                "id": "UN1",
                "name": "kilogram",
                "symbol": "kg",
                "sources": [
                    "https://si-digital-framework.org/SI/units/kilogram",
                ],
            },
            "system": {
                "symbol": "SI",
                "dimensions": "[0,1,0,0,0,0,0]",
            },
            "transforms_to": [],
        }

        actual = quantity_object_to_cordra_content(serialized_quantity_object)

        self.assertEqual(actual, expected)

    def test_split_references_and_sources_preserves_urls_and_citations(self):
        value = (
            "https://cie.co.at/eilvterm/17-21-050, "
            "The CIE system of physical photometry "
            "(ISO/CIE 23539:2023)"
        )

        sources = split_references_and_sources(value)

        self.assertEqual(
            sources,
            [
                "https://cie.co.at/eilvterm/17-21-050",
                ("The CIE system of physical photometry (ISO/CIE 23539:2023)"),
            ],
        )

    def test_textual_unit_reference_is_serialized_as_a_source(self):
        serialized_quantity_object = mass_ratio_kilogram_serialized_quantity_object()
        serialized_quantity_object["unit_reference"] = "SI Brochure"

        cordra_content = quantity_object_to_cordra_content(serialized_quantity_object)

        self.assertEqual(
            cordra_content["unit"]["sources"],
            ["SI Brochure"],
        )
        self.assertNotIn("reference", cordra_content["unit"])

    def test_serializer_does_not_emit_reference_properties(self):
        serialized_quantity_object = mass_ratio_kilogram_serialized_quantity_object()

        cordra_content = quantity_object_to_cordra_content(serialized_quantity_object)

        self.assertNotIn("reference", cordra_content["aspect"])
        self.assertNotIn("reference", cordra_content["unit"])


if __name__ == "__main__":
    unittest.main()
