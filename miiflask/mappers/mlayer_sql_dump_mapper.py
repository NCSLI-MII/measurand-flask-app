#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""
Class-based M-Layer PostgreSQL dump importer.

This module is designed to sit beside mlayer_mapper.py and provide a comparable
programmatic interface for building the application's database from a raw
PostgreSQL plain-text pg_dump instead of JSON/API data.

Typical programmatic usage:

    from pathlib import Path
    import mlayer

    from mlayer_sql_dump_mapper import (
        MlayerDumpImportConfig,
        MlayerSqlDumpMapper,
    )

    config = MlayerDumpImportConfig(
        dump_path=Path("m_layer_v5.86.dmp"),
        sqlite_path=Path("mlayer.sqlite"),
        drop_create=True,
    )

    mapper = MlayerSqlDumpMapper(config=config, models_module=mlayer)
    mapper.run()

CLI usage:

    python mlayer_sql_dump_mapper.py \
        --dump m_layer_v5.86.dmp \
        --sqlite mlayer.sqlite \
        --models mlayer \
        --drop-create
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import Boolean, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


LOG = logging.getLogger("mlayer_sql_dump_mapper")


@dataclass
class CopyBlock:
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass
class ImportResult:
    inserted_counts: dict[str, int]
    derived_quantity_objects: int = 0
    updated_dimension_systematic_scales: int = 0
    updated_quantity_object_fields: int = 0


@dataclass
class MlayerDumpImportConfig:
    dump_path: Path
    sqlite_path: Path | None = None
    database_url: str | None = None
    drop_create: bool = False
    strict: bool = False
    batch_size: int = 1000
    echo_sql: bool = False
    disable_sqlite_foreign_keys_during_import: bool = True
    skip_post_processing: bool = False
    skip_quantity_object_derivation: bool = False
    skip_quantity_object_name_update: bool = False
    skip_dimension_systematic_scale_update: bool = False


class PgDumpCopyParser:
    """
    Parses PostgreSQL plain-text pg_dump COPY blocks.

    This is intentionally focused on data extraction. Schema DDL is ignored
    because the target database schema is created from SQLAlchemy metadata.
    """

    COPY_RE = re.compile(
        r"^COPY\s+(?P<table>[^\s(]+)\s*\((?P<columns>[^)]*)\)\s+FROM\s+stdin;",
        re.IGNORECASE,
    )

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or LOG

    def parse(self, dump_path: Path) -> list[CopyBlock]:
        blocks: list[CopyBlock] = []

        in_copy = False
        current_table: str | None = None
        current_columns: list[str] = []
        current_rows: list[dict[str, Any]] = []

        def finish_current() -> None:
            nonlocal in_copy, current_table, current_columns, current_rows

            if in_copy and current_table is not None:
                blocks.append(
                    CopyBlock(
                        table_name=current_table,
                        columns=current_columns,
                        rows=current_rows,
                    )
                )

            in_copy = False
            current_table = None
            current_columns = []
            current_rows = []

        with dump_path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\n")

                header = self.parse_copy_header(line)

                if header:
                    if in_copy:
                        self.logger.warning(
                            "COPY block for %s was not terminated before line %s; closing it",
                            current_table,
                            line_number,
                        )
                        finish_current()

                    current_table, current_columns = header
                    current_rows = []
                    in_copy = True
                    continue

                if not in_copy:
                    continue

                if line == r"\.":
                    finish_current()
                    continue

                if not line:
                    continue

                if line.startswith("--"):
                    self.logger.warning(
                        "Comment encountered inside COPY block %s at line %s; closing block",
                        current_table,
                        line_number,
                    )
                    finish_current()
                    continue

                values = line.split("\t")

                if len(values) != len(current_columns):
                    self.logger.warning(
                        "Skipping malformed COPY row at line %s for table %s: "
                        "expected %s columns, got %s",
                        line_number,
                        current_table,
                        len(current_columns),
                        len(values),
                    )
                    continue

                row = {
                    col: self.pg_unescape_copy_value(value)
                    for col, value in zip(current_columns, values)
                }
                current_rows.append(row)

        finish_current()
        return blocks

    @classmethod
    def parse_copy_header(cls, line: str) -> tuple[str, list[str]] | None:
        match = cls.COPY_RE.match(line)

        if not match:
            return None

        table_name = cls.normalize_table_name(match.group("table"))
        columns = [col.strip().strip('"') for col in match.group("columns").split(",")]
        return table_name, columns

    @staticmethod
    def normalize_table_name(raw_name: str) -> str:
        name = raw_name.strip()
        parts = [part.strip().strip('"') for part in name.split(".")]
        return parts[-1]

    @staticmethod
    def pg_unescape_copy_value(value: str | None) -> Any:
        if value is None:
            return None

        if value == r"\N":
            return None

        replacements = {
            r"\b": "\b",
            r"\f": "\f",
            r"\n": "\n",
            r"\r": "\r",
            r"\t": "\t",
            r"\v": "\v",
            r"\\": "\\",
        }

        for src, dst in replacements.items():
            value = value.replace(src, dst)

        return value


