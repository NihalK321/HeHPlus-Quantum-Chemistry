"""Read-only adapters for peptide records already imported by the library."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any, Protocol

from .descriptors import analyze_candidate_set, analyze_sequence
from .models import CandidateRecord, CandidateSetAnalysis, SequenceAnalysis


class PeptideLookup(Protocol):
    """The only library capability this package needs: a non-mutating lookup."""

    def get(self, peptide_id: str) -> Mapping[str, Any] | None:
        """Return one peptide-library record, or None if it is unavailable."""


def analyze_library_peptide(
    lookup: PeptideLookup,
    peptide_id: str,
    *,
    target_ph: float = 7.0,
) -> SequenceAnalysis:
    """Read and analyze one previously imported record without opening or writing a DB.

    Callers pass an existing repository or service explicitly. The adapter never
    constructs PeptideLibraryService and never imports, updates, or upserts data.
    """

    record = lookup.get(peptide_id)
    if record is None:
        unavailable = analyze_sequence(None, identifier=peptide_id, target_ph=target_ph)
        return replace(
            unavailable,
            limitations=(
                f"Peptide-library record {peptide_id!r} was not found; no descriptors were calculated.",
            ),
        )
    return analyze_library_record(record, target_ph=target_ph)


def analyze_library_record(
    record: Mapping[str, Any],
    *,
    target_ph: float = 7.0,
) -> SequenceAnalysis:
    """Analyze a peptide-library response mapping with provenance and safety guards."""

    identifier_value = record.get("id")
    identifier = str(identifier_value) if identifier_value is not None else None
    sequence_value = record.get("sequence")
    sequence = sequence_value if isinstance(sequence_value, str) else None
    declared_modifications = _source_modifications(record)
    provenance = _provenance(record)
    analysis = analyze_sequence(
        sequence,
        identifier=identifier,
        target_ph=target_ph,
        modifications=declared_modifications,
        source_provenance=provenance,
    )

    nonstandard = _as_labels(record.get("nonstandardResidues"))
    selectable = record.get("selectableForOptimization")
    limitations = list(analysis.limitations)
    if nonstandard:
        limitations.append(
            "The peptide library declares nonstandard residue(s): " + "; ".join(nonstandard) + "."
        )
    if selectable is False:
        limitations.append(
            "The peptide library marks this record as not selectable for optimization; "
            "sequence-derived values are withheld by this adapter."
        )

    if nonstandard or selectable is False:
        return replace(
            analysis,
            status="unsupported",
            amino_acid_composition=None,
            molecular_mass_da=None,
            estimated_net_charge=None,
            estimated_isoelectric_point=None,
            average_kyte_doolittle_hydropathy=None,
            basic_residue_composition=None,
            acidic_residue_composition=None,
            basic_residue_fraction=None,
            acidic_residue_fraction=None,
            limitations=tuple(limitations),
            unsupported_residues=tuple(sorted(set((*analysis.unsupported_residues, *nonstandard)))),
        )
    return analysis


def analyze_library_records(
    records: Iterable[Mapping[str, Any]],
    *,
    target_ph: float = 7.0,
    require_exactly_eight: bool = False,
) -> CandidateSetAnalysis:
    """Analyze already-read library records as a bounded, read-only candidate set.

    This is the batch boundary for the initial eight-candidate experiment. It
    neither instantiates a service nor changes any library table or source record.
    """

    candidate_records = tuple(_candidate_record_from_library_record(record) for record in records)
    return analyze_candidate_set(
        candidate_records,
        target_ph=target_ph,
        require_exactly_eight=require_exactly_eight,
    )


def _source_modifications(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Collect source-declared modifications without attempting to interpret them."""

    modifications: list[Any] = []
    primary_source = record.get("primarySource")
    if isinstance(primary_source, Mapping):
        modifications.extend(_as_items(primary_source.get("modifications")))
    source_references = record.get("sourceReferences")
    if isinstance(source_references, list):
        for source in source_references:
            if isinstance(source, Mapping):
                modifications.extend(_as_items(source.get("modifications")))
    return tuple(modifications)


def _candidate_record_from_library_record(record: Mapping[str, Any]) -> CandidateRecord:
    identifier_value = record.get("id")
    if not isinstance(identifier_value, str) or not identifier_value.strip():
        raise ValueError("Each peptide-library candidate record requires a non-empty string id.")

    sequence_value = record.get("sequence")
    sequence = sequence_value if isinstance(sequence_value, str) else None
    limitations_as_modifications = [
        _modification_label(item) for item in _source_modifications(record)
    ]
    nonstandard = _as_labels(record.get("nonstandardResidues"))
    if nonstandard:
        limitations_as_modifications.append(
            "source-declared nonstandard residue(s): " + "; ".join(nonstandard)
        )
    if record.get("selectableForOptimization") is False:
        limitations_as_modifications.append("library marks this candidate not selectable for optimization")

    return CandidateRecord(
        identifier=identifier_value,
        sequence=sequence,
        modifications=tuple(limitations_as_modifications),
        provenance=_provenance(record),
    )


def _provenance(record: Mapping[str, Any]) -> dict[str, Any]:
    """Keep library provenance visible without claiming source data are descriptors."""

    return {
        "library_record_id": record.get("id"),
        "library_name": record.get("name"),
        "source_count": record.get("sourceCount"),
        "primary_source": record.get("primarySource"),
    }


def _as_labels(value: Any) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in _as_items(value) if str(item).strip())


def _as_items(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, Mapping)):
        return (value,)
    if isinstance(value, list) or isinstance(value, tuple):
        return tuple(value)
    return (value,)


def _modification_label(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "modification", "description", "type"):
            label = value.get(key)
            if isinstance(label, str) and label.strip():
                return label.strip()
        return "source-declared modification with unspecified chemistry"
    label = str(value).strip()
    return label or "source-declared modification with unspecified chemistry"

