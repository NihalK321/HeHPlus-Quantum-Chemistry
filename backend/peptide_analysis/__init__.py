"""Isolated, sequence-derived peptide chemistry analysis for PepperQ.

These utilities calculate documented descriptors from standard, unmodified primary
sequences. They deliberately do not claim measured chemistry, bioactivity,
compatibility, therapeutic activity, or experimental validation.
"""

from .descriptors import analyze_candidate_set, analyze_sequence, compare_sequences
from .library_adapter import analyze_library_peptide, analyze_library_record, analyze_library_records
from .models import (
    CandidateRecord,
    CandidateSetAnalysis,
    GoalContribution,
    PairwiseAnalysis,
    QuboScoringContract,
    ResearchGoal,
    ResearchScore,
    SequenceAnalysis,
)
from .scoring import build_qubo_scoring_contract, score_pair, score_sequence

__all__ = [
    "CandidateRecord",
    "CandidateSetAnalysis",
    "GoalContribution",
    "PairwiseAnalysis",
    "QuboScoringContract",
    "ResearchGoal",
    "ResearchScore",
    "SequenceAnalysis",
    "analyze_candidate_set",
    "analyze_library_peptide",
    "analyze_library_record",
    "analyze_library_records",
    "analyze_sequence",
    "build_qubo_scoring_contract",
    "compare_sequences",
    "score_pair",
    "score_sequence",
]

