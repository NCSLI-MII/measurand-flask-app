#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.
#!/usr/bin/env python3
"""
Class-based M-Layer JSON importer.

This importer builds the application database from JSON/API-style M-Layer data.

It is designed for the harmonized model where conversions and casts are stored
in one ORM table:

    ConversionCast

JSON input may still contain separate logical collections:

    conversions -> ConversionCast(is_cast=False)
    casts       -> ConversionCast(is_cast=True)

Typical programmatic usage:

    from pathlib import Path
    import mlayer

    from mlayer_json_mapper_v2 import (
        MlayerJsonImportConfig,
        MlayerJsonMapper,
    )

    config = MlayerJsonImportConfig(
        json_dir=Path("./data/json"),
        sqlite_path=Path("./data/mlayer_json.sqlite"),
        drop_create=True,
    )

    mapper = MlayerJsonMapper(config=config, models_module=mlayer)
    mapper.run()

CLI usage:

    python mlayer_json_mapper_v2.py \
        --json-dir ./data/json \
        --sqlite ./data/mlayer_json.sqlite \
        --models mlayer \
        --drop-create
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from miiflask.flask.models import mlayer

LOG = logging.getLogger("mlayer_json_mapper")


@dataclass
class MlayerJsonImportConfig:
    """
    Configuration for the JSON mapper.

    json_dir:
        Directory containing JSON collection files.

    database_url:
        Full SQLAlchemy database URL. If provided, this takes precedence over
        sqlite_path.

    sqlite_path:
        SQLite database path.

    drop_create:
        Drop and recreate all ORM tables before importing.

    strict:
        Raise errors for missing collections or unresolved references instead
        of logging warnings.

    batch_size:
        Flush every N inserted objects.

    collection_files:
        Maps logical collection names to JSON file names.
    """

    json_dir: Path | None = None
    database_url: str | None = None
    sqlite_path: Path | None = None

    drop_create: bool = False
    strict: bool = False
    batch_size: int = 1000
    echo_sql: bool = False

    enable_sqlite_foreign_keys: bool = False

    skip_post_processing: bool = False
    skip_quantity_object_name_update: bool = False
    skip_dimension_systematic_scale_update: bool = False

    collection_files: dict[str, str] = field(
        default_factory=lambda: {
            "prefixes": "prefixes.json",
            "systems": "systems.json",
            "dimensions": "dimensions.json",
            "aspects": "aspects.json",
            "units": "units.json",
            "scales": "scales.json",
            "functions": "functions.json",
            "conversions": "conversions.json",
            "casts": "casts.json",
        }
    )


@dataclass
class JsonImportResult:
    inserted_counts: dict[str, int]
    skipped_counts: dict[str, int]
    updated_dimension_systematic_scales: int = 0
    updated_quantity_object_fields: int = 0


class MlayerModelRegistry:
    """
    Helper for discovering SQLAlchemy ORM models by __tablename__.
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


