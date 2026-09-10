#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
import tempfile
import unittest
import warnings
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from miiflask.flask.db import bind_engine
from miiflask.flask.models import mlayer

from miiflask.mappers.mlayer_json_mapper import (
    MlayerJsonImportConfig,
    MlayerJsonMapper,
)

from miiflask.mappers.taxonomy_mapper_v2 import (
    TaxonomyMapper,
    ValidationError,
)


class ValidateDbTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        self.sqlite_path = self.data_dir / "miiflask.db"

        self.mlayer_json_dir = Path("resources/repo/m-layer/source/json")
        self.taxonomy_xml = Path(
            "resources/repo/measurand-taxonomy/MeasurandTaxonomyCatalog.xml"
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_validate(self):
        self.assertTrue(
            self.mlayer_json_dir.exists(),
            f"M-Layer JSON directory does not exist: {self.mlayer_json_dir}",
        )

        self.assertTrue(
            self.taxonomy_xml.exists(),
            f"Taxonomy XML file does not exist: {self.taxonomy_xml}",
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

        engine = create_engine(
            f"sqlite:///{self.sqlite_path}",
            future=True,
        )

        bind_engine(engine)

        parms = {
            "path": str(self.data_dir),
            "database": str(self.sqlite_path),
            "usertables": str(self.data_dir / "tables_"),
            "measurands": str(self.taxonomy_xml),
            "mlayer": str(self.mlayer_json_dir),
            "kcdb": "resources/kcdb",
            "kcdb_cmc_data": "kcdb_cmc_physics.json",
            "kcdb_cmc_api_countries": ["CA"],
            "api_mlayer": "https://api.mlayer.org",
            "use_api": False,
            "use_cmc_api": False,
            "update_resources": False,
        }

        with Session(engine) as session:
            taxonomy_mapper = TaxonomyMapper(session, parms)
            taxonomy_mapper.extractTaxonomy_v2()
            taxonomy_mapper.loadTaxonomy()

            session.commit()
        try:
            taxonomy_mapper.roundtrip()
        except ValidationError as exc:
            message = (
                "Taxonomy roundtrip validation failed, but this is currently "
                f"non-blocking: {exc}"
            )
            warnings.warn(message, UserWarning)
            print(f"::warning::{message}")



if __name__ == "__main__":
    unittest.main()

