"""Reproducible local-statevector VQE calculations for HeH+.

The calculation implemented here is deliberately narrow and explicit:

* molecule: HeH+ (two electrons, charge +1, spin 0),
* electronic-structure driver: PySCF through Qiskit Nature,
* model chemistry: restricted Hartree--Fock integrals in STO-3G,
* mapping: Jordan--Wigner without qubit reduction,
* ansatz: UCCSD built on a Hartree--Fock reference,
* variational solver: Qiskit StatevectorEstimator with SLSQP, and
* classical comparison: exact diagonalization filtered to the molecular
  particle-number sector in the same Hamiltonian and basis.

The result records electronic and total molecular energies separately.  The
qubit Hamiltonian contains the electronic energy; nuclear repulsion is added
exactly once to form the total molecular energy.  These are calculated values
for the stated model, not experimental measurements or chemical predictions
outside that model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import platform
from typing import Any, Callable, Mapping, Sequence

import numpy as np


DEFAULT_OUTPUT_DIRECTORY = Path(__file__).resolve().parent / ".local"
HARTREE_UNIT = "Hartree"


@dataclass(frozen=True)
class HeHPlusConfig:
    """Configuration for one fixed-geometry HeH+ VQE calculation.

    ``spin`` uses PySCF's convention (``N_alpha - N_beta``), so a spin value
    of zero represents the closed-shell two-electron singlet target here.
    """

    bond_distance_angstrom: float = 1.0
    basis: str = "sto3g"
    charge: int = 1
    spin: int = 0
    maxiter: int = 200
    ftol: float = 1e-10

    def __post_init__(self) -> None:
        if not np.isfinite(self.bond_distance_angstrom) or self.bond_distance_angstrom <= 0:
            raise ValueError("bond_distance_angstrom must be a positive finite value")
        if self.basis.strip().lower() != "sto3g":
            raise ValueError("this reproducible first experiment is fixed to the STO-3G basis")
        if self.charge != 1:
            raise ValueError("this experiment is defined for HeH+ with charge +1")
        if self.spin != 0:
            raise ValueError("this experiment is defined for the spin-0, two-electron state")
        if self.maxiter <= 0:
            raise ValueError("maxiter must be positive")
        if not np.isfinite(self.ftol) or self.ftol <= 0:
            raise ValueError("ftol must be a positive finite value")

    @property
    def atom_specification(self) -> str:
        """Return the explicitly Angstrom-valued PySCF geometry string."""

        return f"He 0 0 0; H 0 0 {self.bond_distance_angstrom:.12g}"


@dataclass(frozen=True)
class ConvergencePoint:
    """One VQE objective-function evaluation recorded by the callback."""

    evaluation: int
    electronic_energy_hartree: float
    parameters: tuple[float, ...]


@dataclass
class HeHPlusSystem:
    """The Qiskit Nature objects prepared for a single HeH+ geometry."""

    config: HeHPlusConfig
    problem: Any
    mapper: Any
    qubit_hamiltonian: Any
    ansatz: Any
    nuclear_repulsion_hartree: float
    num_particles: tuple[int, int]
    num_spatial_orbitals: int


@dataclass(frozen=True)
class HeHPlusResult:
    """Provenance-rich output from one actual local HeH+ VQE calculation."""

    config: HeHPlusConfig
    calculation_status: str
    calculated_with: str
    classical_reference_method: str
    energy_convention: str
    molecule: str
    electron_count: int
    num_particles: tuple[int, int]
    electronic_energy_hartree: float
    nuclear_repulsion_hartree: float
    total_molecular_energy_hartree: float
    classical_electronic_energy_hartree: float
    classical_total_molecular_energy_hartree: float
    absolute_electronic_error_hartree: float
    absolute_total_energy_error_hartree: float
    qubit_count: int
    parameter_count: int
    circuit_depth: int
    decomposed_circuit_depth: int
    ansatz: str
    mapping: str
    optimizer: str
    estimator: str
    optimizer_evaluations: int
    convergence_history: tuple[ConvergencePoint, ...]
    optimal_parameters: tuple[float, ...]
    circuit_text: str
    package_versions: Mapping[str, str]
    created_at_utc: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation suitable for recorded outputs."""

        return asdict(self)


