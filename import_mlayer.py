#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

#!/usr/bin/env python3
"""
Unified M-Layer import and validation command.

Supports:

    sql-dump
        Import from PostgreSQL plain-text dump into SQLite.

    json
        Import from JSON directory into SQLite.

    both
        Import SQL dump and JSON into two separate SQLite databases, then compare.

    compare
        Compare two already-created SQLite databases.

Example:

    python import_mlayer.py both \
        --dump ./data/m_layer_v5.86.dmp \
        --json-dir ./data/json \
        --sql-sqlite ./data/mlayer_sql.sqlite \
        --json-sqlite ./data/mlayer_json.sqlite \
        --drop-create \
        --batch-size 5000
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import argparse
import logging
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from miiflask.flask.models import mlayer

from miiflask.mappers.mlayer_sql_dump_mapper import (
    MlayerDumpImportConfig,
    MlayerSqlDumpMapper,
)

from miiflask.mappers.mlayer_json_mapper import (
    MlayerJsonImportConfig,
    MlayerJsonMapper,
)


LOG = logging.getLogger("mlayer_import")


# =============================================================================
# Import runners
# =============================================================================


def run_sql_dump_import(args):
    config = MlayerDumpImportConfig(
        dump_path=Path(args.dump),
        sqlite_path=Path(args.sqlite),
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
    )

    mapper = MlayerSqlDumpMapper(
        config=config,
        models_module=mlayer,
    )

    return mapper.run()


def run_json_import(args):
    config = MlayerJsonImportConfig(
        json_dir=Path(args.json_dir),
        sqlite_path=Path(args.sqlite),
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
    )

    mapper = MlayerJsonMapper(
        config=config,
        models_module=mlayer,
    )

    return mapper.run()


def run_both_imports(args):
    LOG.info("Running SQL dump import")
    sql_args = argparse.Namespace(
        dump=args.dump,
        sqlite=args.sql_sqlite,
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
    )
    sql_result = run_sql_dump_import(sql_args)

    LOG.info("Running JSON import")
    json_args = argparse.Namespace(
        json_dir=args.json_dir,
        sqlite=args.json_sqlite,
        drop_create=args.drop_create,
        strict=args.strict,
        batch_size=args.batch_size,
    )
    json_result = run_json_import(json_args)

    LOG.info("SQL import result: %s", sql_result)
    LOG.info("JSON import result: %s", json_result)

    if args.compare:
        compare_args = argparse.Namespace(
            sql_sqlite=args.sql_sqlite,
            json_sqlite=args.json_sqlite,
            fail_on_mismatch=args.fail_on_mismatch,
            sample_limit=args.sample_limit,
        )
        return compare_databases_from_args(compare_args)

    return 0


# =============================================================================
# Validation / comparison
# =============================================================================


@dataclass
class TableComparison:
    table_name: str
    sql_count: int
    json_count: int
    matches: bool


@dataclass
class FieldMismatch:
    table_name: str
    primary_key: Any
    column_name: str
    sql_value: Any
    json_value: Any


@dataclass
class ComparisonResult:
    table_counts: list[TableComparison] = field(default_factory=list)
    conversion_cast_summary: dict[str, dict[str, int]] = field(default_factory=dict)
    missing_in_json: dict[str, list[Any]] = field(default_factory=dict)
    missing_in_sql: dict[str, list[Any]] = field(default_factory=dict)
    field_mismatches: list[FieldMismatch] = field(default_factory=list)

    @property
    def has_mismatches(self) -> bool:
        if any(not item.matches for item in self.table_counts):
            return True

        if any(values for values in self.missing_in_json.values()):
            return True

        if any(values for values in self.missing_in_sql.values()):
            return True

        if self.field_mismatches:
            return True

        return False


class MlayerDatabaseComparator:
    """
    Compare two M-Layer SQLite databases produced from the same dataset.

    Intended comparison direction:

        SQL dump import database  vs  JSON import database

    This validates whether both import pathways produce equivalent application
    database content.
    """

    DEFAULT_TABLES = [
        "aspect",
        "unit",
        "prefix",
        "system",
        "dimension",
        "scale",
        "transform",
        "quantityobject_table",
        "conversion_cast",
    ]

    # Tables where direct PK comparison is useful.
    DEFAULT_PK_COMPARE_TABLES = [
        "aspect",
        "unit",
        "prefix",
        "system",
        "dimension",
        "scale",
        "transform",
    ]

    # Tables with composite or generated identities need special handling.
    DEFAULT_KEY_COMPARE_TABLES = {
        "quantityobject_table": ["scale_id", "aspect_id"],
        "conversion_cast": [
            "is_cast",
            "src_scale_id",
            "dst_scale_id",
            "src_aspect_id",
            "dst_aspect_id",
            "transform_id",
            "parameters",
        ],
    }

    # Avoid comparing fields that are often derived, database-generated,
    # or allowed to differ during transition.
    DEFAULT_EXCLUDED_COLUMNS = {
        "id",  # for conversion_cast if auto-generated
    }

    def __init__(
        self,
        *,
        sql_sqlite: Path,
        json_sqlite: Path,
        models_module: Any,
        sample_limit: int = 20,
        logger: logging.Logger | None = None,
    ) -> None:
        self.sql_sqlite = Path(sql_sqlite)
        self.json_sqlite = Path(json_sqlite)
        self.models_module = models_module
        self.sample_limit = sample_limit
        self.logger = logger or LOG

        self.sql_engine = create_engine(f"sqlite:///{self.sql_sqlite}", future=True)
        self.json_engine = create_engine(f"sqlite:///{self.json_sqlite}", future=True)

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

    def compare(self) -> ComparisonResult:
        result = ComparisonResult()

        with Session(self.sql_engine) as sql_session, Session(self.json_engine) as json_session:
            self.compare_table_counts(sql_session, json_session, result)
            self.compare_conversion_cast_summary(sql_session, json_session, result)
            self.compare_primary_key_tables(sql_session, json_session, result)
            self.compare_keyed_tables(sql_session, json_session, result)

        self.print_summary(result)
        return result

    # -------------------------------------------------------------------------
    # Count comparison
    # -------------------------------------------------------------------------

    def compare_table_counts(
        self,
        sql_session: Session,
        json_session: Session,
        result: ComparisonResult,
    ) -> None:
        self.logger.info("Comparing table counts")

        for table_name in self.DEFAULT_TABLES:
            model = self.models_by_table.get(table_name)

            if model is None:
                self.logger.warning("Skipping count comparison for missing model: %s", table_name)
                continue

            sql_count = sql_session.query(model).count()
            json_count = json_session.query(model).count()

            item = TableComparison(
                table_name=table_name,
                sql_count=sql_count,
                json_count=json_count,
                matches=sql_count == json_count,
            )

            result.table_counts.append(item)

            status = "OK" if item.matches else "MISMATCH"

            self.logger.info(
                "  %-25s sql=%s json=%s %s",
                table_name,
                sql_count,
                json_count,
                status,
            )

    # -------------------------------------------------------------------------
    # Conversion/cast summary
    # -------------------------------------------------------------------------

    def compare_conversion_cast_summary(
        self,
        sql_session: Session,
        json_session: Session,
        result: ComparisonResult,
    ) -> None:
        ConversionCast = self.models_by_table.get("conversion_cast")

        if ConversionCast is None:
            self.logger.warning("Skipping ConversionCast summary: model not found")
            return

        def summary(session: Session) -> dict[str, int]:
            total = session.query(ConversionCast).count()
            casts = (
                session.query(ConversionCast)
                .filter(ConversionCast.is_cast.is_(True))
                .count()
            )
            conversions = (
                session.query(ConversionCast)
                .filter(ConversionCast.is_cast.is_(False))
                .count()
            )

            return {
                "total": total,
                "conversions": conversions,
                "casts": casts,
            }

        sql_summary = summary(sql_session)
        json_summary = summary(json_session)

        result.conversion_cast_summary = {
            "sql": sql_summary,
            "json": json_summary,
        }

        self.logger.info("ConversionCast summary")
        self.logger.info("  SQL : %s", sql_summary)
        self.logger.info("  JSON: %s", json_summary)

    # -------------------------------------------------------------------------
    # PK table comparison
    # -------------------------------------------------------------------------

    def compare_primary_key_tables(
        self,
        sql_session: Session,
        json_session: Session,
        result: ComparisonResult,
    ) -> None:
        self.logger.info("Comparing primary-keyed tables")

        for table_name in self.DEFAULT_PK_COMPARE_TABLES:
            model = self.models_by_table.get(table_name)

            if model is None:
                continue

            pk_columns = list(model.__table__.primary_key.columns)

            if len(pk_columns) != 1:
                self.logger.warning(
                    "Skipping PK comparison for %s because it does not have a single-column PK",
                    table_name,
                )
                continue

            pk_name = pk_columns[0].name

            sql_rows = {
                getattr(row, pk_name): row
                for row in sql_session.query(model).all()
            }

            json_rows = {
                getattr(row, pk_name): row
                for row in json_session.query(model).all()
            }

            self.compare_key_sets(
                result=result,
                table_name=table_name,
                sql_keys=set(sql_rows.keys()),
                json_keys=set(json_rows.keys()),
            )

            shared_keys = set(sql_rows.keys()) & set(json_rows.keys())

            for key in sorted(shared_keys):
                self.compare_row_fields(
                    result=result,
                    table_name=table_name,
                    key=key,
                    sql_row=sql_rows[key],
                    json_row=json_rows[key],
                )

    # -------------------------------------------------------------------------
    # Composite-key semantic comparison
    # -------------------------------------------------------------------------

    def compare_keyed_tables(
        self,
        sql_session: Session,
        json_session: Session,
        result: ComparisonResult,
    ) -> None:
        self.logger.info("Comparing semantically-keyed tables")

        for table_name, key_columns in self.DEFAULT_KEY_COMPARE_TABLES.items():
            model = self.models_by_table.get(table_name)

            if model is None:
                continue

            sql_rows = {
                self.make_semantic_key(row, key_columns): row
                for row in sql_session.query(model).all()
            }

            json_rows = {
                self.make_semantic_key(row, key_columns): row
                for row in json_session.query(model).all()
            }

            self.compare_key_sets(
                result=result,
                table_name=table_name,
                sql_keys=set(sql_rows.keys()),
                json_keys=set(json_rows.keys()),
            )

            # For semantic-keyed rows, matching keys are generally sufficient
            # because the key columns define equivalence. Additional field
            # comparison can be added later if needed.

    @staticmethod
    def make_semantic_key(row: Any, columns: list[str]) -> tuple[Any, ...]:
        return tuple(getattr(row, column, None) for column in columns)

    # -------------------------------------------------------------------------
    # Shared comparison helpers
    # -------------------------------------------------------------------------

    def compare_key_sets(
        self,
        *,
        result: ComparisonResult,
        table_name: str,
        sql_keys: set[Any],
        json_keys: set[Any],
    ) -> None:
        missing_in_json = sorted(sql_keys - json_keys)[: self.sample_limit]
        missing_in_sql = sorted(json_keys - sql_keys)[: self.sample_limit]

        if missing_in_json:
            result.missing_in_json.setdefault(table_name, []).extend(missing_in_json)

            self.logger.warning(
                "%s: %s keys present in SQL but missing in JSON. Sample: %s",
                table_name,
                len(sql_keys - json_keys),
                missing_in_json,
            )

        if missing_in_sql:
            result.missing_in_sql.setdefault(table_name, []).extend(missing_in_sql)

            self.logger.warning(
                "%s: %s keys present in JSON but missing in SQL. Sample: %s",
                table_name,
                len(json_keys - sql_keys),
                missing_in_sql,
            )

    def compare_row_fields(
        self,
        *,
        result: ComparisonResult,
        table_name: str,
        key: Any,
        sql_row: Any,
        json_row: Any,
    ) -> None:
        for column in sql_row.__table__.columns:
            column_name = column.name

            if column_name in self.DEFAULT_EXCLUDED_COLUMNS:
                continue

            sql_value = getattr(sql_row, column_name, None)
            json_value = getattr(json_row, column_name, None)

            if self.normalise_value(sql_value) != self.normalise_value(json_value):
                mismatch = FieldMismatch(
                    table_name=table_name,
                    primary_key=key,
                    column_name=column_name,
                    sql_value=sql_value,
                    json_value=json_value,
                )

                result.field_mismatches.append(mismatch)

                if len(result.field_mismatches) <= self.sample_limit:
                    self.logger.warning(
                        "%s[%r].%s mismatch: sql=%r json=%r",
                        table_name,
                        key,
                        column_name,
                        sql_value,
                        json_value,
                    )

    @staticmethod
    def normalise_value(value: Any) -> Any:
        """
        Normalize simple value differences before comparison.

        This helps avoid false mismatches from bool/int/string formatting.
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            text = value.strip()

            if text.lower() in {"t", "true"}:
                return True

            if text.lower() in {"f", "false"}:
                return False

            if text == "":
                return None

            return text

        return value

    def print_summary(self, result: ComparisonResult) -> None:
        self.logger.info("=" * 72)
        self.logger.info("M-Layer import comparison summary")
        self.logger.info("=" * 72)

        mismatched_counts = [
            item
            for item in result.table_counts
            if not item.matches
        ]

        if not mismatched_counts:
            self.logger.info("Table counts: OK")
        else:
            self.logger.warning("Table counts: %s mismatches", len(mismatched_counts))

        if result.conversion_cast_summary:
            sql_summary = result.conversion_cast_summary["sql"]
            json_summary = result.conversion_cast_summary["json"]

            if sql_summary == json_summary:
                self.logger.info("ConversionCast summary: OK")
            else:
                self.logger.warning(
                    "ConversionCast summary mismatch: sql=%s json=%s",
                    sql_summary,
                    json_summary,
                )

        total_missing_json = sum(len(values) for values in result.missing_in_json.values())
        total_missing_sql = sum(len(values) for values in result.missing_in_sql.values())

        if total_missing_json == 0 and total_missing_sql == 0:
            self.logger.info("Key comparison: OK")
        else:
            self.logger.warning(
                "Key comparison mismatches: missing_in_json=%s missing_in_sql=%s",
                total_missing_json,
                total_missing_sql,
            )

        if not result.field_mismatches:
            self.logger.info("Field comparison: OK")
        else:
            self.logger.warning(
                "Field comparison mismatches: %s",
                len(result.field_mismatches),
            )

        if result.has_mismatches:
            self.logger.warning("Overall result: MISMATCH")
        else:
            self.logger.info("Overall result: OK")


