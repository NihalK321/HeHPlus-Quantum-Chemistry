"""Offline tests for the provenance-preserving peptide library.

Fixtures exercise documented response shapes only. They are not imported as
scientific data and no test reaches a public database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Any
from urllib.error import URLError
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import app
from backend.peptide_library.api_router import get_peptide_library
from backend.peptide_library.dbaasp import extract_dbaasp_peptide_records
from backend.peptide_library.http_client import JsonHttpClient, SourceRequestError
from backend.peptide_library.models import SourcePeptideRecord
from backend.peptide_library.service import create_service
from backend.peptide_library.storage import PeptideRepository
from backend.peptide_library.uniprot import UniProtPeptideConnector, extract_mature_peptide_records, parse_next_link
from backend.peptide_library.validation import validate_sequence


@pytest.fixture
def library_database_path():
    """Use a unique system-temp SQLite file without changing shared fixtures."""

    path = Path(gettempdir()) / f"pepperq-library-{uuid4().hex}.sqlite3"
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            os.remove(candidate)


def source_record(
    *,
    sequence: str = "ACDE",
    source_database: str = "FixtureDB",
    source_accession: str = "FIXTURE_1",
    source_record_key: str = "fixture-record-1",
) -> SourcePeptideRecord:
    return SourcePeptideRecord(
        sequence=sequence,
        source_database=source_database,
        source_accession=source_accession,
        source_url=f"https://example.test/{source_accession}",
        source_record_key=source_record_key,
        name="Fixture peptide",
        annotations=[{"type": "Fixture annotation", "description": "Response-shape test fixture"}],
        evidence_type="fixture",
        retrieval_timestamp="2026-11-14T00:00:00Z",
    )


def uniprot_fixture() -> dict[str, Any]:
    return {
        "primaryAccession": "P00001",
        "uniProtkbId": "FIXTURE_TEST",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Fixture precursor"}}},
        "organism": {"scientificName": "Fixture organism"},
        "sequence": {"value": "MACDEFGHIK"},
        "features": [
            {
                "type": "Peptide",
                "featureId": "PRO_000000001",
                "description": "Fixture mature peptide",
                "location": {
                    "start": {"value": 2, "modifier": "EXACT"},
                    "end": {"value": 5, "modifier": "EXACT"},
                },
                "evidences": [{"evidenceCode": "ECO:0000000"}],
            }
        ],
    }


def test_mature_feature_extraction_uses_one_based_inclusive_coordinates():
    records = extract_mature_peptide_records(
        uniprot_fixture(),
        source_version="UniProt release fixture",
        retrieval_timestamp="2026-11-14T00:00:00Z",
    )

    assert len(records) == 1
    assert records[0].sequence == "ACDE"
    assert records[0].parent_protein_accession == "P00001"
    assert records[0].peptide_feature_coordinates == {
        "start": 2,
        "end": 5,
        "coordinate_system": "UniProt parent sequence; 1-based inclusive",
        "feature_id": "PRO_000000001",
    }


def test_uncertain_or_invalid_uniprot_feature_coordinates_are_skipped():
    fixture = uniprot_fixture()
    fixture["features"][0]["location"]["start"]["modifier"] = "UNKNOWN"
    assert extract_mature_peptide_records(fixture, source_version=None, retrieval_timestamp="now") == []

    fixture = uniprot_fixture()
    fixture["features"][0]["location"]["end"]["value"] = 999
    assert extract_mature_peptide_records(fixture, source_version=None, retrieval_timestamp="now") == []


def test_sequence_validation_preserves_nonstandard_source_residues_but_blocks_selection():
    standard = validate_sequence(" acde ")
    nonstandard = validate_sequence("ACU")
    invalid = validate_sequence("AC1")

    assert standard.normalized_sequence == "ACDE"
    assert standard.selectable_for_optimization
    assert nonstandard.is_source_valid
    assert not nonstandard.selectable_for_optimization
    assert nonstandard.nonstandard_residues == ({"position": 3, "residue": "U"},)
    assert not invalid.is_source_valid


def test_sqlite_deduplicates_sequences_without_losing_source_provenance(library_database_path):
    database_path = library_database_path
    repository = PeptideRepository(database_path)
    first = repository.upsert(source_record(source_database="Source A", source_accession="A1", source_record_key="A1-feature"))
    second = repository.upsert(source_record(source_database="Source B", source_accession="B1", source_record_key="B1-feature"))
    repository.close()

    reopened = PeptideRepository(database_path)
    stats = reopened.stats()
    detail = reopened.get(first.peptide_id)

    assert first.peptide_created
    assert not second.peptide_created
    assert second.source_reference_created
    assert stats["totalImportedRecords"] == 1
    assert stats["totalSourceRecords"] == 2
    assert detail is not None
    assert {source["sourceDatabase"] for source in detail["sourceReferences"]} == {"Source A", "Source B"}
    reopened.close()


def test_search_and_pagination_are_parameterized_and_bounded(library_database_path):
    repository = PeptideRepository(library_database_path)
    repository.upsert(source_record(sequence="ACDE", source_record_key="first"))
    repository.upsert(source_record(sequence="FGHIK", source_record_key="second"))
    repository.upsert(source_record(sequence="LMNPQR", source_record_key="third"))

    result = repository.search(search="FGH", minimum_length=4, maximum_length=5, page=1, page_size=1)
    assert result["total"] == 1
    assert result["items"][0]["sequence"] == "FGHIK"
    assert result["items"][0]["sourceReferences"][0]["id"]
    with pytest.raises(ValueError, match="page_size"):
        repository.search(page_size=101)
    with pytest.raises(ValueError, match="minimum_length"):
        repository.search(minimum_length=6, maximum_length=5)
    repository.close()


def test_source_failure_has_a_clear_typed_error_and_no_silent_fallback():
    def offline_opener(*_args: Any, **_kwargs: Any):
        raise URLError("offline")

    client = JsonHttpClient(max_retries=0, opener=offline_opener)
    with pytest.raises(SourceRequestError, match="offline"):
        client.get_json("https://example.test/peptides", source="Fixture source")


def test_uniprot_connector_parses_recorded_response_shape_without_network():
    class FakeResponse:
        status = 200
        headers = {"X-UniProt-Release": "fixture", "X-UniProt-Release-Date": "today"}

        def read(self):
            return json.dumps({"results": [uniprot_fixture()]}).encode("utf-8")

        def close(self):
            return None

    connector = UniProtPeptideConnector(
        JsonHttpClient(max_retries=0, opener=lambda *_args, **_kwargs: FakeResponse())
    )
    records = list(connector.iter_mature_peptides(limit=1, page_size=1))
    assert records[0].sequence == "ACDE"
    assert records[0].source_version == "UniProt release fixture (today)"


def test_uniprot_cursor_parser_keeps_commas_inside_fields_query_parameter():
    link = (
        '<https://rest.uniprot.org/uniprotkb/search?fields=accession,id,sequence&cursor=next-page>; '
        'rel="next"'
    )
    assert parse_next_link(link) == "https://rest.uniprot.org/uniprotkb/search?fields=accession,id,sequence&cursor=next-page"


def test_dbaasp_complex_keeps_explicit_monomers_separate():
    detail = {
        "id": 1,
        "dbaaspId": "DBAASPR_1",
        "name": "Fixture complex",
        "monomers": [
            {"id": 2, "dbaaspId": "DBAASPR_2", "name": "Chain one", "sequence": "ACDE", "pdbs": []},
            {
                "id": 3,
                "dbaaspId": "DBAASPR_3",
                "name": "Chain two",
                "sequence": "FGHI",
                "pdbs": [{"name": "1XKM_1", "pdbUrl": "https://www.rcsb.org/structure/1XKM"}],
            },
        ],
    }
    records = extract_dbaasp_peptide_records(detail, source_version="fixture", retrieval_timestamp="now")

    assert [record.sequence for record in records] == ["ACDE", "FGHI"]
    assert "ACDEFGHI" not in {record.sequence for record in records}
    assert records[1].structure_references[0]["identifier"] == "1XKM"


def test_library_api_returns_search_detail_and_actual_stats(library_database_path):
    service = create_service(library_database_path)
    outcome = service.repository.upsert(source_record(sequence="ACDE", source_database="UniProtKB/Swiss-Prot"))
    app.dependency_overrides[get_peptide_library] = lambda: service
    try:
        with TestClient(app) as client:
            collection = client.get("/api/peptides", params={"search": "ACDE"})
            assert collection.status_code == 200
            assert collection.json()["total"] == 1
            assert collection.json()["items"][0]["sequence"] == "ACDE"

            stats = client.get("/api/peptides/stats")
            assert stats.status_code == 200
            assert stats.json()["totalPeptides"] == 1
            assert stats.json()["bySource"] == {"UniProtKB/Swiss-Prot": 1}

            detail = client.get(f"/api/peptides/{outcome.peptide_id}")
            assert detail.status_code == 200
            assert detail.json()["sourceReferences"][0]["sourceAccession"] == "FIXTURE_1"
            assert client.get("/api/peptides/missing").status_code == 404
            assert client.get("/api/peptides", params={"page_size": 101}).status_code == 422
    finally:
        app.dependency_overrides.clear()
        service.repository.close()
