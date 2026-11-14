"""Sequence normalization and selection-safety validation."""

from __future__ import annotations

from .models import SequenceValidation


STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
_SOURCE_SEQUENCE_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def normalize_sequence(sequence: str) -> str:
    """Normalize whitespace and case without changing residue order."""

    return "".join(sequence.split()).upper()


def validate_sequence(sequence: str) -> SequenceValidation:
    """Validate a source sequence and flag nonstandard residues.

    An alphabetic source sequence may be preserved even if it contains a
    nonstandard residue such as ``U`` or ``X``. It is then excluded from the
    standard-residue optimization candidate set until reviewed.
    """

    normalized = normalize_sequence(sequence)
    if not normalized:
        return SequenceValidation(
            normalized_sequence="",
            is_source_valid=False,
            selectable_for_optimization=False,
            error="Sequence is empty after whitespace normalization.",
        )

    invalid = tuple(sorted({residue for residue in normalized if residue not in _SOURCE_SEQUENCE_ALPHABET}))
    if invalid:
        return SequenceValidation(
            normalized_sequence=normalized,
            is_source_valid=False,
            selectable_for_optimization=False,
            invalid_characters=invalid,
            error="Sequence contains characters outside the supported residue-letter alphabet.",
        )

    nonstandard = tuple(
        {"position": position, "residue": residue}
        for position, residue in enumerate(normalized, start=1)
        if residue not in STANDARD_AMINO_ACIDS
    )
    return SequenceValidation(
        normalized_sequence=normalized,
        is_source_valid=True,
        selectable_for_optimization=not nonstandard,
        nonstandard_residues=nonstandard,
    )