class MlayerJsonMapper:
    """
    JSON mapper for the harmonized M-Layer data model.

    This class intentionally follows the broad transformation order used by the
    existing mlayer_mapper.py:

        prefixes
        systems
        dimensions
        aspects
        units
        scales
        functions
        conversions
        casts

    The main difference is that conversions and casts are now both imported into
    ConversionCast.
    """

    COLLECTION_ORDER = [
        "prefixes",
        "systems",
        "dimensions",
        "aspects",
        "units",
        "scales",
        "functions",
        "conversions",
        "casts",
    ]

    def __init__(
        self,
        config: MlayerJsonImportConfig,
        models_module: Any,
        session: Session | None = None,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.models_module = models_module
        self.registry = MlayerModelRegistry(models_module)

        self.external_session = session
        self.engine = engine
        self.logger = logger or LOG

        self.collections: dict[str, list[dict[str, Any]]] = {}

        self.inserted_counts: dict[str, int] = defaultdict(int)
        self.skipped_counts: dict[str, int] = defaultdict(int)

    def run(self) -> JsonImportResult:
        """
        Full import lifecycle.
        """

        self.collections = self.load_collections()

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
                self.logger.exception("JSON import failed; transaction rolled back")
                raise

    def _run_with_session(self, session: Session) -> JsonImportResult:
        self.import_collections(session)

        result = JsonImportResult(
            inserted_counts=dict(self.inserted_counts),
            skipped_counts=dict(self.skipped_counts),
        )

        if not self.config.skip_post_processing:
            if not self.config.skip_dimension_systematic_scale_update:
                result.updated_dimension_systematic_scales = (
                    self.update_dimension_systematic_scales(session)
                )

            if not self.config.skip_quantity_object_name_update:
                result.updated_quantity_object_fields = (
                    self.update_quantity_object_names(session)
                )

        self.verify_counts(session)

        return result

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

        if self.config.enable_sqlite_foreign_keys:
            cursor.execute("PRAGMA foreign_keys=ON")
        else:
            # During initial bulk import, OFF is safer because root scales and
            # dimension/systematic-scale relationships can be cyclic.
            cursor.execute("PRAGMA foreign_keys=OFF")

        cursor.close()

    def prepare_schema(self, engine: Engine) -> None:
        if self.config.drop_create:
            self.logger.warning("Dropping and recreating ORM tables")
            self.registry.Base.metadata.drop_all(engine)

        self.registry.Base.metadata.create_all(engine)

    # -------------------------------------------------------------------------
    # JSON loading
    # -------------------------------------------------------------------------

    def load_collections(self) -> dict[str, list[dict[str, Any]]]:
        """
        Load configured JSON collections from json_dir.

        This implementation expects either:

        1. a top-level list:
            [
                {...},
                {...}
            ]

        or

        2. a top-level object containing one of:
            {
                "data": [...]
            }

            {
                "results": [...]
            }

            {
                "<collection_name>": [...]
            }
        """

        if self.config.json_dir is None:
            raise ValueError("json_dir must be provided for file-based JSON import")

        collections: dict[str, list[dict[str, Any]]] = {}

        for collection_name in self.COLLECTION_ORDER:
            filename = self.config.collection_files.get(collection_name)

            if not filename:
                self._handle_missing_collection(collection_name, "No filename configured")
                collections[collection_name] = []
                continue

            path = self.config.json_dir / filename

            if not path.exists():
                self._handle_missing_collection(collection_name, f"File not found: {path}")
                collections[collection_name] = []
                continue

            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)

            rows = self.extract_rows_from_payload(
                payload=payload,
                collection_name=collection_name,
            )

            self.logger.info(
                "Loaded JSON collection %-15s rows=%s from %s",
                collection_name,
                len(rows),
                path,
            )

            collections[collection_name] = rows

        return collections

    def _handle_missing_collection(self, collection_name: str, message: str) -> None:
        if self.config.strict:
            raise RuntimeError(f"Missing JSON collection {collection_name!r}: {message}")

        self.logger.warning("Missing JSON collection %s: %s", collection_name, message)

    @staticmethod
    def extract_rows_from_payload(
        payload: Any,
        collection_name: str,
    ) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            for key in [collection_name, "data", "results", "items"]:
                value = payload.get(key)

                if isinstance(value, list):
                    return value

        raise ValueError(
            f"Could not extract rows for collection {collection_name!r}; "
            f"expected list or object containing data/results/items/{collection_name}"
        )

    # -------------------------------------------------------------------------
    # Import orchestration
    # -------------------------------------------------------------------------

    def import_collections(self, session: Session) -> None:
        for collection_name in self.COLLECTION_ORDER:
            rows = self.collections.get(collection_name, [])

            for obj in rows:
                created = self.transform_object(
                    session=session,
                    collection_name=collection_name,
                    obj=obj,
                )

                if created is None:
                    self.skipped_counts[collection_name] += 1
                else:
                    target_table = getattr(created, "__tablename__", collection_name)
                    self.inserted_counts[target_table] += 1

                    if self.inserted_counts[target_table] % self.config.batch_size == 0:
                        session.flush()

            session.flush()

            self.logger.info(
                "Imported collection %-15s inserted=%s skipped=%s",
                collection_name,
                sum(1 for _ in rows) - self.skipped_counts[collection_name],
                self.skipped_counts[collection_name],
            )

    def transform_object(
        self,
        session: Session,
        collection_name: str,
        obj: dict[str, Any],
    ) -> Any | None:
        transform_name = f"transform_{collection_name}"

        transform = getattr(self, transform_name, None)

        if transform is None:
            message = f"No transform method for JSON collection {collection_name!r}"

            if self.config.strict:
                raise RuntimeError(message)

            self.logger.warning(message)
            return None

        return transform(session, obj)

    # -------------------------------------------------------------------------
    # Individual transforms
    # -------------------------------------------------------------------------

    def transform_prefixes(self, session: Session, obj: dict[str, Any]) -> Any:
        Prefix = self.registry.require("prefix")

        prefix = Prefix(
            id=obj.get("id"),
            ml_name=obj.get("ml_name"),
            name=obj.get("name"),
            symbol=obj.get("symbol"),
            sources=obj.get("reference"),
            numerator=self.coerce_float(obj.get("numerator")),
            denominator=self.coerce_float(obj.get("denominator")),
        )

        session.add(prefix)
        return prefix

    def transform_systems(self, session: Session, obj: dict[str, Any]) -> Any:
        System = self.registry.require("system")

        system = System(
            id=obj.get("id"),
            ml_name=obj.get("ml_name"),
            #name=obj.get("name"),
            symbol=obj.get("symbol"),
            n=self.coerce_int(obj.get("n")),
            basis=obj.get("basis"),
            sources=obj.get("reference"),
        )

        session.add(system)
        return system

    def transform_dimensions(self, session: Session, obj: dict[str, Any]) -> Any:
        Dimension = self.registry.require("dimension")

        values = self.keep_model_columns(
            Dimension,
            {
                "id": obj.get("id"),
                "exponents": obj.get("exponents"),
                "formal_system_id": obj.get("formal_system_id"),
                "systematic_scale_id": obj.get("systematic_scale_id"),
                "is_quotient": obj.get("is_quotient"),
            },
        )

        values = self.coerce_model_column_types(Dimension, values)

        dimension = Dimension(**values)
        session.add(dimension)
        return dimension

    def transform_aspects(self, session: Session, obj: dict[str, Any]) -> Any:
        Aspect = self.registry.require("aspect")

        name = obj.get("name")

        if name == "electric potential difference":
            name = "voltage"

        if isinstance(name, str):
            name = name.replace(" ", "-")

        aspect = Aspect(
            id=obj.get("id"),
            ml_name=obj.get("ml_name"),
            name=name,
            symbol=obj.get("symbol"),
            sources=obj.get("reference"),
        )

        session.add(aspect)
        return aspect

    def transform_units(self, session: Session, obj: dict[str, Any]) -> Any:
        Unit = self.registry.require("unit")

        unit = Unit(
            id=obj.get("id"),
            ml_name=obj.get("ml_name"),
            name=obj.get("name"),
            symbol=obj.get("symbol"),
            sources=obj.get("reference"),
        )

        session.add(unit)
        return unit

    def transform_scales(self, session: Session, obj: dict[str, Any]) -> Any:
        Scale = self.registry.require("scale")

        values = {
            "id": obj.get("id"),
            "ml_name": obj.get("ml_name"),
            "name": obj.get("name"),
            "symbol": obj.get("symbol"),
            "scale_type": obj.get("type") or obj.get("scale_type"),
            "ref_point": obj.get("ref_point"),
            "ref_point_l": obj.get("ref_point_l"),
            "ref_point_h": obj.get("ref_point_h"),
            "is_systematic": obj.get("is_systematic"),
            "is_special": obj.get("is_special"),
            "is_augmented": obj.get("is_augmented"),
            "unit_id": obj.get("unit_id"),
            "prefix_id": obj.get("prefix_id"),
            "system_dimensions_id": obj.get("system_dimensions_id"),
            "root_scale_id": obj.get("root_scale_id"),
            "reference": obj.get("reference"),
        }

        values = self.keep_model_columns(Scale, values)
        values = self.coerce_model_column_types(Scale, values)

        scale = Scale(**values)
        session.add(scale)
        return scale

    def transform_functions(self, session: Session, obj: dict[str, Any]) -> Any:
        """
        JSON functions map to ORM Transform.
        """

        Transform = self.registry.require("transform")

        transform = Transform(
            id=obj.get("id"),
            ml_name=obj.get("ml_name"),
            #name=obj.get("name"),
            py_function=obj.get("py_function"),
            py_names_in_scope=obj.get("py_names_in_scope"),
            comments=obj.get("comments"),
        )

        session.add(transform)
        return transform

    def transform_conversions(self, session: Session, obj: dict[str, Any]) -> Any:
        """
        JSON conversion -> ConversionCast(is_cast=False).

        JSON conversion records usually have one aspect_id that applies to both
        source and destination.
        """

        aspect_id = obj.get("aspect_id")

        return self.create_conversion_cast(
            session=session,
            is_cast=False,
            src_scale_id=obj.get("src_scale_id"),
            dst_scale_id=obj.get("dst_scale_id"),
            src_aspect_id=obj.get("src_aspect_id") or aspect_id,
            dst_aspect_id=obj.get("dst_aspect_id") or aspect_id,
            function_id=obj.get("function_id"),
            transform_id=obj.get("transform_id"),
            parameters=obj.get("parameters"),
        )

    def transform_casts(self, session: Session, obj: dict[str, Any]) -> Any:
        """
        JSON cast -> ConversionCast(is_cast=True).

        JSON cast records generally have separate source/destination aspects.
        """

        return self.create_conversion_cast(
            session=session,
            is_cast=True,
            src_scale_id=obj.get("src_scale_id"),
            dst_scale_id=obj.get("dst_scale_id"),
            src_aspect_id=obj.get("src_aspect_id"),
            dst_aspect_id=obj.get("dst_aspect_id"),
            function_id=obj.get("function_id"),
            transform_id=obj.get("transform_id"),
            parameters=obj.get("parameters"),
        )

    # -------------------------------------------------------------------------
    # Unified ConversionCast handling
    # -------------------------------------------------------------------------

    def create_conversion_cast(
        self,
        session: Session,
        *,
        is_cast: bool,
        src_scale_id: str | None,
        dst_scale_id: str | None,
        src_aspect_id: str | None,
        dst_aspect_id: str | None,
        function_id: str | None = None,
        transform_id: str | None = None,
        parameters: Any = None,
    ) -> Any:
        ConversionCast = self.registry.require("conversion_cast")

        transform_id = transform_id or function_id

        missing = []

        for field_name, value in [
            ("src_scale_id", src_scale_id),
            ("dst_scale_id", dst_scale_id),
            ("src_aspect_id", src_aspect_id),
            ("dst_aspect_id", dst_aspect_id),
            ("transform_id", transform_id),
        ]:
            if not value:
                missing.append(field_name)

        if missing:
            message = (
                f"Cannot create ConversionCast; missing required fields: {missing}"
            )

            if self.config.strict:
                raise RuntimeError(message)

            self.logger.warning(message)
            return None

        values = {
            "is_cast": is_cast,
            "src_scale_id": src_scale_id,
            "dst_scale_id": dst_scale_id,
            "src_aspect_id": src_aspect_id,
            "dst_aspect_id": dst_aspect_id,
            "transform_id": transform_id,
            "parameters": self.normalise_parameters(parameters),
        }

        values = self.keep_model_columns(ConversionCast, values)
        values = self.coerce_model_column_types(ConversionCast, values)

        conversion_cast = ConversionCast(**values)

        session.add(conversion_cast)

        self.ensure_quantity_object(
            session=session,
            scale_id=src_scale_id,
            aspect_id=src_aspect_id,
        )

        self.ensure_quantity_object(
            session=session,
            scale_id=dst_scale_id,
            aspect_id=dst_aspect_id,
        )

        return conversion_cast

    def ensure_quantity_object(
        self,
        session: Session,
        *,
        scale_id: str | None,
        aspect_id: str | None,
    ) -> Any | None:
        """
        Ensure a QuantityObject exists for the scale/aspect pair.

        This mirrors the earlier mapper behaviour where conversions and casts
        were used to populate Aspect.scales / QuantityObject relationships.
        """

        if not scale_id or not aspect_id:
            return None

        QuantityObject = self.registry.get("quantityobject_table")

        if QuantityObject is None:
            self.logger.warning("QuantityObject model not found; cannot ensure scale/aspect pair")
            return None

        existing = (
            session.query(QuantityObject)
            .filter(
                QuantityObject.scale_id == scale_id,
                QuantityObject.aspect_id == aspect_id,
            )
            .first()
        )

        if existing is not None:
            return existing

        values = {
            "scale_id": scale_id,
            "aspect_id": aspect_id,
        }

        values = self.keep_model_columns(QuantityObject, values)

        quantity_object = QuantityObject(**values)
        session.add(quantity_object)

        return quantity_object

    # -------------------------------------------------------------------------
    # Post-processing
    # -------------------------------------------------------------------------

    def update_dimension_systematic_scales(self, session: Session) -> int:
        """
        For each systematic scale, set Dimension.systematic_scale_id when the
        ORM model supports it.
        """

        Scale = self.registry.get("scale")
        Dimension = self.registry.get("dimension")

        if Scale is None or Dimension is None:
            self.logger.warning("Cannot update systematic scales: missing Scale or Dimension model")
            return 0

        if not hasattr(Scale, "is_systematic"):
            self.logger.warning("Scale.is_systematic not found")
            return 0

        if not hasattr(Scale, "system_dimensions_id"):
            self.logger.warning("Scale.system_dimensions_id not found")
            return 0

        if not hasattr(Dimension, "systematic_scale_id"):
            self.logger.warning("Dimension.systematic_scale_id not found")
            return 0

        updated = 0

        scales = (
            session.query(Scale)
            .filter(Scale.is_systematic.is_(True))
            .all()
        )

        for scale in scales:
            dimension_id = getattr(scale, "system_dimensions_id", None)

            if not dimension_id:
                continue

            dimension = session.get(Dimension, dimension_id)

            if dimension is None:
                continue

            if getattr(dimension, "systematic_scale_id", None) != scale.id:
                setattr(dimension, "systematic_scale_id", scale.id)
                updated += 1

        session.flush()

        self.logger.info("Updated %s Dimension.systematic_scale_id values", updated)

        return updated

    def update_quantity_object_names(self, session: Session) -> int:
        """
        Populate derived QuantityObject fields where those columns exist.

        This approximates the earlier mlayer_mapper.py logic:
        - quantity_name
        - quantity_symbol
        - system_symbol
        """

        QuantityObject = self.registry.get("quantityobject_table")
        Aspect = self.registry.get("aspect")
        Scale = self.registry.get("scale")
        Unit = self.registry.get("unit")
        Dimension = self.registry.get("dimension")
        System = self.registry.get("system")

        if not all([QuantityObject, Aspect, Scale, Unit]):
            self.logger.warning(
                "Cannot update QuantityObject names: required models not found"
            )
            return 0

        updated = 0

        quantity_objects = session.query(QuantityObject).all()

        for qo in quantity_objects:
            aspect = session.get(Aspect, qo.aspect_id)
            scale = session.get(Scale, qo.scale_id)

            if aspect is None or scale is None:
                continue

            unit = None

            if getattr(scale, "unit_id", None):
                unit = session.get(Unit, scale.unit_id)

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

                if dimension_id and Dimension is not None and System is not None:
                    dimension = session.get(Dimension, dimension_id)

                    if dimension is not None:
                        formal_system_id = getattr(dimension, "formal_system_id", None)

                        if formal_system_id:
                            system = session.get(System, formal_system_id)

                            if system is not None:
                                system_symbol = getattr(system, "symbol", None)

                if system_symbol and getattr(qo, "system_symbol", None) != system_symbol:
                    setattr(qo, "system_symbol", system_symbol)
                    updated += 1

        session.flush()

        self.logger.info("Updated %s QuantityObject derived fields", updated)

        return updated

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    @staticmethod
    def keep_model_columns(model: Any, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {column.name for column in model.__table__.columns}
        return {
            key: value
            for key, value in values.items()
            if key in allowed
        }

    def coerce_model_column_types(self, model: Any, values: dict[str, Any]) -> dict[str, Any]:
        for column in model.__table__.columns:
            if column.name not in values:
                continue

            value = values[column.name]

            if value is None:
                continue

            if isinstance(column.type, Boolean):
                values[column.name] = self.coerce_bool(value)

        return values

    @staticmethod
    def coerce_bool(value: Any) -> bool | None:
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

    @staticmethod
    def coerce_float(value: Any) -> float | None:
        if value is None or value == "":
            return None

        if isinstance(value, str):
            value = value.replace('"', "")

        return float(value)

    @staticmethod
    def normalise_parameters(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            return value

        try:
            return json.dumps(value)
        except TypeError:
            return str(value)

    def verify_counts(self, session: Session) -> None:
        self.logger.info("JSON import verification")

        for table_name, expected in sorted(self.inserted_counts.items()):
            model = self.registry.get(table_name)

            if model is None:
                continue

            actual = session.query(model).count()

            # Actual may be greater than direct inserted count because
            # QuantityObject rows can be created while importing conversions/casts.
            status = "OK" if actual >= expected else "MISMATCH"

            self.logger.info(
                "  %-25s inserted=%s actual=%s %s",
                table_name,
                expected,
                actual,
                status,
            )


# -----------------------------------------------------------------------------
# CLI support
# -----------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-dir", required=True, type=Path)
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
    parser.add_argument("--skip-quantity-object-name-update", action="store_true")
    parser.add_argument("--skip-dimension-systematic-scale-update", action="store_true")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> MlayerJsonImportConfig:
    if not args.sqlite and not args.database_url:
        raise ValueError("Provide either --sqlite or --database-url")

    return MlayerJsonImportConfig(
        json_dir=args.json_dir,
        sqlite_path=args.sqlite,
        database_url=args.database_url,
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
        echo_sql=args.echo_sql,
        enable_sqlite_foreign_keys=args.enable_sqlite_foreign_keys,
        skip_post_processing=args.skip_post_processing,
        skip_quantity_object_name_update=args.skip_quantity_object_name_update,
        skip_dimension_systematic_scale_update=args.skip_dimension_systematic_scale_update,
    )


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s %(name)s: %(message)s",
    )

    models_module_name = mlayer

    #try:
    #    models_module = __import__(models_module_name)
    #except Exception:
    #    LOG.exception("Could not import model module %s", models_module_name)
    #    return 1

    config = config_from_args(args)

    mapper = MlayerJsonMapper(
        config=config,
        models_module=models_module,
    )

    try:
        result = mapper.run()
    except Exception:
        LOG.exception("Import failed")
        return 1

    LOG.info("JSON import complete")
    LOG.info("Inserted counts: %s", result.inserted_counts)
    LOG.info("Skipped counts: %s", result.skipped_counts)
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

