#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
#!/usr/bin/env python3

from pathlib import Path
import argparse
import logging

from miiflask.flask.models import mlayer

from miiflask.mappers.mlayer_sql_dump_mapper import (
    MlayerDumpImportConfig,
    MlayerSqlDumpMapper,
)

# from mlayer_mapper import MlayerMapper


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
    raise NotImplementedError(
        "Wire this to your existing mlayer_mapper.MlayerMapper configuration."
    )


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="source", required=True)

    sql_parser = subparsers.add_parser("sql-dump")
    sql_parser.add_argument("--dump", required=True)
    sql_parser.add_argument("--sqlite", required=True)
    sql_parser.add_argument("--drop-create", action="store_true")
    sql_parser.add_argument("--strict", action="store_true")
    sql_parser.add_argument("--batch-size", type=int, default=1000)

    json_parser = subparsers.add_parser("json")
    json_parser.add_argument("--json-dir", required=True)
    json_parser.add_argument("--sqlite", required=True)
    json_parser.add_argument("--drop-create", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.source == "sql-dump":
        run_sql_dump_import(args)
    elif args.source == "json":
        run_json_import(args)


if __name__ == "__main__":
    main()

