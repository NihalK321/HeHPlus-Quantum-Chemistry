"""Focused tests for documented sequence-derived chemistry calculations.

Expected values below are from Biopython 1.88 for the stated free-terminus model.
The 1e-8 tolerance accommodates ordinary floating-point variation, not a change in
the pKa model or descriptor method.
"""

from __future__ import annotations

import pytest

from backend.peptide_analysis import (
    CandidateRecord,
    ResearchGoal,
    analyze_candidate_set,
    analyze_library_peptide,
    analyze_library_records,
    analyze_sequence,
    build_qubo_scoring_contract,
    compare_sequences,
    score_pair,
    score_sequence,
)


def test_standard_sequence_descriptors_match_documented_biopython_values() -> None:
    result = analyze_sequence("ACDE", identifier="test-acde", target_ph=7.0)

    assert result.status == "calculated"
    assert result.sequence_length == 4
    assert result.amino_acid_composition is not None
    assert result.amino_acid_composition["A"] == 1
    assert result.amino_acid_composition["C"] == 1
    assert result.amino_acid_composition["D"] == 1
    assert result.amino_acid_composition["E"] == 1
    assert result.molecular_mass_da == pytest.approx(436.4375, abs=1e-8)
    assert result.estimated_net_charge == pytest.approx(-2.204857899564378, abs=1e-8)
    assert result.estimated_isoelectric_point == pytest.approx(4.085211753845214, abs=1e-8)
    assert result.average_kyte_doolittle_hydropathy == pytest.approx(-0.675, abs=1e-12)
    assert result.basic_residue_composition == {"K": 0, "R": 0, "H": 0}
    assert result.acidic_residue_composition == {"D": 1, "E": 1}
    assert "Bjellqvist" in result.methods["net_charge"]


def test_nonstandard_modified_and_missing_sequences_withhold_calculated_values() -> None:
    nonstandard = analyze_sequence("ACX")
    assert nonstandard.status == "unsupported"
    assert nonstandard.molecular_mass_da is None
    assert nonstandard.unsupported_residues == ("X",)

    modified = analyze_sequence("ACDE", modifications=[{"name": "C-terminal amidation"}])
    assert modified.status == "unsupported"
    assert modified.estimated_net_charge is None
    assert "modification" in " ".join(modified.limitations).lower()

    unavailable = analyze_sequence(None)
    assert unavailable.status == "unavailable"
    assert unavailable.sequence_length is None

    blocked_termini = analyze_sequence("ACDE", terminal_chemistry="amidated")
    assert blocked_termini.status == "unsupported"
    assert blocked_termini.molecular_mass_da is None


def test_pairwise_terms_are_normalized_string_and_descriptor_proxies() -> None:
    pair = compare_sequences("AAAA", "AAAT", target_ph=7.0)

    assert pair.status == "calculated"
    assert pair.edit_distance == 1
    assert pair.normalized_edit_similarity == pytest.approx(0.75)
    assert pair.normalized_edit_diversity == pytest.approx(0.25)
    assert pair.absolute_hydropathy_difference == pytest.approx(0.625)
    assert pair.absolute_net_charge_difference is not None
    assert "do not predict physical association" in " ".join(pair.limitations).lower()


class _ReadOnlyLookup:
    def __init__(self, record: dict[str, object] | None) -> None:
        self.record = record
        self.calls: list[str] = []

    def get(self, peptide_id: str) -> dict[str, object] | None:
        self.calls.append(peptide_id)
        return self.record


def test_library_adapter_uses_injected_get_only_and_blocks_declared_modifications() -> None:
    lookup = _ReadOnlyLookup(
        {
            "id": "library-1",
            "name": "Imported ACDE",
            "sequence": "ACDE",
            "selectableForOptimization": True,
            "nonstandardResidues": [],
            "sourceCount": 1,
            "primarySource": {"modifications": []},
            "sourceReferences": [{"modifications": [{"name": "N-acetylation"}]}],
        }
    )

    result = analyze_library_peptide(lookup, "library-1")

    assert lookup.calls == ["library-1"]
    assert result.status == "unsupported"
    assert result.molecular_mass_da is None
    assert result.source_provenance is not None
    assert result.source_provenance["library_record_id"] == "library-1"


def test_initial_eight_candidate_set_has_28_pairwise_proxy_terms() -> None:
    records = (
        CandidateRecord("p1", "ACDE"),
        CandidateRecord("p2", "KRRH"),
        CandidateRecord("p3", "VVVV"),
        CandidateRecord("p4", "GSGS"),
        CandidateRecord("p5", "WYFQ"),
        CandidateRecord("p6", "NQST"),
        CandidateRecord("p7", "ILMP"),
        CandidateRecord("p8", "CDEF"),
    )

    result = analyze_candidate_set(records, target_ph=7.0, require_exactly_eight=True)

    assert len(result.candidates) == 8
    assert result.calculated_candidate_count == 8
    assert len(result.pairwise_terms) == 28
    assert all(pair.status == "calculated" for pair in result.pairwise_terms)


def test_read_only_batch_adapter_supports_eight_imported_record_mappings() -> None:
    sequences = ("ACDE", "KRRH", "VVVV", "GSGS", "WYFQ", "NQST", "ILMP", "CDEF")
    imported_records = tuple(
        {
            "id": f"library-{index}",
            "sequence": sequence,
            "selectableForOptimization": True,
            "nonstandardResidues": [],
            "sourceCount": 1,
            "primarySource": {"modifications": []},
            "sourceReferences": [],
        }
        for index, sequence in enumerate(sequences, start=1)
    )

    result = analyze_library_records(imported_records, require_exactly_eight=True)

    assert len(result.candidates) == 8
    assert len(result.pairwise_terms) == 28
    assert all(candidate.status == "calculated" for candidate in result.candidates)


def test_researcher_defined_scores_have_no_implicit_objective_or_pair_penalty() -> None:
    candidates = analyze_candidate_set(
        (
            CandidateRecord("p1", "ACDE"),
            CandidateRecord("p2", "KRRH"),
        )
    )
    individual_goals = (
        ResearchGoal(
            metric="average_hydropathy",
            direction="target",
            target=0.0,
            lower_bound=-4.0,
            upper_bound=4.0,
            weight=2.0,
            rationale="Example only: researcher-defined neutral hydropathy target.",
        ),
        ResearchGoal(
            metric="net_charge",
            direction="maximize",
            lower_bound=-5.0,
            upper_bound=5.0,
            weight=1.0,
        ),
    )
    pairwise_goals = (
        ResearchGoal(
            metric="normalized_edit_diversity",
            direction="maximize",
            lower_bound=0.0,
            upper_bound=1.0,
            weight=1.0,
        ),
    )

    individual_score = score_sequence(candidates.candidates[0], individual_goals)
    pair_score = score_pair(candidates.pairwise_terms[0], pairwise_goals)
    contract = build_qubo_scoring_contract(
        candidates,
        individual_goals=individual_goals,
        pairwise_goals=pairwise_goals,
    )

    assert 0.0 <= individual_score.score <= 1.0
    assert len(individual_score.contributions) == 2
    assert 0.0 <= pair_score.score <= 1.0
    assert set(contract.individual_scores) == {"p1", "p2"}
    assert set(contract.pairwise_scores) == {"p1|p2"}


def test_initial_eight_requirement_rejects_an_incomplete_candidate_set() -> None:
    with pytest.raises(ValueError, match="exactly eight"):
        analyze_candidate_set((CandidateRecord("p1", "ACDE"),), require_exactly_eight=True)

