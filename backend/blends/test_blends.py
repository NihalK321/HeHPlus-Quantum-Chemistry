"""Validate chemistry ranking, all binary assignments, and the actual circuit."""

import json
import sqlite3
from contextlib import closing

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import DiagonalGate
from qiskit.quantum_info import Statevector

from backend.api import app
from backend.blends.api import get_blend_catalog
from backend.blends.catalog import BlendCatalog
from backend.blends.models import BlendRequest, ChemicalGoals, ShortlistRequest
from backend.blends.quantum import probabilities, qubo_to_ising
from backend.blends.scoring import descriptors, pair_overlap, score_candidate
from backend.blends.solver import make_qubo, optimize_blend, shortlist


@pytest.fixture
def catalog(tmp_path):
    path = tmp_path / "references.sqlite3"
    sequences = ["AAAA", "KKKK", "DDDD", "GAGA", "VILV", "STST", "RGDR", "YGGM"]
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE peptides (id TEXT, source TEXT, name TEXT, sequence TEXT, length INTEGER, source_url TEXT, info TEXT)")
        rows = [(str(i), "test", f"Reference {i}", seq, len(seq), f"https://example.org/{i}", "{}") for i, seq in enumerate(sequences)]
        rows += [("modified", "test", "Modified", "CCCC", 4, "https://example.org/modified", json.dumps({"c_terminus": "NH2"})),
                 ("duplicate", "test", "Duplicate", "AAAA", 4, "https://example.org/duplicate", "{}"),
                 ("unsupported", "test", "Unsupported", "AAXA", 4, "https://example.org/unsupported", "{}")]
        connection.executemany("INSERT INTO peptides VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return BlendCatalog(library_path=tmp_path / "absent.sqlite3", legacy_path=path)


def test_catalog_deduplicates_and_excludes_modifications(catalog):
    records, stats = catalog.load()
    assert len(records) == 8
    assert stats["imported_source_records"] == 11
    assert stats["excluded_modified_or_unsupported_records"] == 2
    assert catalog.search("Reference 2")["items"][0]["sequence"] == "DDDD"
    assert catalog.search(page=2, page_size=3)["items"] == records[3:6]


def test_canonical_sources_take_precedence_and_block_modified_fallback(catalog):
    with closing(sqlite3.connect(catalog.library_path)) as connection, connection:
        connection.execute("CREATE TABLE peptides (id TEXT, sequence TEXT, canonical_name TEXT, selectable_for_optimization INTEGER)")
        connection.execute("CREATE TABLE peptide_sources (id TEXT, peptide_id TEXT, modifications_json TEXT, source_name TEXT, source_database TEXT, source_accession TEXT, source_url TEXT, retrieval_timestamp TEXT, source_version TEXT)")
        connection.executemany("INSERT INTO peptides VALUES (?, ?, ?, ?)", [("clean", "AAAA", "Canonical A", 1), ("modified", "KKKK", "Modified K", 1)])
        connection.executemany("INSERT INTO peptide_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            ("1", "clean", "[]", "Source A", "curated", "A1", "https://example.org/A1", "2026-11-14", "v1"),
            ("2", "modified", '["amidation"]', "Source K", "curated", "K1", "https://example.org/K1", "2026-11-14", "v1"),
        ])
    records, _ = catalog.load()
    assert len(records) == 7
    canonical = next(record for record in records if record["sequence"] == "AAAA")
    assert canonical["id"] == "library:clean"
    assert canonical["retrieved_at"] == "2026-11-14"
    assert not any(record["sequence"] == "KKKK" for record in records)


def test_missing_databases_stay_empty(tmp_path):
    catalog = BlendCatalog(tmp_path / "absent-library.db", tmp_path / "absent-legacy.db")
    assert catalog.search()["total"] == 0
    assert shortlist(catalog, ShortlistRequest())["scored_count"] == 0
    assert not catalog.library_path.exists()
    assert not catalog.legacy_path.exists()


def test_property_targets_change_rankings(catalog):
    positive = ChemicalGoals(target_charge=4, charge_weight=1, hydropathy_weight=0)
    negative = ChemicalGoals(target_charge=-4, charge_weight=1, hydropathy_weight=0)
    records, _ = catalog.load()
    by_sequence = {record["sequence"]: record for record in records}
    assert score_candidate(by_sequence["KKKK"], positive)["score"] > score_candidate(by_sequence["DDDD"], positive)["score"]
    assert score_candidate(by_sequence["KKKK"], negative)["score"] < score_candidate(by_sequence["DDDD"], negative)["score"]
    assert descriptors("AAAA", 7.4)["hydropathy"] == pytest.approx(1.8)
    assert pair_overlap("AAAA", "AAAA") == 1
    assert pair_overlap("AAAA", "KKKK") == 0
    assert pair_overlap("GAGA", "GAAA") == pytest.approx(1 / 3)


def test_shortlist_filters_without_changing_source(catalog):
    result = shortlist(catalog, ShortlistRequest(search="Reference", pool_size=4, min_length=4, max_length=4))
    assert result["scored_count"] == 8
    assert len(result["candidates"]) == 4
    assert result["candidates"][0]["score"] >= result["candidates"][-1]["score"]
    assert "score" not in catalog.load()[0][0]
    assert shortlist(catalog, ShortlistRequest(search="does not exist"))["candidates"] == []