class MlayerDumpTransforms:
    """
    PostgreSQL dump value normalization and model-specific transforms.
    """

    @staticmethod
    def strip_outer_pg_quotes(value: Any) -> Any:
        if not isinstance(value, str):
            return value

        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            return value[1:-1]

        return value

    @staticmethod
    def coerce_bool(value: Any) -> bool | None:
        """
        Convert PostgreSQL/JSON boolean-ish values to real Python bools.

        This prevents SQLAlchemy Boolean columns from receiving raw 't'/'f'
        strings from pg_dump COPY data.
        """
        if value is None or value == "":
            return None

        if isinstance(value, bool):
            return value

        text = str(value).strip().lower()

        if text in {"t", "true", "1", "yes", "y"}:
            return True

        if text in {"f", "false", "0", "no", "n"}:
            return False

        raise ValueError(f"Cannot coerce to bool: {value!r}")

    @staticmethod
    def coerce_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    @classmethod
    def coerce_float(cls, value: Any) -> float | None:
        if value is None or value == "":
            return None

        value = cls.strip_outer_pg_quotes(value)
        return float(str(value))

    @classmethod
    def coerce_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(cls.strip_outer_pg_quotes(value))

    @staticmethod
    def parse_pg_array_as_reference(value: Any) -> str | None:
        """
        Convert PostgreSQL text[] values to the application reference string.

        Examples:
            {}                           -> None
            {https://example.org}        -> https://example.org
            {"NIST Special Publication"} -> NIST Special Publication
            {a,b}                        -> a; b
        """
        if value is None:
            return None

        value = str(value).strip()

        if value == "{}":
            return None

        if value.startswith("{") and value.endswith("}"):
            inner = value[1:-1]

            if not inner:
                return None

            try:
                reader = csv.reader([inner], delimiter=",", quotechar='"', escapechar="\\")
                items = next(reader)
                items = [item.strip() for item in items if item.strip()]
                return "; ".join(items) if items else None
            except Exception:
                return inner

        return value

    @staticmethod
    def normalise_parameters(value: Any) -> str | None:
        """
        Keep conversion/cast parameters as text because the current ORM uses text.
        """
        if value is None:
            return None

        text = str(value).strip()

        if text == "":
            return None

        if text == "{}":
            return "{}"

        try:
            parsed = ast.literal_eval(text)
            return repr(parsed)
        except Exception:
            return text

    @staticmethod
    def normalise_aspect_name(value: Any) -> Any:
        """
        Match mlayer_mapper.py behaviour for Aspect.name.
        """
        if value is None:
            return None

        text = str(value)

        if text == "electric potential difference":
            text = "voltage"

        return text.replace(" ", "-")

    @classmethod
    def build_transforms(cls) -> dict[str, dict[str, Callable[[Any], Any]]]:
        source_ref = cls.parse_pg_array_as_reference

        return {
            "aspect": {
                "name": cls.normalise_aspect_name,
                "reference": source_ref,
            },
            "prefix": {
                "numerator": cls.coerce_float,
                "denominator": cls.coerce_float,
                "reference": source_ref,
            },
            "unit": {
                "reference": source_ref,
            },
            "system": {
                "n": cls.coerce_int,
                "reference": source_ref,
            },
            "dimension": {
                "is_quotient": cls.coerce_bool,
            },
            "scale": {
                "is_systematic": cls.coerce_bool,
                "is_special": cls.coerce_bool,
                "is_augmented": cls.coerce_bool,
                "reference": source_ref,
            },
            "quantityobject_table": {
                "reference": source_ref,
            },
            "conversion": {
                "parameters": cls.normalise_parameters,
            },
            "cast": {
                "parameters": cls.normalise_parameters,
            },
        }