@dataclass(frozen=True)
class PotentialEnergyScan:
    """Calculated HeH+ results at consistently configured bond distances."""

    results: tuple[HeHPlusResult, ...]
    created_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "molecule": "HeH+",
            "result_source": "calculated",
            "energy_convention": (
                "Electronic qubit-Hamiltonian energy plus the PySCF nuclear "
                "repulsion energy equals total molecular energy (Hartree)."
            ),
            "created_at_utc": self.created_at_utc,
            "results": [result.to_dict() for result in self.results],
        }


def _dependencies() -> dict[str, Any]:
    """Import the optional scientific stack only when a calculation is run."""

    try:
        from qiskit.primitives import StatevectorEstimator
        from qiskit_algorithms import NumPyMinimumEigensolver, VQE
        from qiskit_algorithms.optimizers import SLSQP
        from qiskit_nature.second_q.algorithms import GroundStateEigensolver
        from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD
        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.units import DistanceUnit
    except ImportError as exc:  # pragma: no cover - exercised in lean installs
        raise RuntimeError(
            "The HeH+ experiment requires qiskit-nature, qiskit-algorithms, "
            "and pyscf. Install backend/quantum_chemistry/requirements.txt."
        ) from exc

    return {
        "DistanceUnit": DistanceUnit,
        "GroundStateEigensolver": GroundStateEigensolver,
        "HartreeFock": HartreeFock,
        "JordanWignerMapper": JordanWignerMapper,
        "NumPyMinimumEigensolver": NumPyMinimumEigensolver,
        "PySCFDriver": PySCFDriver,
        "SLSQP": SLSQP,
        "StatevectorEstimator": StatevectorEstimator,
        "UCCSD": UCCSD,
        "VQE": VQE,
    }


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:  # pragma: no cover - defensive only
        return "not installed"


def package_versions() -> dict[str, str]:
    """Capture the packages and runtime that materially affect a result."""

    return {
        "python": platform.python_version(),
        "qiskit": _version("qiskit"),
        "qiskit-algorithms": _version("qiskit-algorithms"),
        "qiskit-nature": _version("qiskit-nature"),
        "pyscf": _version("pyscf"),
        "numpy": _version("numpy"),
        "scipy": _version("scipy"),
    }


def build_heh_plus_system(config: HeHPlusConfig | None = None) -> HeHPlusSystem:
    """Build the requested physical-sector Hamiltonian and UCCSD ansatz.

    The atomic coordinates passed to :class:`PySCFDriver` are explicitly in
    Angstrom.  The returned Hamiltonian represents the electronic energy only;
    its nuclear-repulsion term is retained separately for unambiguous totals.
    """

    config = config or HeHPlusConfig()
    deps = _dependencies()
    driver = deps["PySCFDriver"](
        atom=config.atom_specification,
        unit=deps["DistanceUnit"].ANGSTROM,
        charge=config.charge,
        spin=config.spin,
        basis=config.basis,
    )
    problem = driver.run()
    num_particles = tuple(int(value) for value in problem.num_particles)
    if num_particles != (1, 1):
        raise RuntimeError(
            "Unexpected HeH+ particle sector from PySCFDriver; expected (1, 1), "
            f"received {num_particles}."
        )

    mapper = deps["JordanWignerMapper"]()
    qubit_hamiltonian = mapper.map(problem.hamiltonian.second_q_op())
    hartree_fock = deps["HartreeFock"](
        problem.num_spatial_orbitals,
        num_particles,
        mapper,
    )
    ansatz = deps["UCCSD"](
        problem.num_spatial_orbitals,
        num_particles,
        mapper,
        initial_state=hartree_fock,
    )

    return HeHPlusSystem(
        config=config,
        problem=problem,
        mapper=mapper,
        qubit_hamiltonian=qubit_hamiltonian,
        ansatz=ansatz,
        nuclear_repulsion_hartree=float(problem.hamiltonian.nuclear_repulsion_energy),
        num_particles=num_particles,
        num_spatial_orbitals=int(problem.num_spatial_orbitals),
    )