def compare_databases_from_args(args) -> int:
    comparator = MlayerDatabaseComparator(
        sql_sqlite=Path(args.sql_sqlite),
        json_sqlite=Path(args.json_sqlite),
        models_module=mlayer,
        sample_limit=args.sample_limit,
    )

    result = comparator.compare()

    if result.has_mismatches and args.fail_on_mismatch:
        return 1

    return 0


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import and validate M-Layer data from SQL dump and/or JSON."
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level. Example: DEBUG, INFO, WARNING",
    )

    subparsers = parser.add_subparsers(dest="source", required=True)

    # -------------------------------------------------------------------------
    # sql-dump
    # -------------------------------------------------------------------------

    sql_parser = subparsers.add_parser(
        "sql-dump",
        help="Import from PostgreSQL plain-text dump",
    )
    sql_parser.add_argument("--dump", required=True)
    sql_parser.add_argument("--sqlite", required=True)
    sql_parser.add_argument("--drop-create", action="store_true")
    sql_parser.add_argument("--strict", action="store_true")
    sql_parser.add_argument("--batch-size", type=int, default=1000)

    # -------------------------------------------------------------------------
    # json
    # -------------------------------------------------------------------------

    json_parser = subparsers.add_parser(
        "json",
        help="Import from JSON collection directory",
    )
    json_parser.add_argument("--json-dir", required=True)
    json_parser.add_argument("--sqlite", required=True)
    json_parser.add_argument("--drop-create", action="store_true")
    json_parser.add_argument("--strict", action="store_true")
    json_parser.add_argument("--batch-size", type=int, default=1000)

    # -------------------------------------------------------------------------
    # both
    # -------------------------------------------------------------------------

    both_parser = subparsers.add_parser(
        "both",
        help="Import both SQL dump and JSON, then optionally compare",
    )
    both_parser.add_argument("--dump", required=True)
    both_parser.add_argument("--json-dir", required=True)
    both_parser.add_argument("--sql-sqlite", required=True)
    both_parser.add_argument("--json-sqlite", required=True)
    both_parser.add_argument("--drop-create", action="store_true")
    both_parser.add_argument("--strict", action="store_true")
    both_parser.add_argument("--batch-size", type=int, default=1000)
    both_parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare the two generated databases after import",
    )
    both_parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Return exit code 1 if comparison mismatches are found",
    )
    both_parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Number of mismatch examples to log per category",
    )

    # -------------------------------------------------------------------------
    # compare
    # -------------------------------------------------------------------------

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare existing SQL-import and JSON-import SQLite databases",
    )
    compare_parser.add_argument("--sql-sqlite", required=True)
    compare_parser.add_argument("--json-sqlite", required=True)
    compare_parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
    )
    compare_parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.source == "sql-dump":
        run_sql_dump_import(args)
        return 0

    if args.source == "json":
        run_json_import(args)
        return 0

    if args.source == "both":
        return run_both_imports(args)

    if args.source == "compare":
        return compare_databases_from_args(args)

    parser.error(f"Unknown source: {args.source}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

