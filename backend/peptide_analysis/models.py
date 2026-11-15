"""Typed input/output models for transparent sequence-derived peptide descriptors.

The models in this package deliberately describe *calculated sequence descriptors*.
They do not represent measured peptide properties, bioactivity, compatibility, or
clinical suitability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Literal, Mapping


AnalysisStatus = Literal["calculated", "unsupported", "unavailable"]
STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


@dataclass(frozen=True, slots=True)
class SequenceAnalysis:
    """Sequence-only peptide descriptors with methods and assumptions attached."""

    identifier: str | None
    sequence: str | None
    status: AnalysisStatus
    target_ph: float
    sequence_length: int | None
    amino_acid_composition: Mapping[str, int] | None
    molecular_mass_da: float | None
    estimated_net_charge: float | None
    estimated_isoelectric_point: float | None
    average_kyte_doolittle_hydropathy: float | None
    basic_residue_composition: Mapping[str, int] | None
    acidic_residue_composition: Mapping[str, int] | None
    basic_residue_fraction: float | None
    acidic_residue_fraction: float | None
    terminal_chemistry_assumption: str
    methods: Mapping[str, str]
    limitations: tuple[str, ...] = ()
    unsupported_residues: tuple[str, ...] = ()
    source_provenance: Mapping[str, Any] | None = None

    @property
    def is_calculated(self) -> bool:
        """Whether all reported descriptor values were calculated."""

        return self.status == "calculated"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation without changing meaning."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class PairwiseAnalysis:
    """Transparent, sequence-derived pair terms; not a compatibility assessment."""

    left_identifier: str | None
    right_identifier: str | None
    status: AnalysisStatus
    target_ph: float
    normalized_edit_similarity: float | None
    normalized_edit_diversity: float | None
    edit_distance: int | None
    absolute_hydropathy_difference: float | None
    absolute_net_charge_difference: float | None
    methods: Mapping[str, str]
    limitations: tuple[str, ...] = ()

    @property
    def is_calculated(self) -> bool:
        return self.status == "calculated"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    """Minimal, read-only candidate input for the initial small blend experiment."""

    identifier: str
    sequence: str | None
    modifications: tuple[str, ...] = ()
    provenance: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CandidateSetAnalysis:
    """Individual descriptors and all pair terms for a small candidate set."""

    target_ph: float
    candidates: tuple[SequenceAnalysis, ...]
    pairwise_terms: tuple[PairwiseAnalysis, ...]
    limitations: tuple[str, ...] = ()

    @property
    def calculated_candidate_count(self) -> int:
        return sum(candidate.is_calculated for candidate in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResearchGoal:
    """An explicitly researcher-defined normalised objective for one descriptor.

    The lower and upper bounds define a declared normalisation interval. They are
    not inferred from a candidate set. This prevents the analysis layer from
    silently creating a research objective or a compatibility score.
    """

    metric: str
    direction: Literal["maximize", "minimize", "target"]
    weight: float
    lower_bound: float
    upper_bound: float
    target: float | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ValueError("ResearchGoal.metric must be non-empty.")
        if self.direction not in {"maximize", "minimize", "target"}:
            raise ValueError("ResearchGoal.direction must be maximize, minimize, or target.")
        if not all(isfinite(float(value)) for value in (self.weight, self.lower_bound, self.upper_bound)):
            raise ValueError("ResearchGoal weights and bounds must be finite.")
        if self.weight <= 0:
            raise ValueError("ResearchGoal.weight must be positive.")
        if self.upper_bound <= self.lower_bound:
            raise ValueError("ResearchGoal.upper_bound must exceed lower_bound.")
        if self.direction == "target" and self.target is None:
            raise ValueError("A target-direction ResearchGoal requires target.")
        if self.target is not None and not isfinite(float(self.target)):
            raise ValueError("ResearchGoal.target must be finite.")
        if self.target is not None and not self.lower_bound <= self.target <= self.upper_bound:
            raise ValueError("ResearchGoal.target must fall inside its normalization bounds.")
        if self.direction != "target" and self.target is not None:
            raise ValueError("Only a target-direction ResearchGoal may include target.")


@dataclass(frozen=True, slots=True)
class GoalContribution:
    """One normalized, weighted component of a researcher-defined score."""

    metric: str
    raw_value: float
    normalized_value: float
    weight: float
    weighted_value: float
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchScore:
    """A transparent score usable by a downstream QUBO builder, not a QUBO itself."""

    entity_identifier: str
    score: float
    contributions: tuple[GoalContribution, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QuboScoringContract:
    """Scores and pair proxies for an agreed downstream peptide-selection objective.

    This package intentionally does not create QUBO, Ising, QAOA, or compatibility
    coefficients. A quantum-optimization owner must explicitly agree how these
    transparent, researcher-provided terms map into a mathematical objective.
    """

    target_ph: float
    individual_scores: Mapping[str, ResearchScore]
    pairwise_scores: Mapping[str, ResearchScore]
    individual_goals: tuple[ResearchGoal, ...] = field(default_factory=tuple)
    pairwise_goals: tuple[ResearchGoal, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = ()