class MlayerModelRegistry:
    """
    Small helper around the SQLAlchemy model module.

    The mapper intentionally discovers by __tablename__, since your application
    models use semantic class names but table names are what the dump maps to.
    """

    def __init__(self, models_module: Any) -> None:
        self.models_module = models_module
        self.models_by_table = self.discover_model_classes(models_module)

    @staticmethod
    def discover_model_classes(models_module: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for name in dir(models_module):
            obj = getattr(models_module, name)
            table_name = getattr(obj, "__tablename__", None)
            if table_name:
                result[table_name] = obj

        return result

    @property
    def Base(self) -> Any:
        if not hasattr(self.models_module, "Base"):
            raise RuntimeError("Model module does not expose Base")
        return self.models_module.Base

    def get(self, table_name: str) -> Any | None:
        return self.models_by_table.get(table_name)

    def require(self, table_name: str) -> Any:
        model = self.get(table_name)

        if model is None:
            raise RuntimeError(f"ORM model with __tablename__={table_name!r} was not found")

        return model


class MlayerSqlDumpMapper:
    """
    Mapper/importer analogous to mlayer_mapper.MlayerMapper, but for raw
    PostgreSQL dump data.

    This class is intended to be reusable from scripts, CLI commands, tests,
    admin tools, notebooks, etc.
    """

    def __init__(
        self,
        config: MlayerDumpImportConfig,
        models_module: Any,
        session: Session | None = None,
        engine: Engine | None = None,
        parser: PgDumpCopyParser | None = None,
        transforms: type[MlayerDumpTransforms] = MlayerDumpTransforms,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.models_module = models_module
        self.registry = MlayerModelRegistry(models_module)
        self.external_session = session
        self.engine = engine
        self.parser = parser or PgDumpCopyParser(logger=logger or LOG)
        self.transforms_cls = transforms
        self.transforms = transforms.build_transforms()
        self.logger = logger or LOG

        self.blocks: list[CopyBlock] = []
        self.inserted_counts: dict[str, int] = defaultdict(int)

    def run(self) -> ImportResult:
        """
        Full import lifecycle:
        - parse dump
        - create/drop database schema as configured
        - import rows
        - run mapper-aligned post-processing
        - verify counts
        """
        self.blocks = self.load_blocks()

        if self.external_session is not None:
            return self._run_with_session(self.external_session)

        engine = self.engine or self.create_engine()
        self.prepare_schema(engine)

        SessionLocal = sessionmaker(bind=engine, future=True)

        with SessionLocal() as session:
            try:
                result = self._run_with_session(session)
                session.commit()
                return result
            except Exception:
                session.rollback()
                self.logger.exception("Import failed; transaction rolled back")
                raise

    def _run_with_session(self, session: Session) -> ImportResult:
        inserted_counts = self.import_blocks(session)

        result = ImportResult(inserted_counts=dict(inserted_counts))

        if not self.config.skip_post_processing:
            if not self.config.skip_dimension_systematic_scale_update:
                result.updated_dimension_systematic_scales = (
                    self.update_dimension_systematic_scales(session)
                )

            if not self.config.skip_quantity_object_derivation:
                result.derived_quantity_objects = (
                    self.ensure_quantity_objects_from_conversion_cast(session)
                )

            if not self.config.skip_quantity_object_name_update:
                result.updated_quantity_object_fields = (
                    self.update_quantity_object_names(session)
                )

        self.verify_counts(session, inserted_counts)
        return result

    def load_blocks(self) -> list[CopyBlock]:
        self.logger.info("Parsing dump: %s", self.config.dump_path)
        blocks = self.parser.parse(self.config.dump_path)

        self.logger.info("Found %s COPY blocks", len(blocks))
        for block in blocks:
            self.logger.info(
                "  %-20s rows=%s columns=%s",
                block.table_name,
                len(block.rows),
                ",".join(block.columns),
            )

        return blocks

    def create_engine(self) -> Engine:
        if self.config.database_url:
            database_url = self.config.database_url
        elif self.config.sqlite_path:
            database_url = f"sqlite:///{self.config.sqlite_path}"
        else:
            raise ValueError("Either database_url or sqlite_path must be provided")

        engine = create_engine(
            database_url,
            future=True,
            echo=self.config.echo_sql,
        )

        if database_url.startswith("sqlite"):
            event.listen(engine, "connect", self._set_sqlite_pragmas)

        return engine

    def _set_sqlite_pragmas(self, dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()

        if self.config.disable_sqlite_foreign_keys_during_import:
            cursor.execute("PRAGMA foreign_keys=OFF")
        else:
            cursor.execute("PRAGMA foreign_keys=ON")

        cursor.close()

    def prepare_schema(self, engine: Engine) -> None:
        if self.config.drop_create:
            self.logger.warning("Dropping and recreating ORM tables")
            self.registry.Base.metadata.drop_all(engine)

        self.registry.Base.metadata.create_all(engine)

    def import_blocks(self, session: Session) -> dict[str, int]:
        self.inserted_counts = defaultdict(int)

        for block in self.order_blocks_for_import(self.blocks):
            self.import_block(session, block)

        session.flush()
        return dict(self.inserted_counts)

    def import_block(self, session: Session, block: CopyBlock) -> None:
        source_table = block.table_name

        if source_table == "reference":
            self.logger.warning(
                "Skipping source table 'reference'. If you add an active Reference "
                "model to mlayer.py, add its mapping in build_mapping()."
            )
            return

        if source_table == "conversion_cast":
            self.import_conversion_cast_block(session, block)
            return

        mapping = self.build_mapping()
        config = mapping.get(source_table)

        if config is None:
            message = f"No mapping configured for source table {source_table!r}; skipping"
            if self.config.strict:
                raise RuntimeError(message)
            self.logger.warning(message)
            return

        model = config["model"]

        if model is None:
            message = f"No ORM model found for source table {source_table!r}; skipping"
            if self.config.strict:
                raise RuntimeError(message)
            self.logger.warning(message)
            return

        target_table = model.__tablename__
        column_map = config.get("column_map", {})

        for source_row in block.rows:
            obj = self.make_orm_object(
                model=model,
                target_table=target_table,
                source_row=source_row,
                column_map=column_map,
            )

            session.add(obj)
            self.inserted_counts[target_table] += 1

            if self.inserted_counts[target_table] % self.config.batch_size == 0:
                session.flush()

        self.logger.info(
            "Imported %s rows from %s into %s",
            len(block.rows),
            source_table,
            target_table,
        )

    def build_mapping(self) -> dict[str, dict[str, Any]]:
        """
        Source pg_dump table -> target ORM model and column mapping.

        This mapping is intentionally aligned with mlayer_mapper.py:
        - function -> transform
        - aspect_scale -> quantityobject_table
        - sources -> reference
        - scale.type -> scale.scale_type
        """
        return {
            "prefix": {
                "model": self.registry.get("prefix"),
                "column_map": {
                    "sources": "reference",
                },
            },
            "system": {
                "model": self.registry.get("system"),
                "column_map": {
                    "sources": "reference",
                },
            },
            "dimension": {
                "model": self.registry.get("dimension"),
                "column_map": {},
            },
            "aspect": {
                "model": self.registry.get("aspect"),
                "column_map": {
                    "sources": "reference",
                },
            },
            "unit": {
                "model": self.registry.get("unit"),
                "column_map": {
                    "sources": "reference",
                },
            },
            "scale": {
                "model": self.registry.get("scale"),
                "column_map": {
                    "type": "scale_type",
                    "sources": "reference",
                },
            },
            "function": {
                "model": self.registry.get("transform"),
                "column_map": {},
            },
            "aspect_scale": {
                "model": self.registry.get("quantityobject_table"),
                "column_map": {
                    "sources": "reference",
                },
            },
        }

    def order_blocks_for_import(self, blocks: list[CopyBlock]) -> list[CopyBlock]:
        """
        Match mlayer_mapper.py's broad load order.

        mlayer_mapper.py order:
            prefixes, systems, dimensions, aspects, units, scales, functions

        Then:
            aspect_scale and conversion_cast.
        """
        priority = {
            "prefix": 10,
            "system": 20,
            "dimension": 30,
            "aspect": 40,
            "unit": 50,
            "scale": 60,
            "function": 70,
            "aspect_scale": 80,
            "conversion_cast": 90,
            "reference": 999,
        }

        return sorted(blocks, key=lambda block: priority.get(block.table_name, 500))

    def make_orm_object(
        self,
        model: Any,
        target_table: str,
        source_row: dict[str, Any],
        column_map: dict[str, str],
    ) -> Any:
        row = self.rename_columns(source_row, column_map)
        row = self.keep_model_columns(model, row)
        row = self.apply_transforms(target_table, row)
        row = self.coerce_model_column_types(model, row)
        return model(**row)

    @staticmethod
    def rename_columns(row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
        return {mapping.get(key, key): value for key, value in row.items()}

    @staticmethod
    def keep_model_columns(model: Any, row: dict[str, Any]) -> dict[str, Any]:
        allowed = {column.name for column in model.__table__.columns}
        return {key: value for key, value in row.items() if key in allowed}

    def apply_transforms(self, target_table_name: str, row: dict[str, Any]) -> dict[str, Any]:
        table_transforms = self.transforms.get(target_table_name, {})

        for column_name, transform in table_transforms.items():
            if column_name in row:
                row[column_name] = transform(row[column_name])

        return row

    def coerce_model_column_types(self, model: Any, row: dict[str, Any]) -> dict[str, Any]:
        """
        Generic ORM-aware coercion. This handles Boolean columns not explicitly
        listed in the transform table.
        """
        for column in model.__table__.columns:
            if column.name not in row:
                continue

            value = row[column.name]

            if value is None:
                continue

            if isinstance(column.type, Boolean):
                row[column.name] = self.transforms_cls.coerce_bool(value)

        return row

    def import_conversion_cast_block(self, session: Session, block: CopyBlock) -> None:
        split_rows = self.split_conversion_cast_rows(block)

        for target_table, model, row in split_rows:
            session.add(model(**row))
            self.inserted_counts[target_table] += 1

            if self.inserted_counts[target_table] % self.config.batch_size == 0:
                session.flush()

        self.logger.info(
            "Imported %s rows from conversion_cast into conversion/cast",
            len(block.rows),
        )

    def split_conversion_cast_rows(
        self,
        block: CopyBlock,
    ) -> list[tuple[str, Any, dict[str, Any]]]:
        """
        Split source conversion_cast rows into Conversion and Cast rows.

        mlayer_mapper.py alignment:
        - is_cast false -> Conversion
        - is_cast true  -> Cast
        - function_id   -> transform_id
        - non-cast conversion with aspect_id uses that aspect for both src/dst
        """
        conversion_model = self.registry.require("conversion")
        cast_model = self.registry.require("cast")

        output: list[tuple[str, Any, dict[str, Any]]] = []

        for source_row in block.rows:
            is_cast = self.transforms_cls.coerce_bool(source_row.get("is_cast"))

            row = dict(source_row)

            if "function_id" in row:
                row["transform_id"] = row.pop("function_id")

            if not is_cast and "aspect_id" in row:
                row.setdefault("src_aspect_id", row["aspect_id"])
                row.setdefault("dst_aspect_id", row["aspect_id"])

            row.pop("is_cast", None)

            if is_cast:
                target_table = "cast"
                model = cast_model
            else:
                target_table = "conversion"
                model = conversion_model

            row = self.keep_model_columns(model, row)
            row = self.apply_transforms(target_table, row)
            row = self.coerce_model_column_types(model, row)

            output.append((target_table, model, row))

        return output

    def conversion_cast_source_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for block in self.blocks:
            if block.table_name == "conversion_cast":
                rows.extend(block.rows)

        return rows

    def ensure_quantity_objects_from_conversion_cast(self, session: Session) -> int:
        """
        Align with mlayer_mapper.py's getScaleAspectAssociations behaviour.

        The JSON mapper creates QuantityObject rows from conversions and casts.
        If aspect_scale already populated them, this method skips existing pairs.
        """
        qo_model = self.registry.get("quantityobject_table")

        if qo_model is None:
            self.logger.warning(
                "Cannot derive QuantityObject rows: quantityobject_table model not found"
            )
            return 0

        added = 0

        for row in self.conversion_cast_source_rows():
            is_cast = self.transforms_cls.coerce_bool(row.get("is_cast"))

            pairs: list[tuple[Any, Any]] = []

            if is_cast:
                if row.get("src_scale_id") and row.get("src_aspect_id"):
                    pairs.append((row["src_scale_id"], row["src_aspect_id"]))

                if row.get("dst_scale_id") and row.get("dst_aspect_id"):
                    pairs.append((row["dst_scale_id"], row["dst_aspect_id"]))
            else:
                aspect_id = (
                    row.get("aspect_id")
                    or row.get("src_aspect_id")
                    or row.get("dst_aspect_id")
                )

                if row.get("src_scale_id") and aspect_id:
                    pairs.append((row["src_scale_id"], aspect_id))

                if row.get("dst_scale_id") and aspect_id:
                    pairs.append((row["dst_scale_id"], aspect_id))

            for scale_id, aspect_id in pairs:
                existing = (
                    session.query(qo_model)
                    .filter(
                        qo_model.scale_id == scale_id,
                        qo_model.aspect_id == aspect_id,
                    )
                    .first()
                )

                if existing is not None:
                    continue

                session.add(qo_model(scale_id=scale_id, aspect_id=aspect_id))
                added += 1

        session.flush()

        if added:
            self.logger.info(
                "Derived %s missing QuantityObject rows from conversion_cast",
                added,
            )
        else:
            self.logger.info("No missing QuantityObject rows needed to be derived")

        return added

    def update_dimension_systematic_scales(self, session: Session) -> int:
        """
        Align with mlayer_mapper.py's _updateDimensionSystematicScale.

        For each systematic scale, set the corresponding
        Dimension.systematic_scale_id if the model exposes these attributes.
        """
        scale_model = self.registry.get("scale")
        dimension_model = self.registry.get("dimension")

        if scale_model is None or dimension_model is None:
            self.logger.warning(
                "Cannot update systematic scales: scale or dimension model not found"
            )
            return 0

        required_scale_attrs = ["is_systematic", "system_dimensions_id"]
        for attr in required_scale_attrs:
            if not hasattr(scale_model, attr):
                self.logger.warning(
                    "Cannot update systematic scales: Scale.%s not found",
                    attr,
                )
                return 0

        if not hasattr(dimension_model, "systematic_scale_id"):
            self.logger.warning(
                "Cannot update systematic scales: Dimension.systematic_scale_id not found"
            )
            return 0

        count = 0

        scales = (
            session.query(scale_model)
            .filter(scale_model.is_systematic.is_(True))
            .all()
        )

        for scale in scales:
            dimension_id = getattr(scale, "system_dimensions_id", None)

            if not dimension_id:
                continue

            dimension = session.get(dimension_model, dimension_id)

            if dimension is None:
                continue

            if getattr(dimension, "systematic_scale_id", None) != scale.id:
                setattr(dimension, "systematic_scale_id", scale.id)
                count += 1

        session.flush()
        self.logger.info("Updated %s Dimension.systematic_scale_id values", count)
        return count

    def update_quantity_object_names(self, session: Session) -> int:
        """
        Approximate mlayer_mapper.py's QuantityObject display-field update.

        This only sets fields that actually exist in the current ORM model.
        """
        qo_model = self.registry.get("quantityobject_table")
        aspect_model = self.registry.get("aspect")
        scale_model = self.registry.get("scale")
        unit_model = self.registry.get("unit")
        dimension_model = self.registry.get("dimension")
        system_model = self.registry.get("system")

        if not all([qo_model, aspect_model, scale_model, unit_model]):
            self.logger.warning(
                "Cannot update QuantityObject names: required models not found"
            )
            return 0

        updated = 0
        quantity_objects = session.query(qo_model).all()

        for qo in quantity_objects:
            aspect = session.get(aspect_model, qo.aspect_id)
            scale = session.get(scale_model, qo.scale_id)

            if aspect is None or scale is None:
                continue

            unit = None
            if getattr(scale, "unit_id", None):
                unit = session.get(unit_model, scale.unit_id)

            if hasattr(qo, "quantity_name"):
                current_name = getattr(qo, "name", None)

                if current_name:
                    computed_name = current_name
                elif getattr(scale, "name", None):
                    computed_name = f"{aspect.name} {scale.name}"
                elif unit is not None and getattr(unit, "name", None):
                    computed_name = f"{aspect.name} {unit.name}"
                else:
                    computed_name = None

                if computed_name and getattr(qo, "quantity_name", None) != computed_name:
                    setattr(qo, "quantity_name", computed_name)
                    updated += 1

            if hasattr(qo, "quantity_symbol"):
                current_symbol = getattr(qo, "symbol", None)

                if current_symbol:
                    computed_symbol = current_symbol
                elif getattr(scale, "symbol", None):
                    computed_symbol = f"{aspect.symbol} {scale.symbol}"
                elif unit is not None and getattr(unit, "symbol", None):
                    computed_symbol = f"{aspect.symbol} {unit.symbol}"
                else:
                    computed_symbol = None

                if computed_symbol and getattr(qo, "quantity_symbol", None) != computed_symbol:
                    setattr(qo, "quantity_symbol", computed_symbol)
                    updated += 1

            if hasattr(qo, "system_symbol"):
                system_symbol = None

                dimension_id = getattr(scale, "system_dimensions_id", None)
                if dimension_id and dimension_model is not None and system_model is not None:
                    dimension = session.get(dimension_model, dimension_id)
                    if dimension is not None:
                        formal_system_id = getattr(dimension, "formal_system_id", None)
                        if formal_system_id:
                            system = session.get(system_model, formal_system_id)
                            if system is not None:
                                system_symbol = getattr(system, "symbol", None)

                if system_symbol and getattr(qo, "system_symbol", None) != system_symbol:
                    setattr(qo, "system_symbol", system_symbol)
                    updated += 1

        session.flush()
        self.logger.info("Updated %s QuantityObject derived fields", updated)
        return updated

    def verify_counts(
        self,
        session: Session,
        inserted_counts: dict[str, int],
    ) -> None:
        self.logger.info("Import verification")

        for table_name, expected in sorted(inserted_counts.items()):
            model = self.registry.get(table_name)

            if model is None:
                continue

            actual = session.query(model).count()
            status = "OK" if actual >= expected else "MISMATCH"

            self.logger.info(
                "  %-25s inserted=%s actual=%s %s",
                table_name,
                expected,
                actual,
                status,
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", required=True, type=Path)
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--database-url")
    parser.add_argument("--models", default="mlayer")
    parser.add_argument("--drop-create", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--echo-sql", action="store_true")
    parser.add_argument("--enable-sqlite-foreign-keys", action="store_true")
    parser.add_argument("--skip-post-processing", action="store_true")
    parser.add_argument("--skip-quantity-object-derivation", action="store_true")
    parser.add_argument("--skip-quantity-object-name-update", action="store_true")
    parser.add_argument("--skip-dimension-systematic-scale-update", action="store_true")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> MlayerDumpImportConfig:
    if not args.sqlite and not args.database_url:
        raise ValueError("Provide either --sqlite or --database-url")

    return MlayerDumpImportConfig(
        dump_path=args.dump,
        sqlite_path=args.sqlite,
        database_url=args.database_url,
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
        echo_sql=args.echo_sql,
        disable_sqlite_foreign_keys_during_import=not args.enable_sqlite_foreign_keys,
        skip_post_processing=args.skip_post_processing,
        skip_quantity_object_derivation=args.skip_quantity_object_derivation,
        skip_quantity_object_name_update=args.skip_quantity_object_name_update,
        skip_dimension_systematic_scale_update=args.skip_dimension_systematic_scale_update,
    )


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s %(name)s: %(message)s",
    )

    models_module = importlib.import_module(args.models)
    config = config_from_args(args)

    mapper = MlayerSqlDumpMapper(
        config=config,
        models_module=models_module,
    )

    try:
        result = mapper.run()
    except Exception:
        return 1

    LOG.info("Import complete")
    LOG.info("Inserted counts: %s", result.inserted_counts)
    LOG.info("Derived QuantityObject rows: %s", result.derived_quantity_objects)
    LOG.info(
        "Updated Dimension.systematic_scale_id rows: %s",
        result.updated_dimension_systematic_scales,
    )
    LOG.info(
        "Updated QuantityObject derived fields: %s",
        result.updated_quantity_object_fields,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

