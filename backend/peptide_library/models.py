"""Typed records exchanged between peptide source connectors and SQLite storage.

The connector layer supplies source-specific provenance. Storage deliberately
does not calculate chemistry properties or alter source sequences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SequenceValidation:
    """Validation state for a stored source sequence."""

    normalized_sequence: str
    is_source_valid: bool
    selectable_for_optimization: bool
    invalid_characters: tuple[str, ...] = ()
    nonstandard_residues: tuple[JsonObject, ...] = ()
    error: str | None = None


@dataclass(slots=True)
class SourcePeptideRecord:
    """One provenance-bearing peptide occurrence supplied by a source API.

    ``source_record_key`` identifies a source occurrence, such as a UniProt
    feature ID, so multiple source references can point to one sequence.
    """

    sequence: str
    source_database: str
    source_accession: str
    source_url: str
    source_record_key: str
    name: str | None = None
    parent_protein_accession: str | None = None
    peptide_feature_coordinates: JsonObject | None = None
    organism: str | None = None
    description: str | None = None
    annotations: list[JsonObject] = field(default_factory=list)
    modifications: list[JsonObject] = field(default_factory=list)
    structure_references: list[JsonObject] = field(default_factory=list)
    available_experimental_properties: JsonObject | None = None
    evidence_type: str | None = None
    source_version: str | None = None
    retrieval_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class UpsertResult:
    """Outcome of inserting or refreshing one source record."""

    peptide_id: str
    peptide_created: bool
    source_reference_created: bool
    selectable_for_optimization: bool