def _circuit_text(circuit: Any) -> str:
    """Use Qiskit's text drawer to retain a portable circuit representation."""

    return str(circuit.draw(output="text", fold=-1))


def _decompose_for_metadata(circuit: Any) -> Any:
    """Expose gate-level depth while retaining the original UCCSD circuit too."""

    decomposed = circuit
    for _ in range(3):
        next_circuit = decomposed.decompose()
        if next_circuit == decomposed:
            break
        decomposed = next_circuit
    return decomposed


def _classical_reference(system: HeHPlusSystem, deps: Mapping[str, Any]) -> tuple[float, float]:
    """Exact-diagonalize in the correct two-electron sector of this model.

    Qiskit Nature's filter criterion enforces the physical particle sector,
    avoiding the unphysical global minimum over all Fock-space occupations.
    """

    exact_solver = deps["NumPyMinimumEigensolver"]()
    exact_solver.filter_criterion = system.problem.get_default_filter_criterion()
    ground_state_solver = deps["GroundStateEigensolver"](system.mapper, exact_solver)
    exact_result = ground_state_solver.solve(system.problem)
    electronic = float(np.real(exact_result.computed_energies[0]))
    total = float(np.real(exact_result.total_energies[0]))
    return electronic, total


def run_heh_plus_vqe(config: HeHPlusConfig | None = None) -> HeHPlusResult:
    """Execute one real statevector VQE and its matched exact reference.

    This function performs no hardware execution and no shot sampling.  A
    UCCSD circuit prepared from the Hartree--Fock reference preserves the
    target particle sector, while the exact comparator additionally applies
    Qiskit Nature's default filter criterion.
    """

    system = build_heh_plus_system(config)
    deps = _dependencies()
    history: list[ConvergencePoint] = []

    def callback(
        evaluation: int,
        parameters: np.ndarray,
        mean: float,
        _metadata: Mapping[str, Any],
    ) -> None:
        history.append(
            ConvergencePoint(
                evaluation=int(evaluation),
                electronic_energy_hartree=float(np.real(mean)),
                parameters=tuple(float(value) for value in parameters),
            )
        )

    initial_point = np.zeros(system.ansatz.num_parameters, dtype=float)
    vqe = deps["VQE"](
        deps["StatevectorEstimator"](),
        system.ansatz,
        deps["SLSQP"](maxiter=system.config.maxiter, ftol=system.config.ftol),
        initial_point=initial_point,
        callback=callback,
    )
    vqe_result = vqe.compute_minimum_eigenvalue(system.qubit_hamiltonian)
    electronic_energy = float(np.real(vqe_result.eigenvalue))
    total_energy = electronic_energy + system.nuclear_repulsion_hartree
    reference_electronic, reference_total = _classical_reference(system, deps)

    optimal_parameters = tuple(float(value) for value in vqe_result.optimal_point)
    optimal_circuit = system.ansatz.assign_parameters(vqe_result.optimal_point, inplace=False)
    decomposed_circuit = _decompose_for_metadata(optimal_circuit)
    optimizer_evaluations = int(
        getattr(vqe_result, "cost_function_evals", 0) or len(history)
    )

    return HeHPlusResult(
        config=system.config,
        calculation_status="completed",
        calculated_with="Qiskit StatevectorEstimator VQE (local exact-state simulator)",
        classical_reference_method=(
            "Qiskit Algorithms NumPyMinimumEigensolver exact diagonalization "
            "with Qiskit Nature's default physical-sector filter"
        ),
        energy_convention=(
            "Electronic energy is the mapped electronic Hamiltonian expectation; "
            "total molecular energy equals electronic energy plus PySCF nuclear "
            "repulsion, all in Hartree."
        ),
        molecule="HeH+",
        electron_count=sum(system.num_particles),
        num_particles=system.num_particles,
        electronic_energy_hartree=electronic_energy,
        nuclear_repulsion_hartree=system.nuclear_repulsion_hartree,
        total_molecular_energy_hartree=total_energy,
        classical_electronic_energy_hartree=reference_electronic,
        classical_total_molecular_energy_hartree=reference_total,
        absolute_electronic_error_hartree=abs(electronic_energy - reference_electronic),
        absolute_total_energy_error_hartree=abs(total_energy - reference_total),
        qubit_count=int(system.qubit_hamiltonian.num_qubits),
        parameter_count=int(system.ansatz.num_parameters),
        circuit_depth=int(optimal_circuit.depth()),
        decomposed_circuit_depth=int(decomposed_circuit.depth()),
        ansatz="UCCSD with HartreeFock initial state",
        mapping="JordanWignerMapper (no qubit reduction)",
        optimizer=f"SLSQP(maxiter={system.config.maxiter}, ftol={system.config.ftol:g})",
        estimator="StatevectorEstimator",
        optimizer_evaluations=optimizer_evaluations,
        convergence_history=tuple(history),
        optimal_parameters=optimal_parameters,
        circuit_text=_circuit_text(optimal_circuit),
        package_versions=package_versions(),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        limitations=(
            "Local statevector simulation is not a hardware result and does not model noise.",
            "STO-3G is a small basis; the result is only comparable within this stated model.",
            "The Born-Oppenheimer electronic calculation uses a fixed He-H distance.",
            "VQE convergence and error are optimizer/model specific, not evidence of quantum advantage.",
        ),
    )


