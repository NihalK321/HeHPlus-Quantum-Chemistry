"""Offline checks for the read-only merged peptide-catalog adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from tempfile import gettempdir
from typing import Any
from uuid import uuid4

import pytest

from backend.peptide_library.catalog_integration import CatalogIntegrator


class _PrimaryLibrary:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records

    def search(self, **filters: Any) -> dict[str, Any]:
        page = int(filters.get("page", 1))
        page_size = int(filters.get("page_size", 100))
        start = (page - 1) * page_size
        total = len(self.records)
        return {
            "items": self.records[start : start + page_size],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if total else 0,
        }


def _primary(sequence: str = "ACDE") -> dict[str, Any]:
    return {
        "id": "pep_primary",
        "name": "Primary peptide",
        "sequence": sequence,
        "sequenceLength": len(sequence),
        "selectableForOptimization": True,
        "nonstandardResidues": [],
        "sourceReferences": [
            {
                "id": "primary-source",
                "sourceDatabase": "UniProtKB/Swiss-Prot",
                "sourceAccession": "P00001",
                "sourceRecordKey": "PRO_00001",
                "sourceUrl": "https://example.test/P00001",
                "peptideFeatureCoordinates": {"start": 2, "end": 5, "coordinateSystem": "fixture", "featureId": "PRO_00001"},
                "description": "Fixture primary source",
                "annotations": [{"type": "fixture"}],
                "modifications": [],
                "structureReferences": [],
                "availableExperimentalProperties": None,
                "evidenceType": "fixture",
                "sourceVersion": "fixture",
                "retrievalTimestamp": "2026-11-14T00:00:00Z",
            }
        ],
    }


def _write_extra(path: Path, records: list[dict[str, Any]]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """CREATE TABLE extra_peptides (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, display_name TEXT NOT NULL,
            sequence TEXT, search_text TEXT NOT NULL, record_json TEXT NOT NULL,
            imported_at TEXT NOT NULL)"""
        )
        for record in records:
            connection.execute(
                "INSERT INTO extra_peptides VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record["id"], record["kind"], record["name"], record.get("sequence"),
                    " ".join([record["id"], record["name"], *record.get("synonyms", [])]).casefold(),
                    json.dumps(record), "fixture",
                ),
            )
        connection.commit()
    finally:
        connection.close()


@pytest.fixture
def extra_database_path():
    """Use a normal system-temp file, not the restricted project tmp fixture."""

    path = Path(gettempdir()) / f"pepperq-extra-catalog-{uuid4().hex}.sqlite"
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            os.remove(candidate)


def _extra_sequence(record_id: str, sequence: str, accession: str, feature: str) -> dict[str, Any]:
    return {
        "id": record_id,
        "kind": "annotated_mature_peptide",
        "name": f"Extra {feature}",
        "sequence": sequence,
        "synonyms": [accession, feature],
        "qaoa_sequence_supported": True,
        "source_references": [{"database": "UniProtKB", "accession": accession, "url": f"https://example.test/{accession}"}],
        "coordinates": {"start": 2, "end": 5},
        "evidence": [],
        "provenance": "Fixture extra source",
    }


def _retatrutide() -> dict[str, Any]:
    return {
        "id": "pubchem:171390338",
        "kind": "modified_peptide",
        "name": "Retatrutide",
        "synonyms": ["retatrutide", "LY3437943", "LY-3437943"],
        "sequence": None,
        "qaoa_sequence_supported": False,
        "exclusion_reason": "Lipidated/modified peptide: simplified sequence chemistry is incomplete",
        "structure": {"formula": "C221H342N46O68", "molecular_weight_g_mol": "4731"},
        "source_references": [{"database": "PubChem", "accession": "171390338", "url": "https://example.test/retatrutide"}],
        "provenance": "Fixture PubChem record",
    }


def test_exact_sequence_merge_keeps_verified_source_provenance(extra_database_path: Path) -> None:
    database = extra_database_path
    _write_extra(
        database,
        [
            _extra_sequence("uniprot:P00001:PRO_00001", "ACDE", "P00001", "PRO_00001"),
            _extra_sequence("uniprot:P00002:PRO_00002", "ACDE", "P00002", "PRO_00002"),
        ],
    )

    result = CatalogIntegrator(_PrimaryLibrary([_primary()]), database).search(page_size=25)

    assert result["total"] == 1
    record = result["items"][0]
    assert record["id"] == "sequence:ACDE"
    assert record["catalogs"] == ["extra", "primary"]
    assert record["nonstandardResidues"] == []
    assert len(record["sourceReferences"]) == 2
    shared = next(item for item in record["sourceReferences"] if item["sourceAccession"] == "P00001")
    assert shared["catalogs"] == ["extra", "primary"]
    assert "primary:pep_primary" in record["catalogRecordIds"]
    assert "extra:uniprot:P00002:PRO_00002" in record["catalogRecordIds"]


def test_retatrutide_aliases_are_searchable_and_sequence_scoring_is_blocked(extra_database_path: Path) -> None:
    database = extra_database_path
    _write_extra(database, [_retatrutide()])
    catalog = CatalogIntegrator(_PrimaryLibrary([]), database)

    for alias in ("retatrutide", "LY3437943", "LY-3437943"):
        result = catalog.search(search=alias)
        assert result["total"] == 1
        record = result["items"][0]
        assert record["sequence"] is None
        assert record["nonstandardResidues"] == []
        assert not record["selectableForOptimization"]
        assert not record["sequenceOnlyScoringEligible"]
        assert "Lipidated/modified" in record["sequenceOnlyScoringExclusionReason"]
        assert record["molecularInformation"]["formula"] == "C221H342N46O68"


def test_primary_nonstandard_flags_are_retained_in_the_aggregate_contract(extra_database_path: Path) -> None:
    _write_extra(extra_database_path, [])
    primary = _primary("ACU")
    primary["selectableForOptimization"] = False
    primary["nonstandardResidues"] = ["U at position 3"]

    result = CatalogIntegrator(_PrimaryLibrary([primary]), extra_database_path).search()

    record = result["items"][0]
    assert record["nonstandardResidues"] == ["U at position 3"]
    assert not record["selectableForOptimization"]
    assert not record["sequenceOnlyScoringEligible"]


def test_global_filtering_pagination_and_stats_use_deduplicated_candidates(extra_database_path: Path) -> None:
    database = extra_database_path
    _write_extra(
        database,
        [
            _extra_sequence("uniprot:P00002:PRO_00002", "VVVV", "P00002", "PRO_00002"),
            _retatrutide(),
        ],
    )
    catalog = CatalogIntegrator(_PrimaryLibrary([_primary("ACDE")]), database)

    first = catalog.search(page=1, page_size=1)
    second = catalog.search(page=2, page_size=1)
    stats = catalog.stats()

    assert first["total"] == 3
    assert first["totalPages"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert catalog.search(source="PubChem")["items"][0]["name"] == "Retatrutide"
    assert catalog.search(min_length=4, max_length=4)["total"] == 2
    assert stats["deduplicatedCandidateCount"] == 3
    assert stats["rawCatalogRecordCount"] == 3
    assert stats["modifiedCandidateCount"] == 1
