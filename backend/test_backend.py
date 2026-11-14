"""Run from the repository root: python -m pytest backend/test_backend.py -q"""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from rdkit import Chem
from rdkit.Chem import rdMolTransforms

from .api import app
from .benchmark import compare_results
from .chemistry import build_problem
from .optimizer import optimize
from .quantum import build_qaoa_circuit, cost_hamiltonian, qaoa_probabilities
from .schema import Configuration, OptimizationRequest


@pytest.fixture(scope="module")
def problem():
    return build_problem(OptimizationRequest())


def test_sequence_normalization():
    assert OptimizationRequest(sequence=" ga ").sequence == "GA"


@pytest.mark.parametrize("changes", [
    {"sequence": ""}, {"sequence": "A"}, {"sequence": "AAAAAAAAA"},
    {"sequence": "AX"}, {"sequence": "Aib"},
    {"torsion_count": 6}, {"torsion_count": 1.5},
    {"angle_options": [180, -180]}, {"angle_options": [0, 0]},
    {"angle_options": [float("nan"), 30]}, {"angle_options": [0, 181]},
    {"method": "hardware"}, {"shots": 0}, {"unexpected": True},
])
def test_invalid_requests(changes):
    with pytest.raises(ValidationError):
        OptimizationRequest(**changes)


def test_geometry_bit_order_and_angles(problem):
    assert len(problem.configurations) == 8
    assert [c.bitstring for c in problem.configurations] == [format(i, "03b") for i in range(8)]
    for configuration in problem.configurations:
        assert np.isfinite(configuration.energy_kcal_mol)
        molecule = Chem.MolFromMolBlock(problem.structures[configuration.bitstring], removeHs=False)
        for i, torsion in enumerate(problem.torsions):
            expected = (-60, 120)[int(configuration.bitstring[::-1][i])]
            actual = rdMolTransforms.GetDihedralDeg(molecule.GetConformer(), *torsion.atom_indices)
            assert abs((actual - expected + 180) % 360 - 180) < 0.1


def test_seed_reproduces_energy_table(problem):
    repeated = build_problem(OptimizationRequest())
    assert np.allclose(
        [c.energy_kcal_mol for c in problem.configurations],
        [c.energy_kcal_mol for c in repeated.configurations],
        rtol=0, atol=1e-7,
    )


def test_too_many_torsions_for_short_peptide():
    with pytest.raises(ValueError, match="only 2"):
        build_problem(OptimizationRequest(sequence="GA", torsion_count=3))


def test_proline_ring_bonds_are_not_rotated():
    problem = build_problem(OptimizationRequest(sequence="GPA", torsion_count=2))
    assert "phi_2" not in [torsion.name for torsion in problem.torsions]


def test_hamiltonian_encodes_asymmetric_energy_table():
    # An asymmetric table catches reversed qubit ordering; the final value
    # also requires a higher-order term, so a quadratic-only model would fail.
    energies = [1, 4, -2, 3, 0, 9, 6, -7]
    hamiltonian = cost_hamiltonian(energies).to_matrix()
    assert np.allclose(hamiltonian, np.diag(energies))


def test_cost_layer_phase_and_mixer():
    from qiskit.quantum_info import Statevector

    energies = np.array([2, 5, -1, 7])
    gamma = 0.7
    state = Statevector.from_instruction(build_qaoa_circuit(energies, [gamma, 0])).data
    normalized = (energies - energies.min()) / np.ptp(energies)
    assert np.allclose(state, np.exp(-1j * gamma * normalized) / 2)
    assert np.allclose(qaoa_probabilities(energies, [0, 0.9]), [0.25] * 4)