def run_potential_energy_scan(
    distances_angstrom: Sequence[float],
    *,
    basis: str = "sto3g",
    maxiter: int = 200,
    ftol: float = 1e-10,
) -> PotentialEnergyScan:
    """Run the same verified model at several He--H distances.

    Every scan point retains its own circuit, convergence history, package
    versions, and exact reference.  The caller should only plot the returned
    calculated values; this helper creates no illustrative energies.
    """

    if not distances_angstrom:
        raise ValueError("at least one bond distance is required for a scan")
    results = tuple(
        run_heh_plus_vqe(
            HeHPlusConfig(
                bond_distance_angstrom=float(distance),
                basis=basis,
                maxiter=maxiter,
                ftol=ftol,
            )
        )
        for distance in distances_angstrom
    )
    return PotentialEnergyScan(
        results=results,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _result_stem(result: HeHPlusResult) -> str:
    distance = f"{result.config.bond_distance_angstrom:.6f}".replace(".", "p")
    timestamp = result.created_at_utc.replace(":", "").replace("+00:00", "Z")
    return f"heh_plus_r_{distance}_angstrom_{timestamp}"


def save_result(
    result: HeHPlusResult,
    output_directory: Path | str = DEFAULT_OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    """Write actual calculation metadata JSON and Qiskit text circuit output."""

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    stem = _result_stem(result)
    json_path = destination / f"{stem}.json"
    circuit_path = destination / f"{stem}.circuit.txt"
    json_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    circuit_path.write_text(result.circuit_text + "\n", encoding="utf-8")
    return json_path, circuit_path


def save_scan(
    scan: PotentialEnergyScan,
    output_directory: Path | str = DEFAULT_OUTPUT_DIRECTORY,
) -> Path:
    """Write a provenance-rich JSON manifest for a completed energy scan."""

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = scan.created_at_utc.replace(":", "").replace("+00:00", "Z")
    path = destination / f"heh_plus_potential_energy_scan_{timestamp}.json"
    path.write_text(json.dumps(scan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path
