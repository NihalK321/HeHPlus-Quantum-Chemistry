"""Focused validation of the independent challenge backend."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


pytest.importorskip("qiskit")
pytest.importorskip("qiskit_algorithms")
pytest.importorskip("qiskit_nature")
pytest.importorskip("pyscf")

# Make this file runnable from the repository root without resolving the
# unrelated top-level ``backend`` package first.
PACKAGE_DIRECTORY = Path(__file__).resolve().parent
if str(PACKAGE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIRECTORY))

from heh_plus import (  # noqa: E402
    DEFAULT_OUTPUT_DIRECTORY,
    HeHPlusConfig,
    build_heh_plus_system,
    run_heh_plus_vqe,
    run_potential_energy_scan,
    save_result,
    save_scan,
)


def test_configuration_rejects_out_of_scope_settings() -> None:
    with pytest.raises(ValueError, match="positive finite"):
        HeHPlusConfig(bond_distance_angstrom=0.0)
    with pytest.raises(ValueError, match="STO-3G"):
        HeHPlusConfig(basis="6-31g")
    with pytest.raises(ValueError, match="charge"):
        HeHPlusConfig(charge=0)
    with pytest.raises(ValueError, match="spin-0"):
        HeHPlusConfig(spin=1)


def test_system_has_expected_two_electron_jordan_wigner_shape() -> None:
    system = build_heh_plus_system(HeHPlusConfig(bond_distance_angstrom=1.0))

    assert system.num_particles == (1, 1)
    assert system.num_spatial_orbitals == 2
    assert system.qubit_hamiltonian.num_qubits == 4
    assert system.ansatz.num_qubits == 4
    assert system.ansatz.num_parameters > 0
    assert system.nuclear_repulsion_hartree == pytest.approx(1.05835442184, abs=1e-10)


def test_real_vqe_matches_exact_reference_and_exports() -> None:
    result = run_heh_plus_vqe(HeHPlusConfig(bond_distance_angstrom=1.0, maxiter=200))

    assert result.calculation_status == "completed"
    assert result.molecule == "HeH+"
    assert result.electron_count == 2
    assert result.num_particles == (1, 1)
    assert result.qubit_count == 4
    assert result.parameter_count > 0
    assert result.optimizer_evaluations >= 1
    assert result.convergence_history
    assert result.circuit_text.strip()
    assert result.total_molecular_energy_hartree == pytest.approx(
        result.electronic_energy_hartree + result.nuclear_repulsion_hartree,
        abs=1e-12,
    )
    assert result.classical_total_molecular_energy_hartree == pytest.approx(
        result.classical_electronic_energy_hartree + result.nuclear_repulsion_hartree,
        abs=1e-12,
    )
    assert result.absolute_electronic_error_hartree < 1e-5
    assert result.absolute_total_energy_error_hartree < 1e-5

    # Kept package-local and ignored so the test remains runnable on Windows
    # environments where pytest's restrictive temporary-directory ACLs fail.
    export_directory = DEFAULT_OUTPUT_DIRECTORY / "test-artifacts"
    json_path, circuit_path = save_result(result, export_directory)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["energy_convention"] == result.energy_convention
    assert payload["package_versions"]["qiskit-nature"] != "not installed"
    assert circuit_path.read_text(encoding="utf-8").strip() == result.circuit_text.strip()


def test_small_scan_exports_manifest() -> None:
    scan = run_potential_energy_scan([0.9, 1.0], maxiter=200)

    assert [point.config.bond_distance_angstrom for point in scan.results] == [0.9, 1.0]
    assert all(point.calculation_status == "completed" for point in scan.results)
    assert all(point.absolute_total_energy_error_hartree < 1e-5 for point in scan.results)

    manifest = save_scan(scan, DEFAULT_OUTPUT_DIRECTORY / "test-artifacts")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["result_source"] == "calculated"
    assert len(payload["results"]) == 2
