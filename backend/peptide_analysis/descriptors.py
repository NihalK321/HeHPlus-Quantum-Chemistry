"""Sequence-derived peptide descriptors and transparent pairwise proxy terms."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import combinations
from numbers import Real
from typing import Any

from Bio.SeqUtils import molecular_weight
from Bio.SeqUtils.ProtParam import ProteinAnalysis

from .models import (
    STANDARD_AMINO_ACIDS,
    CandidateRecord,
    CandidateSetAnalysis,
    PairwiseAnalysis,
    SequenceAnalysis,
)


FREE_TERMINI = "linear, unmodified peptide with free amino and carboxyl termini"

_METHODS: dict[str, str] = {
    "molecular_mass": (
        "Biopython Bio.SeqUtils.molecular_weight(seq_type='protein', "
        "monoisotopic=False): average molecular mass in Da for a linear, "
        "unmodified peptide with free termini."
    ),
    "net_charge": (
        "Biopython Bio.SeqUtils.ProtParam.ProteinAnalysis.charge_at_pH using "
        "the Bjellqvist pKa model; a sequence-derived estimate, not a measurement."
    ),
    "isoelectric_point": (
        "Biopython Bio.SeqUtils.ProtParam.ProteinAnalysis.isoelectric_point "
        "using the Bjellqvist pKa model; a sequence-derived estimate."
    ),
    "hydropathy": (
        "Biopython Bio.SeqUtils.ProtParam.ProteinAnalysis.gravy using the "
        "Kyte-Doolittle hydropathy scale."
    ),
    "pairwise_sequence": (
        "Levenshtein edit distance normalized by the longer sequence length. "
        "It is a string-level sequence proxy, not biological similarity or compatibility."
    ),
    "pairwise_property": (
        "Absolute difference between calculated sequence descriptors at the stated pH. "
        "It is not an interaction, binding, compatibility, or safety measurement."
    ),
}


def analyze_sequence(
    sequence: str | None,
    *,
    identifier: str | None = None,
    target_ph: float = 7.0,
    modifications: Iterable[Any] | None = None,
    terminal_chemistry: str = "free",
    source_provenance: Mapping[str, Any] | None = None,
) -> SequenceAnalysis:
    """Calculate documented descriptors for one standard, unmodified sequence.

    Any declared modification, nonstandard residue, unknown terminal chemistry, or
    missing sequence withholds derived property values instead of silently applying
    a free-terminal, unmodified-sequence model to a chemically different peptide.
    """

    _validate_ph(target_ph)
    normalised_modifications = _normalise_modifications(modifications)
    normalised_sequence = _normalise_sequence(sequence)

    if normalised_sequence is None:
        return _unavailable_sequence(
            identifier=identifier,
            sequence=None,
            target_ph=float(target_ph),
            limitation="No peptide sequence was supplied; sequence-derived descriptors were not calculated.",
            source_provenance=source_provenance,
        )

    unsupported = tuple(sorted({residue for residue in normalised_sequence if residue not in STANDARD_AMINO_ACIDS}))
    limitations: list[str] = []
    if unsupported:
        limitations.append(
            "Unsupported or nonstandard one-letter residue symbols were supplied: "
            + ", ".join(unsupported)
            + "."
        )
    if normalised_modifications:
        limitations.append(
            "Declared chemical modification(s) prevent an unmodified-sequence calculation: "
            + "; ".join(normalised_modifications)
            + "."
        )
    if terminal_chemistry != "free":
        limitations.append(
            "Only free amino and carboxyl termini are implemented; supplied terminal chemistry "
            f"was {terminal_chemistry!r}."
        )

    if limitations:
        return SequenceAnalysis(
            identifier=identifier,
            sequence=normalised_sequence,
            status="unsupported",
            target_ph=float(target_ph),
            sequence_length=len(normalised_sequence),
            amino_acid_composition=None,
            molecular_mass_da=None,
            estimated_net_charge=None,
            estimated_isoelectric_point=None,
            average_kyte_doolittle_hydropathy=None,
            basic_residue_composition=None,
            acidic_residue_composition=None,
            basic_residue_fraction=None,
            acidic_residue_fraction=None,
            terminal_chemistry_assumption=FREE_TERMINI,
            methods=_METHODS,
            limitations=tuple(limitations),
            unsupported_residues=unsupported,
            source_provenance=source_provenance,
        )

    protein = ProteinAnalysis(normalised_sequence)
    composition = {residue: normalised_sequence.count(residue) for residue in sorted(STANDARD_AMINO_ACIDS)}
    basic = {residue: composition[residue] for residue in ("K", "R", "H")}
    acidic = {residue: composition[residue] for residue in ("D", "E")}
    sequence_length = len(normalised_sequence)

    return SequenceAnalysis(
        identifier=identifier,
        sequence=normalised_sequence,
        status="calculated",
        target_ph=float(target_ph),
        sequence_length=sequence_length,
        amino_acid_composition=composition,
        molecular_mass_da=float(molecular_weight(normalised_sequence, seq_type="protein", monoisotopic=False)),
        estimated_net_charge=float(protein.charge_at_pH(float(target_ph))),
        estimated_isoelectric_point=float(protein.isoelectric_point()),
        average_kyte_doolittle_hydropathy=float(protein.gravy()),
        basic_residue_composition=basic,
        acidic_residue_composition=acidic,
        basic_residue_fraction=sum(basic.values()) / sequence_length,
        acidic_residue_fraction=sum(acidic.values()) / sequence_length,
        terminal_chemistry_assumption=FREE_TERMINI,
        methods=_METHODS,
        limitations=(
            "All values are calculated from the submitted primary sequence under the stated "
            "terminal assumptions; they are not experimentally measured peptide properties.",
        ),
        source_provenance=source_provenance,
    )


def compare_sequences(
    left: SequenceAnalysis | str,
    right: SequenceAnalysis | str,
    *,
    target_ph: float = 7.0,
) -> PairwiseAnalysis:
    """Return string-level similarity/diversity and descriptor-difference terms.

    The pairwise values intentionally remain interpretable proxy terms. They do
    not assert peptide-peptide compatibility, interaction strength, synergy, or
    biological effect.
    """

    _validate_ph(target_ph)
    left_analysis = _as_analysis(left, target_ph=float(target_ph))
    right_analysis = _as_analysis(right, target_ph=float(target_ph))

    if not left_analysis.is_calculated or not right_analysis.is_calculated:
        return PairwiseAnalysis(
            left_identifier=left_analysis.identifier,
            right_identifier=right_analysis.identifier,
            status="unsupported",
            target_ph=float(target_ph),
            normalized_edit_similarity=None,
            normalized_edit_diversity=None,
            edit_distance=None,
            absolute_hydropathy_difference=None,
            absolute_net_charge_difference=None,
            methods=_METHODS,
            limitations=(
                "Pairwise terms require two fully calculated, standard, unmodified sequences.",
                *left_analysis.limitations,
                *right_analysis.limitations,
            ),
        )

    assert left_analysis.sequence is not None
    assert right_analysis.sequence is not None
    edit_distance = _levenshtein_distance(left_analysis.sequence, right_analysis.sequence)
    denominator = max(len(left_analysis.sequence), len(right_analysis.sequence))
    diversity = edit_distance / denominator if denominator else 0.0

    assert left_analysis.average_kyte_doolittle_hydropathy is not None
    assert right_analysis.average_kyte_doolittle_hydropathy is not None
    assert left_analysis.estimated_net_charge is not None
    assert right_analysis.estimated_net_charge is not None
    return PairwiseAnalysis(
        left_identifier=left_analysis.identifier,
        right_identifier=right_analysis.identifier,
        status="calculated",
        target_ph=float(target_ph),
        normalized_edit_similarity=1.0 - diversity,
        normalized_edit_diversity=diversity,
        edit_distance=edit_distance,
        absolute_hydropathy_difference=abs(
            left_analysis.average_kyte_doolittle_hydropathy
            - right_analysis.average_kyte_doolittle_hydropathy
        ),
        absolute_net_charge_difference=abs(
            left_analysis.estimated_net_charge - right_analysis.estimated_net_charge
        ),
        methods=_METHODS,
        limitations=(
            "Pairwise values are sequence and descriptor proxies only; they do not predict "
            "physical association, compatibility, affinity, aggregation, solubility, or safety.",
        ),
    )


def analyze_candidate_set(
    records: Iterable[CandidateRecord],
    *,
    target_ph: float = 7.0,
    require_exactly_eight: bool = False,
    max_candidates: int = 8,
) -> CandidateSetAnalysis:
    """Analyze a small candidate set and all candidate pairs without database writes.

    The default maximum of eight is intentional for the initial PepperQ blend
    experiment. Eight candidates generate 28 pair terms and match an 8-qubit,
    one-binary-variable-per-candidate QUBO workflow owned elsewhere.
    """

    _validate_ph(target_ph)
    candidate_records = tuple(records)
    if not candidate_records:
        raise ValueError("At least one candidate record is required.")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive.")
    if len(candidate_records) > max_candidates:
        raise ValueError(
            f"This small-candidate helper accepts at most {max_candidates} records; "
            "split or explicitly redesign the downstream optimization experiment."
        )
    if require_exactly_eight and len(candidate_records) != 8:
        raise ValueError("The initial validated experiment requires exactly eight candidate records.")

    identifiers = [record.identifier for record in candidate_records]
    if any(not identifier.strip() for identifier in identifiers):
        raise ValueError("Each candidate requires a non-empty identifier.")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Candidate identifiers must be unique.")

    candidates = tuple(
        analyze_sequence(
            record.sequence,
            identifier=record.identifier,
            target_ph=float(target_ph),
            modifications=record.modifications,
            source_provenance=record.provenance,
        )
        for record in candidate_records
    )
    pairwise_terms = tuple(
        compare_sequences(left, right, target_ph=float(target_ph))
        for left, right in combinations(candidates, 2)
    )
    return CandidateSetAnalysis(
        target_ph=float(target_ph),
        candidates=candidates,
        pairwise_terms=pairwise_terms,
        limitations=(
            "The set contains calculated sequence descriptors and transparent pairwise proxies. "
            "It does not provide a peptide compatibility, synergy, efficacy, or safety score.",
        ),
    )


def _as_analysis(value: SequenceAnalysis | str, *, target_ph: float) -> SequenceAnalysis:
    if isinstance(value, SequenceAnalysis):
        if abs(value.target_ph - target_ph) > 1e-12:
            raise ValueError(
                "Both existing sequence analyses must use the requested target pH before "
                "their net-charge difference can be compared."
            )
        return value
    if isinstance(value, str):
        return analyze_sequence(value, target_ph=target_ph)
    raise TypeError("compare_sequences accepts a sequence string or SequenceAnalysis.")


def _unavailable_sequence(
    *,
    identifier: str | None,
    sequence: str | None,
    target_ph: float,
    limitation: str,
    source_provenance: Mapping[str, Any] | None,
) -> SequenceAnalysis:
    return SequenceAnalysis(
        identifier=identifier,
        sequence=sequence,
        status="unavailable",
        target_ph=target_ph,
        sequence_length=None,
        amino_acid_composition=None,
        molecular_mass_da=None,
        estimated_net_charge=None,
        estimated_isoelectric_point=None,
        average_kyte_doolittle_hydropathy=None,
        basic_residue_composition=None,
        acidic_residue_composition=None,
        basic_residue_fraction=None,
        acidic_residue_fraction=None,
        terminal_chemistry_assumption=FREE_TERMINI,
        methods=_METHODS,
        limitations=(limitation,),
        source_provenance=source_provenance,
    )


def _normalise_sequence(sequence: str | None) -> str | None:
    if sequence is None:
        return None
    if not isinstance(sequence, str):
        return None
    normalised = sequence.strip().upper()
    return normalised or None


def _normalise_modifications(modifications: Iterable[Any] | None) -> tuple[str, ...]:
    if modifications is None:
        return ()
    if isinstance(modifications, str):
        return (modifications,) if modifications.strip() else ()

    labels: list[str] = []
    for modification in modifications:
        if modification is None:
            continue
        if isinstance(modification, Mapping):
            for key in ("name", "modification", "description", "type"):
                value = modification.get(key)
                if isinstance(value, str) and value.strip():
                    labels.append(value.strip())
                    break
            else:
                labels.append("source-declared modification with unspecified chemistry")
        else:
            value = str(modification).strip()
            if value:
                labels.append(value)
    return tuple(labels)


def _validate_ph(target_ph: float) -> None:
    if isinstance(target_ph, bool) or not isinstance(target_ph, Real):
        raise TypeError("target_ph must be a real number between 0 and 14.")
    if not 0.0 <= float(target_ph) <= 14.0:
        raise ValueError("target_ph must be between 0 and 14 inclusive.")


def _levenshtein_distance(left: str, right: str) -> int:
    """Calculate a deterministic edit distance without an alignment-score model."""

    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_residue in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_residue in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_residue != right_residue),
                )
            )
        previous = current
    return previous[-1]

