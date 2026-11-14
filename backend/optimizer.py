"""Coordinate chemistry, classical reference, and an optional QAOA search."""

from time import perf_counter

import numpy as np
from scipy.optimize import minimize

from .benchmark import compare_results
from .chemistry import build_problem
from .schema import OptimizationRequest, OptimizationResult


LIMITATIONS = [
    "MMFF94 is classical molecular mechanics, not a quantum electronic-structure calculation.",
    "Only a small discrete torsion grid is searched; this is not a full folding prediction.",
    "Unselected coordinates are fixed at a seeded embedded geometry; no solvent or relaxation is modeled.",
    "Free termini and default protonation are used; no disulfide bonds or other modifications are added.",
    "Absolute energies should not be compared across different peptide sequences.",
    "The energy table is enumerated classically before QAOA; no speedup or biological activity is claimed.",
    "QAOA uses ideal statevector simulation; sampled counts are simulated measurements, not hardware results.",
]


def optimize(request: OptimizationRequest) -> OptimizationResult:
    started = perf_counter()
    problem = build_problem(request)
    chemistry_seconds = perf_counter() - started
    started = perf_counter()
    energies = np.array([item.energy_kcal_mol for item in problem.configurations])
    rng = np.random.default_rng(request.seed)

    if request.method == "classical":
        optimal = np.isclose(energies, energies.min(), rtol=0, atol=1e-7)
        probabilities = optimal.astype(float) / optimal.sum()
        best_index = int(np.argmin(energies))
        counts = {}
        evaluations = len(energies)
        converged = True
        message = "All configurations evaluated; minimum is exact within this grid."
        execution_backend = "exhaustive_search"
    else:
        from .quantum import print_qaoa_circuit, qaoa_probabilities

        spread = float(np.ptp(energies))
        scaled = (energies - energies.min()) / spread if spread > 0 else np.zeros_like(energies)

        def objective(parameters):
            return float(qaoa_probabilities(energies, parameters) @ scaled)

        initial = rng.uniform(0.1, np.pi, size=2 * request.layers)
        fitted = minimize(objective, initial, method="COBYLA", options={"maxiter": request.max_iterations})
        print_qaoa_circuit(energies, fitted.x, problem.sequence, [torsion.name for torsion in problem.torsions])
        probabilities = qaoa_probabilities(energies, fitted.x)
        probabilities = np.maximum(probabilities, 0)
        probabilities /= probabilities.sum()
        samples = rng.multinomial(request.shots, probabilities)
        observed = np.flatnonzero(samples)
        best_index = int(observed[np.argmin(energies[observed])])
        counts = {item.bitstring: int(count) for item, count in zip(problem.configurations, samples) if count}
        evaluations = int(fitted.nfev)
        converged = bool(fitted.success)
        message = str(fitted.message)
        execution_backend = "qiskit_statevector"

    best = problem.configurations[best_index]
    return OptimizationResult(
        sequence=problem.sequence,
        method=request.method,
        execution_backend=execution_backend,
        seed=request.seed,
        torsions=problem.torsions,
        angle_options=request.angle_options,
        configurations=problem.configurations,
        best_configuration=best,
        best_structure_molblock=problem.structures[best.bitstring],
        best_structure_pdb=problem.pdb_structures[best.bitstring],
        probabilities={item.bitstring: float(probability) for item, probability in zip(problem.configurations, probabilities)},
        counts=counts,
        benchmark=compare_results(problem.configurations, probabilities, best),
        optimizer_evaluations=evaluations,
        optimizer_converged=converged,
        optimizer_message=message,
        chemistry_seconds=chemistry_seconds,
        optimizer_seconds=perf_counter() - started,
        limitations=LIMITATIONS,
    )
