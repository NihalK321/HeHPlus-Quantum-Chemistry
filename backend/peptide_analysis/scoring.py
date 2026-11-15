"""Researcher-configured scoring terms for downstream, separately owned QUBO work."""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

from .models import (
    CandidateSetAnalysis,
    GoalContribution,
    PairwiseAnalysis,
    QuboScoringContract,
    ResearchGoal,
    ResearchScore,
    SequenceAnalysis,
)


def score_sequence(
    analysis: SequenceAnalysis,
    goals: Iterable[ResearchGoal],
) -> ResearchScore:
    """Score one calculated sequence only against explicit researcher-supplied goals.

    No default goal, weight, normalization interval, compatibility score, or
    bioactivity interpretation is supplied by this package.
    """

    if not analysis.is_calculated:
        raise ValueError("Only fully calculated sequence analyses can be scored.")
    values = {
        "molecular_mass_da": analysis.molecular_mass_da,
        "net_charge": analysis.estimated_net_charge,
        "isoelectric_point": analysis.estimated_isoelectric_point,
        "average_hydropathy": analysis.average_kyte_doolittle_hydropathy,
        "basic_residue_fraction": analysis.basic_residue_fraction,
        "acidic_residue_fraction": analysis.acidic_residue_fraction,
        "sequence_length": analysis.sequence_length,
    }
    return _score(
        entity_identifier=analysis.identifier or "<unidentified-sequence>",
        values=values,
        goals=goals,
    )


def score_pair(
    analysis: PairwiseAnalysis,
    goals: Iterable[ResearchGoal],
) -> ResearchScore:
    """Score pairwise proxy terms only against explicit researcher-supplied goals."""

    if not analysis.is_calculated:
        raise ValueError("Only fully calculated pairwise analyses can be scored.")
    values = {
        "normalized_edit_similarity": analysis.normalized_edit_similarity,
        "normalized_edit_diversity": analysis.normalized_edit_diversity,
        "absolute_hydropathy_difference": analysis.absolute_hydropathy_difference,
        "absolute_net_charge_difference": analysis.absolute_net_charge_difference,
        "edit_distance": analysis.edit_distance,
    }
    return _score(
        entity_identifier=_pair_identifier(analysis),
        values=values,
        goals=goals,
        limitations=(
            "Pair scores combine explicit research proxies; they do not establish "
            "peptide compatibility, interaction, synergy, or safety.",
        ),
    )


def build_qubo_scoring_contract(
    candidate_set: CandidateSetAnalysis,
    *,
    individual_goals: Iterable[ResearchGoal],
    pairwise_goals: Iterable[ResearchGoal] = (),
) -> QuboScoringContract:
    """Prepare transparent score tables for an agreed downstream QUBO contract.

    This function deliberately stops before construction of coefficients. The
    optimization owner and chemistry researcher must agree whether a normalized
    research score becomes a reward, a penalty, or another mathematical term.
    """

    individual_goals_tuple = tuple(individual_goals)
    pairwise_goals_tuple = tuple(pairwise_goals)
    if not individual_goals_tuple:
        raise ValueError("At least one explicit individual ResearchGoal is required.")

    individual_scores: dict[str, ResearchScore] = {}
    for candidate in candidate_set.candidates:
        if candidate.identifier is None:
            raise ValueError("A downstream scoring contract requires candidate identifiers.")
        individual_scores[candidate.identifier] = score_sequence(candidate, individual_goals_tuple)

    pairwise_scores: dict[str, ResearchScore] = {}
    if pairwise_goals_tuple:
        for pair in candidate_set.pairwise_terms:
            pairwise_scores[_pair_identifier(pair)] = score_pair(pair, pairwise_goals_tuple)

    return QuboScoringContract(
        target_ph=candidate_set.target_ph,
        individual_scores=individual_scores,
        pairwise_scores=pairwise_scores,
        individual_goals=individual_goals_tuple,
        pairwise_goals=pairwise_goals_tuple,
        limitations=(
            "This is a scoring exchange contract, not QUBO, Ising, QAOA, or an "
            "experimental compatibility result. Its terms require documented researcher rationale.",
        ),
    )


def _score(
    *,
    entity_identifier: str,
    values: dict[str, float | int | None],
    goals: Iterable[ResearchGoal],
    limitations: tuple[str, ...] = (),
) -> ResearchScore:
    goals_tuple = tuple(goals)
    if not goals_tuple:
        raise ValueError("At least one explicit ResearchGoal is required.")

    contributions: list[GoalContribution] = []
    total_weight = 0.0
    weighted_total = 0.0
    for goal in goals_tuple:
        if goal.metric not in values:
            available = ", ".join(sorted(values))
            raise ValueError(f"Metric {goal.metric!r} is unavailable. Available metrics: {available}.")
        raw_value = values[goal.metric]
        if raw_value is None or not isfinite(float(raw_value)):
            raise ValueError(f"Metric {goal.metric!r} has no finite calculated value.")
        normalized_value = _normalise(float(raw_value), goal)
        weighted_value = normalized_value * goal.weight
        contributions.append(
            GoalContribution(
                metric=goal.metric,
                raw_value=float(raw_value),
                normalized_value=normalized_value,
                weight=goal.weight,
                weighted_value=weighted_value,
                rationale=goal.rationale,
            )
        )
        total_weight += goal.weight
        weighted_total += weighted_value

    return ResearchScore(
        entity_identifier=entity_identifier,
        score=weighted_total / total_weight,
        contributions=tuple(contributions),
        limitations=limitations,
    )


def _normalise(value: float, goal: ResearchGoal) -> float:
    """Normalize solely inside the researcher's declared interval."""

    if goal.direction == "maximize":
        result = (value - goal.lower_bound) / (goal.upper_bound - goal.lower_bound)
    elif goal.direction == "minimize":
        result = (goal.upper_bound - value) / (goal.upper_bound - goal.lower_bound)
    else:
        assert goal.target is not None
        scale = max(abs(goal.target - goal.lower_bound), abs(goal.upper_bound - goal.target))
        result = 1.0 - abs(value - goal.target) / scale
    return max(0.0, min(1.0, result))


def _pair_identifier(analysis: PairwiseAnalysis) -> str:
    left = analysis.left_identifier or "<unidentified-left>"
    right = analysis.right_identifier or "<unidentified-right>"
    return f"{left}|{right}"

