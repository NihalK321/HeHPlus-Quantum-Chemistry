"""Isolated, reproducible quantum-chemistry experiments for PepperQ.

This package currently contains a local-statevector VQE study for HeH+.  It is
intentionally separate from the peptide QAOA implementation: VQE estimates an
electronic-structure energy, while QAOA selects peptide candidates.
"""

from .heh_plus import (
    HeHPlusConfig,
    HeHPlusResult,
    HeHPlusSystem,
    PotentialEnergyScan,
    build_heh_plus_system,
    run_heh_plus_vqe,
    run_potential_energy_scan,
    save_result,
    save_scan,
)

__all__ = [
    "HeHPlusConfig",
    "HeHPlusResult",
    "HeHPlusSystem",
    "PotentialEnergyScan",
    "build_heh_plus_system",
    "run_heh_plus_vqe",
    "run_potential_energy_scan",
    "save_result",
    "save_scan",
]
