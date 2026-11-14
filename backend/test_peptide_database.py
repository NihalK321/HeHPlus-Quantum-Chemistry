"""Offline contract tests: no source database or network is required."""

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from .api import app, peptide_database
from .peptide_database import PeptideDatabase
from .schema import PeptideLookupRequest


@pytest.fixture
def database(tmp_path):
    return PeptideDatabase(tmp_path / "peptides.sqlite3")


def source_record(identifier=16, sequence="ENREVPPGFTALIKTLRKCKII", **extra):
    return {"id": identifier, "name": "Distinctin chain 1", "sequence": sequence,
            "complexity": "monomer", "cTerminus": None, **extra}


def source_client(records):
    def handler(request):
        offset = int(request.url.params.get("offset", 0))
        return httpx.Response(200, json={"data": records[offset:offset + 2], "totalCount": len(records)})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_import_pagination_and_residue_filter(database):
    records = [source_record(), source_record(17, "YGGFL"),
               source_record(18, "YgGFL"), source_record(19, "YGGXL"),
               source_record(20, "YGGFL", complexity="multimer")]
    with source_client(records) as client:
        result = database.sync(client, progress=None)
    assert result["sources"]["DBAASP"] == 2
    assert result["sync"]["downloaded"] == 5
    assert result["sync"]["skipped"] == 3
    result = database.lookup(PeptideLookupRequest(sequence="YGGFL", include_details=False))
    assert result["exact_match_count"] == 1
    assert result["exact_matches"][0]["id"] == "dbaasp:17"


def test_failed_sync_preserves_old_catalog(database):
    with source_client([source_record()]) as client:
        database.sync(client, progress=None)
    def fail(request):
        if request.url.params["offset"] == "0":
            return httpx.Response(200, json={"data": [source_record(99, "YGGFL")], "totalCount": 2})
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            database.sync(client, progress=None)
    result = database.lookup(PeptideLookupRequest(sequence="ENREVPPGFTALIKTLRKCKII", include_details=False))
    assert result["exact_matches"][0]["id"] == "dbaasp:16"
    assert database.status()["sources"]["DBAASP"] == 1


def test_partial_sequence_is_not_exact(database):
    result = database.lookup(PeptideLookupRequest(sequence="YGGF", include_details=False))
    assert result["exact_matches"] == []
    assert result["similar_sequences"] == []


def test_local_reference_and_similar_sequence_do_not_predict_activity(database):
    exact = database.lookup(PeptideLookupRequest(sequence=" yggfm "))
    assert exact["exact_matches"][0]["name"] == "Met-enkephalin"
    assert exact["exact_matches"][0]["documented_role"]
    similar = database.lookup(PeptideLookupRequest(sequence="YGGFL", include_similar=True, minimum_identity=0.8))
    assert similar["exact_match_count"] == 0
    assert similar["similar_sequences"][0]["sequence_identity"] == 0.8
    assert similar["similar_sequences"][0]["documented_role"] is None


def test_multiple_records_same_sequence_are_preserved(database):
    with source_client([source_record(1, "YGGFL"), source_record(2, "YGGFL")]) as client:
        database.sync(client, progress=None)
    result = database.lookup(PeptideLookupRequest(sequence="YGGFL", limit=1, include_details=False))
    assert result["exact_match_count"] == 2
    assert len(result["exact_matches"]) == 1


def test_details_return_assay_context_and_are_cached(database):
    with source_client([source_record()]) as client:
        database.sync(client, progress=None)
    calls = []
    def detail(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"id": 16, "sequence": "ENREVPPGFTALIKTLRKCKII",
            "targetActivities": [{"targetSpecies": {"name": "E. coli"}, "activityMeasureValue": "MIC",
                "concentration": ">100", "unit": {"name": "uM"}, "medium": {"name": "MHB"}}],
            "articles": [{"title": "Example study", "year": 2020, "pubmed": {"pubmedId": "123"}}]})
    query = PeptideLookupRequest(sequence="ENREVPPGFTALIKTLRKCKII")
    with httpx.Client(transport=httpx.MockTransport(detail)) as client:
        first = database.lookup(query, client)["exact_matches"][0]
        second = database.lookup(query, client)["exact_matches"][0]
    assert len(calls) == 1
    assert first["activities"][0]["reported_concentration"] == ">100"
    assert first["activities"][0]["medium"] == "MHB"
    assert second["references"][0]["pubmed_id"] == "123"


def test_source_failure_is_not_reported_as_no_match(database):
    with source_client([source_record()]) as client:
        database.sync(client, progress=None)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        result = database.lookup(PeptideLookupRequest(sequence="ENREVPPGFTALIKTLRKCKII"), client)
    assert result["exact_match_count"] == 1
    assert "unavailable" in result["exact_matches"][0]["detail_status"]


@pytest.mark.parametrize("sequence", ["", "A", "AX", "A" * 201])
def test_bad_lookup_sequences(sequence):
    with pytest.raises(ValidationError):
        PeptideLookupRequest(sequence=sequence)


def test_lookup_api(database):
    app.dependency_overrides[peptide_database] = lambda: database
    try:
        with TestClient(app) as client:
            assert client.get("/peptides/status").json()["indexed_records"] >= 3
            response = client.post("/peptides/lookup", json={"sequence": "CYIQNCPLG"})
            assert response.status_code == 200
            assert response.json()["exact_matches"][0]["name"] == "Oxytocin"
            assert client.post("/peptides/lookup", json={"sequence": "Aib"}).status_code == 422
    finally:
        app.dependency_overrides.clear()
