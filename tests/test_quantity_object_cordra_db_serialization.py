#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.


"""
Database-backed tests for converting mlayer QuantityObject records into
Cordra MlayerQuantityObject content.

These tests intentionally do not call:
  - Flask API endpoints
  - Cordra endpoints
  - mocked HTTP responses

Instead, they validate the internal contract:

    mlayer JSON import
        -> SQLAlchemy QuantityObject
        -> QuantityObjectSchema serialization
        -> Cordra content mapping

This is intended to sit beside test_validate_db_json.py and provide
coverage for the Cordra serialization path.
"""

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine
from miiflask.flask.models import mlayer
from miiflask.flask.models.mlayer import QuantityObject
from miiflask.flask.models.schemas import QuantityObjectSchema
from miiflask.flask.serializers.cordra import (
    parse_transform_parameters,
    quantity_object_to_cordra_content,
    REPRESENTED_QUANTITY_CONTEXT,
)
from miiflask.mappers.mlayer_json_mapper import (
    MlayerJsonImportConfig,
    MlayerJsonMapper,
)


class QuantityObjectCordraDbSerializationTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        self.sqlite_path = self.data_dir / "miiflask.db"

        self.mlayer_json_dir = Path("resources/repo/m-layer/source/json")

        self.assertTrue(
            self.mlayer_json_dir.exists(),
            f"M-Layer JSON directory does not exist: {self.mlayer_json_dir}",
        )

        mlayer_config = MlayerJsonImportConfig(
            json_dir=self.mlayer_json_dir,
            sqlite_path=self.sqlite_path,
            drop_create=True,
            strict=True,
            batch_size=1000,
        )

        mlayer_mapper = MlayerJsonMapper(
            config=mlayer_config,
            models_module=mlayer,
        )

        mlayer_mapper.run()

        self.engine = create_engine(
            f"sqlite:///{self.sqlite_path}",
            future=True,
        )

        bind_engine(self.engine)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _get_mass_ratio_kilogram_quantity_object(self, session):
        """
        Retrieve the mass ratio kilogram QuantityObject from the imported
        mlayer test database.

        Expected natural key:
            aspect_id = AS2
            scale_id = SC1
        """
        stmt = select(QuantityObject).where(
            QuantityObject.aspect_id == "AS2",
            QuantityObject.scale_id == "SC1",
        )

        quantity_object = session.scalars(stmt).one_or_none()

        self.assertIsNotNone(
            quantity_object,
            "Expected QuantityObject AS2/SC1, mass ratio kilogram, "
            "to exist in imported mlayer JSON database.",
        )

        return quantity_object

    def _serialize_mass_ratio_kilogram(self):
        """
        Import and serialize the AS2/SC1 QuantityObject using the actual
        application schema.
        """
        with Session(self.engine) as session:
            quantity_object = self._get_mass_ratio_kilogram_quantity_object(session)

            schema = QuantityObjectSchema()
            serialized = schema.dump(quantity_object)

        return serialized

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
        serialized = self._serialize_mass_ratio_kilogram()

        cordra_content = quantity_object_to_cordra_content(serialized)

        self.assertEqual(cordra_content["schema_version"], "1.0.0")
        self.assertEqual(cordra_content["object_type"], "RepresentedQuantity")
        # self.assertEqual(cordra_content["@context"], REPRESENTED_QUANTITY_CONTEXT)

        self.assertIn("mlayer", cordra_content)
        self.assertIn("quantity", cordra_content)
        self.assertIn("aspect", cordra_content)
        self.assertIn("scale", cordra_content)
        self.assertIn("unit", cordra_content)
        self.assertIn("system", cordra_content)
        self.assertIn("transforms_to", cordra_content)

        self.assertEqual(cordra_content["mlayer"]["natural_id"], "AS2:SC1")
        self.assertEqual(cordra_content["mlayer"]["aspect_id"], "AS2")
        self.assertEqual(cordra_content["mlayer"]["scale_id"], "SC1")
        self.assertEqual(cordra_content["mlayer"]["source_system"], "mlayer")
        self.assertEqual(
            cordra_content["mlayer"]["source_endpoint"],
            "/api/represented_quantity/AS2/SC1/",
        )

        self.assertEqual(
            cordra_content["quantity"]["name"],
            "mass ratio kilogram",
        )
        self.assertEqual(cordra_content["quantity"]["symbol"], "ratio kg")

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

        self.assertEqual(cordra_content["scale"]["id"], "SC1")
        self.assertEqual(cordra_content["scale"]["name"], "ratio kilogram")
        self.assertEqual(cordra_content["scale"]["symbol"], "ratio kg")
        self.assertEqual(cordra_content["scale"]["type"], "ratio")

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

        self.assertEqual(cordra_content["system"]["symbol"], "SI")
        self.assertEqual(
            cordra_content["system"]["dimensions"],
            "[0,1,0,0,0,0,0]",
        )

        self.assertIsInstance(cordra_content["transforms_to"], list)

        self.assertGreater(
            len(cordra_content["transforms_to"]),
            0,
            "Expected mass ratio kilogram to have at least one outgoing "
            "transformation.",
        )

        first_transform = cordra_content["transforms_to"][0]

        self.assertIn("kind", first_transform)
        self.assertIn("is_cast", first_transform)

        self.assertIn("aspect_scale", first_transform)
        self.assertIsInstance(first_transform["aspect_scale"], dict)
        self.assertIn("aspect_id", first_transform["aspect_scale"])
        self.assertIn("scale_id", first_transform["aspect_scale"])
        self.assertIsInstance(first_transform["aspect_scale"]["aspect_id"], str)
        self.assertIsInstance(first_transform["aspect_scale"]["scale_id"], str)

        self.assertIn("name", first_transform)
        self.assertIn("symbol", first_transform)
        self.assertIn("function", first_transform)
        self.assertIn("parameters", first_transform)
        self.assertIn("relation", first_transform)

    def test_quantity_object_cordra_content_uses_json_object_for_transform_parameters(
        self,
    ):
        serialized = self._serialize_mass_ratio_kilogram()

        cordra_content = quantity_object_to_cordra_content(serialized)

        transforms_to = cordra_content["transforms_to"]

        self.assertGreater(
            len(transforms_to),
            0,
            "Expected AS2/SC1 mass ratio kilogram to have transforms_to data.",
        )

        transforms_with_parameters = [
            transform
            for transform in transforms_to
            if transform.get("parameters") is not None
        ]

        self.assertGreater(
            len(transforms_with_parameters),
            0,
            "Expected at least one transform to contain parameters.",
        )

        for transform in transforms_with_parameters:
            parameters = transform["parameters"]

            self.assertIsInstance(
                parameters,
                dict,
                f"Expected transform parameters to be a JSON object/dict, "
                f"got {type(parameters).__name__}: {parameters!r}",
            )

    def test_mass_ratio_kilogram_golden_cordra_payload(self):
        serialized = self._serialize_mass_ratio_kilogram()

        cordra_content = quantity_object_to_cordra_content(serialized)

        expected_without_transforms = {
            "schema_version": "1.0.0",
            "object_type": "RepresentedQuantity",
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
                "reference": "https://si-digital-framework.org/quantities/MASS",
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
                "reference": "https://si-digital-framework.org/SI/units/kilogram",
            },
            "system": {
                "symbol": "SI",
                "dimensions": "[0,1,0,0,0,0,0]",
            },
        }

        actual_without_transforms = {
            key: value
            for key, value in cordra_content.items()
            if key != "transforms_to"
        }

        self.assertEqual(
            actual_without_transforms,
            expected_without_transforms,
        )

        self.assertIn("transforms_to", cordra_content)
        self.assertIsInstance(cordra_content["transforms_to"], list)

        self.assertGreater(
            len(cordra_content["transforms_to"]),
            0,
            "Golden payload test expects mass ratio kilogram to include "
            "outgoing transforms.",
        )

        expected_transform_subset = {
            "aspect_name": "mass",
            "aspect_scale": {
                "aspect_id": "AS2",
                "scale_id": "SC86",
            },
            "function": "lambda x: a*x",
            "is_cast": False,
            "kind": "conversion",
            "name": "mass ratio gram",
            "parameters": {
                "a": "1E+3",
            },
            "scale_name": "ratio gram",
            "symbol": "ratio g",
        }

        gram_transform = None

        for transform in cordra_content["transforms_to"]:
            aspect_scale = transform.get("aspect_scale") or {}

            if (
                aspect_scale.get("aspect_id") == "AS2"
                and aspect_scale.get("scale_id") == "SC86"
            ):
                gram_transform = transform
                break

        self.assertIsNotNone(
            gram_transform,
            "Expected golden payload to include transform from AS2/SC1 "
            "mass ratio kilogram to AS2/SC86 mass ratio gram.",
        )

        for key, expected_value in expected_transform_subset.items():
            self.assertEqual(
                gram_transform.get(key),
                expected_value,
                f"Unexpected value for transform field {key!r}",
            )

        self.assertIn("relation", gram_transform)
        self.assertIsInstance(gram_transform["relation"], str)
        self.assertIn("ratio g", gram_transform["relation"])
        self.assertIn("parameters", gram_transform["relation"])


if __name__ == "__main__":
    unittest.main()
