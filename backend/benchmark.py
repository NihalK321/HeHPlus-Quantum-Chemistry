"""Exact classical reference and uniform-random baseline for the same table."""

import numpy as np

from .schema import BenchmarkResult, Configuration


def compare_results(configurations: list[Configuration], probabilities, sampled_best: Configuration) -> BenchmarkResult:
    energies = np.array([item.energy_kcal_mol for item in configurations])
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.shape != energies.shape or not np.all(np.isfinite(probabilities)):
        raise ValueError("One finite probability is required per configuration.")
    if np.any(probabilities < 0) or not np.isclose(probabilities.sum(), 1):
        raise ValueError("Probabilities must be nonnegative and sum to one.")
    minimum = float(energies.min())
    optimal = np.isclose(energies, minimum, rtol=0, atol=1e-7)
    return BenchmarkResult(
        minimum_energy_kcal_mol=minimum,
        optimal_bitstrings=[item.bitstring for item, is_optimal in zip(configurations, optimal) if is_optimal],
        uniform_expected_energy_kcal_mol=float(energies.mean()),
        uniform_optimum_probability=float(optimal.mean()),
        solver_expected_energy_kcal_mol=float(probabilities @ energies),
        solver_optimum_probability=float(probabilities[optimal].sum()),
        sampled_best_gap_kcal_mol=max(0.0, sampled_best.energy_kcal_mol - minimum),
    )