def test_tied_optima_benchmark():
    configurations = [
        Configuration(bitstring=format(i, "02b"), angles_degrees=[], energy_kcal_mol=energy)
        for i, energy in enumerate([1, -2, -2, 5])
    ]
    result = compare_results(configurations, [0.1, 0.2, 0.3, 0.4], configurations[0])
    assert result.optimal_bitstrings == ["01", "10"]
    assert result.solver_optimum_probability == pytest.approx(0.5)
    assert result.uniform_optimum_probability == 0.5
    assert result.sampled_best_gap_kcal_mol == 3


def test_classical_solver():
    result = optimize(OptimizationRequest())
    assert result.best_configuration.energy_kcal_mol == result.benchmark.minimum_energy_kcal_mol
    assert result.benchmark.solver_optimum_probability == 1
    assert result.benchmark.sampled_best_gap_kcal_mol == 0
    assert result.counts == {}


def test_qaoa_sampling_and_reproducibility():
    request = OptimizationRequest(sequence="GA", torsion_count=2, method="qaoa", max_iterations=20, shots=128)
    first = optimize(request)
    second = optimize(request)
    assert first.execution_backend == "qiskit_statevector"
    assert sum(first.counts.values()) == 128
    assert sum(first.probabilities.values()) == pytest.approx(1)
    assert first.counts == second.counts
    assert first.probabilities == pytest.approx(second.probabilities)
    assert first.best_configuration.bitstring in first.counts
    observed_energies = [c.energy_kcal_mol for c in first.configurations if c.bitstring in first.counts]
    assert first.best_configuration.energy_kcal_mol == min(observed_energies)
    assert first.optimizer_evaluations > 0


def test_http_contract():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/options").json()["maximum_torsions"] == 5
        response = client.post("/optimize", json={"sequence": "GA", "torsion_count": 2})
        assert response.status_code == 200
        assert len(response.json()["configurations"]) == 4
        assert "V2000" in response.json()["best_structure_molblock"]
        assert client.post("/optimize", json={"sequence": "AX"}).status_code == 422
        assert client.post("/optimize", json={"sequence": "GA", "torsion_count": 3}).status_code == 422
        preflight = client.options("/optimize", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        })
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_pdb_export_preserves_residues_and_selected_geometry(problem):
    for configuration in problem.configurations:
        pdb = problem.pdb_structures[configuration.bitstring]
        molecule = Chem.MolFromPDBBlock(pdb, removeHs=False)
        original = Chem.MolFromMolBlock(problem.structures[configuration.bitstring], removeHs=False)
        assert molecule is not None
        assert molecule.GetNumAtoms() == original.GetNumAtoms()
        assert np.allclose(molecule.GetConformer().GetPositions(),
                           original.GetConformer().GetPositions(), atol=0.001)
        residues = {atom.GetPDBResidueInfo().GetResidueNumber(): atom.GetPDBResidueInfo().GetResidueName()
                    for atom in molecule.GetAtoms() if atom.GetPDBResidueInfo().GetName().strip() == "CA"}
        assert residues == {1: "GLY", 2: "ALA", 3: "GLY", 4: "ALA"}


def test_pdb_download_endpoints():
    with TestClient(app) as client:
        response = client.get("/structure.pdb", params={"sequence": "GA", "torsion_count": 2})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("chemical/x-pdb")
        assert response.headers["content-disposition"].startswith('attachment; filename="peptide_GA_classical_')
        assert response.headers["content-disposition"].endswith('.pdb"')
        assert Chem.MolFromPDBBlock(response.text) is not None
        assert client.get("/structure.pdb", params={"sequence": "AX"}).status_code == 422
        assert client.get("/structure.pdb", params={"sequence": "GA", "torsion_count": 3}).status_code == 422
        request = {"sequence": "GA", "torsion_count": 2, "method": "qaoa", "max_iterations": 20}
        downloaded = client.post("/optimize/pdb", json=request)
        result = client.post("/optimize", json=request).json()
        assert downloaded.status_code == 200
        assert downloaded.text == result["best_structure_pdb"]
        assert "_qaoa_" in downloaded.headers["content-disposition"]
