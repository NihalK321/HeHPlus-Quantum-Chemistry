"""Reproducible local import command for PepperQ's peptide library.

Examples:
    python -m backend.peptide_library.cli import --source uniprot --limit 100
    python -m backend.peptide_library.cli import --source uniprot --limit 1000
    python -m backend.peptide_library.cli stats
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import create_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import and inspect the local PepperQ peptide library.")
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional SQLite path. Defaults to the ignored package-local database or PEPPERQ_PEPTIDE_DB.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    import_parser = commands.add_parser("import", help="Retrieve verified records from one documented source API.")
    import_parser.add_argument("--source", choices=("uniprot", "dbaasp"), default="uniprot")
    import_parser.add_argument("--limit", type=int, default=100, help="Maximum source peptide records to process.")
    import_parser.add_argument("--page-size", type=int, help="Source page size; bounded by each connector.")
    import_parser.add_argument(
        "--enrich-structures",
        action="store_true",
        help="For DBAASP only, retrieve RCSB metadata for explicit source-supplied PDB IDs.",
    )
    commands.add_parser("stats", help="Print actual local record counts without calling external services.")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    service = create_service(arguments.database)
    try:
        if arguments.command == "stats":
            print(json.dumps(service.stats(), indent=2, sort_keys=True))
            return 0

        if arguments.limit < 1:
            raise ValueError("--limit must be at least 1")
        if arguments.source == "uniprot":
            report = service.import_uniprot(
                limit=arguments.limit,
                page_size=arguments.page_size or 500,
            )
        else:
            report = service.import_dbaasp(
                limit=arguments.limit,
                page_size=arguments.page_size or 50,
                enrich_structures=arguments.enrich_structures,
            )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "completed" else 1
    except ValueError as error:
        print(f"Importer configuration error: {error}")
        return 2
    finally:
        service.repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