def test_all_256_direct_qubo_and_ising_costs_agree(catalog):
    candidates = shortlist(catalog, ShortlistRequest())["candidates"]
    model = make_qubo(candidates, 3, 0.7)
    offset, fields, couplings = qubo_to_ising(model["constant"], model["linear"], model["quadratic"])
    for index, state in enumerate(model["states"]):
        selected = np.flatnonzero(state)
        direct = -sum(candidates[i]["score"] for i in selected)
        direct += 0.7 * sum(pair_overlap(candidates[i]["sequence"], candidates[j]["sequence"]) for i in selected for j in selected if i < j)
        direct += model["penalty"] * (len(selected) - 3) ** 2
        z = 1 - 2 * state
        assert model["energies"][index] == pytest.approx(direct)
        assert offset + fields @ z + z @ couplings @ z == pytest.approx(direct)
    feasible = model["states"].sum(axis=1) == 3
    assert feasible.sum() == 56
    assert model["energies"][~feasible].min() > model["energies"][feasible].max()
    assert model["states"][1].tolist() == [1, 0, 0, 0, 0, 0, 0, 0]


def test_native_gates_match_direct_diagonal_evolution(catalog):
    candidates = shortlist(catalog, ShortlistRequest(pool_size=4))["candidates"]
    model = make_qubo(candidates, 2, 0.3)
    _, fields, couplings = qubo_to_ising(model["constant"], model["linear"], model["quadratic"])
    parameters = [0.7, 0.3, 1.2, 0.6]
    scale = 4.2
    reference = QuantumCircuit(4)
    reference.h(range(4))
    for gamma, beta in np.array(parameters).reshape(-1, 2):
        reference.append(DiagonalGate(np.exp(-1j * gamma * model["energies"] / scale)), range(4))
        reference.rx(2 * beta, range(4))
    np.testing.assert_allclose(probabilities(fields, couplings, parameters, scale), Statevector.from_instruction(reference).probabilities(), atol=1e-12)


def test_solver_counts_export_and_exact_reference(catalog):
    request = BlendRequest(candidate_ids=[record["id"] for record in catalog.load()[0]], max_iterations=20)
    result = optimize_blend(catalog, request)
    assert result["provenance"] == "simulated"
    assert sum(result["counts"].values()) == request.shots
    assert len(result["classical_reference"]["candidate_ids"]) == 3
    assert result["benchmark"]["feasible_subset_count"] == 56
    assert result["evaluations"] == len(result["history"])
    exported = qasm2.loads(result["circuit_qasm"])
    distribution = Statevector.from_instruction(exported).probabilities()
    np.testing.assert_allclose(distribution, list(result["probabilities"].values()), atol=1e-12)
    if result["selected_blend"]:
        selected = result["selected_blend"]
        index = int(selected["bitstring"], 2)
        assert selected["candidate_ids"] == [identifier for i, identifier in enumerate(request.candidate_ids) if (index >> i) & 1]
        assert result["counts"][selected["bitstring"]] > 0
        assert result["benchmark"]["sampled_objective_gap"] >= -1e-10
    repeat = optimize_blend(catalog, request)
    assert result["counts"] == repeat["counts"]


def test_no_feasible_sample_does_not_substitute_classical(catalog, monkeypatch):
    def always_empty(fields, *args):
        values = np.zeros(2 ** len(fields))
        values[0] = 1
        return values
    monkeypatch.setattr("backend.blends.solver.probabilities", always_empty)
    result = optimize_blend(catalog, BlendRequest(candidate_ids=["0", "1", "2", "3"], max_iterations=10))
    assert result["selected_blend"] is None
    assert result["classical_reference"] is not None
    assert result["status"] == "no_feasible_sample"
    assert result["benchmark"]["observed_feasibility_rate"] == 0


@pytest.mark.parametrize("values", [
    {"candidate_ids": ["0", "0", "1", "2"]},
    {"candidate_ids": ["0", "1"], "blend_size": 2},
    {"candidate_ids": ["0", "1", "2", "3"], "charge_weight": 0, "hydropathy_weight": 0},
    {"candidate_ids": ["0", "1", "2", "3"], "target_charge": float("nan")},
])
def test_invalid_goals_and_pools_rejected(values):
    with pytest.raises(ValidationError):
        BlendRequest(**values)


def test_versioned_api_workflow(catalog):
    app.dependency_overrides[get_blend_catalog] = lambda: catalog
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/blends/catalog").json()["total"] == 8
            shortlist_response = client.post("/api/v1/blends/shortlist", json={})
            assert shortlist_response.status_code == 200
            ids = [candidate["id"] for candidate in shortlist_response.json()["candidates"]]
            response = client.post("/api/v1/blends/optimize", json={"candidate_ids": ids, "max_iterations": 10})
            assert response.status_code == 200, response.text
            assert response.json()["benchmark"]["qubits"] == 8
            assert client.post("/api/v1/blends/optimize", json={"candidate_ids": ["missing", "1", "2", "3"]}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_blend_catalog, None)
