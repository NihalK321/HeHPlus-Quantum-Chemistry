"""Prepare or explicitly submit one optimized HeH+ energy estimate to IBM Quantum.

The normal invocation writes a no-cost preflight record and exits.  A QPU job
is possible only when both ``--submit`` and a deliberate ``--backend`` choice
are supplied.  This is intentionally a single-point energy estimate: VQE
optimization remains local, then the optimized circuit is measured on hardware
and compared with the saved local VQE and exact classical energies.

The script uses the current client-side IBM Runtime Estimator interface.  It
maps the electronic Hamiltonian through the transpiled circuit layout before
submission, then adds nuclear repulsion exactly once after measurement.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


CHALLENGE_ROOT = Path(__file__).resolve().parent
if str(CHALLENGE_ROOT) not in sys.path:
    sys.path.insert(0, str(CHALLENGE_ROOT))

from backend.heh_plus import HeHPlusConfig, build_heh_plus_system  # noqa: E402


DEFAULT_RESULTS = CHALLENGE_ROOT / "artifacts" / "hehplus_potential_energy_scan.json"
DEFAULT_HARDWARE_DIRECTORY = CHALLENGE_ROOT / "artifacts" / "hardware"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_safe(value: Any) -> Any:
    """Convert Runtime metadata to JSON without exposing credentials."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except ValueError:
            pass
    return repr(value)


def _scalar(value: Any) -> float:
    """Extract the one expectation value produced by the one-PUB job."""

    if hasattr(value, "reshape"):
        flattened = value.reshape(-1)
        if len(flattened) != 1:
            raise RuntimeError(f"Expected one estimator value, received {len(flattened)}.")
        return float(flattened[0])
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise RuntimeError(f"Expected one estimator value, received {len(value)}.")
        return _scalar(value[0])
    return float(value)


def _backend_name(backend: Any) -> str:
    name = getattr(backend, "name", None)
    return str(name() if callable(name) else name)


def _job_value(job: Any, method: str) -> Any:
    value = getattr(job, method, None)
    return value() if callable(value) else value


def _load_point(path: Path, distance: float) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        results = document["results"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"Unable to read a canonical HeH+ scan from {path}: {exc}") from exc

    if document.get("molecule") != "HeH+":
        raise SystemExit("The supplied scan is not an HeH+ scan.")
    matches = [
        result
        for result in results
        if math.isclose(
            float(result["config"]["bond_distance_angstrom"]), distance, abs_tol=1e-12
        )
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one point at {distance:g} Å in {path}; found {len(matches)}."
        )
    return matches[0]


def _system_for_point(point: Mapping[str, Any]) -> Any:
    config = point["config"]
    system = build_heh_plus_system(
        HeHPlusConfig(
            bond_distance_angstrom=float(config["bond_distance_angstrom"]),
            basis=str(config["basis"]),
            charge=int(config["charge"]),
            spin=int(config["spin"]),
            maxiter=int(config["maxiter"]),
            ftol=float(config["ftol"]),
        )
    )
    if len(point["optimal_parameters"]) != system.ansatz.num_parameters:
        raise RuntimeError("Saved optimal parameters do not match the rebuilt UCCSD ansatz.")
    if int(point["qubit_count"]) != system.qubit_hamiltonian.num_qubits:
        raise RuntimeError("Saved qubit count does not match the rebuilt mapped Hamiltonian.")
    return system


def _base_record(
    *,
    point: Mapping[str, Any],
    system: Any,
    results_path: Path,
    requested_distance: float,
    backend_name: str | None,
    precision: float,
    shots: int | None,
    resilience_level: int,
) -> dict[str, Any]:
    return {
        "record_type": "pepperq.hehplus_hardware_estimator_record",
        "record_version": 1,
        "created_at_utc": _utc_now(),
        "hardware_execution": False,
        "execution_status": "not_submitted",
        "backend_name": backend_name,
        "job_id": None,
        "molecule": "HeH+",
        "molecular_charge": 1,
        "electron_count": 2,
        "bond_distance_angstrom": requested_distance,
        "basis": point["config"]["basis"],
        "mapping": point["mapping"],
        "ansatz": point["ansatz"],
        "variational_parameter_count": len(point["optimal_parameters"]),
        "logical_qubit_count": int(system.qubit_hamiltonian.num_qubits),
        "energy_convention": (
            "Measured electronic Hamiltonian expectation plus PySCF nuclear repulsion exactly once "
            "equals total molecular energy (Hartree)."
        ),
        "nuclear_repulsion_hartree": point["nuclear_repulsion_hartree"],
        "local_ideal_vqe_total_energy_hartree": point["total_molecular_energy_hartree"],
        "exact_classical_total_energy_hartree": point["classical_total_molecular_energy_hartree"],
        "local_vqe_vs_classical_absolute_error_hartree": point[
            "absolute_total_energy_error_hartree"
        ],
        "source_scan": {
            "path": str(results_path),
            "sha256": _sha256(results_path),
            "point_created_at_utc": point["created_at_utc"],
        },
        "requested_estimator_options": {
            "precision": precision,
            "default_shots": shots,
            "resilience_level": resilience_level,
            "mitigation_note": (
                "Level 0 requests no Runtime error mitigation/suppression. Higher levels must be "
                "interpreted from the returned Runtime metadata and may add measurement or ZNE work."
            ),
        },
        "observable_layout_step": (
            "The script calls system.qubit_hamiltonian.apply_layout(isa_circuit.layout) after ISA "
            "transpilation, so Pauli observables address the physical qubits used by the circuit."
        ),
        "submission_safety": (
            "This record is not a hardware result unless hardware_execution is true and a completed "
            "job result is present. The script submits only with --submit and an explicit --backend."
        ),
    }


def _import_runtime() -> tuple[Any, Any, Any]:
    try:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService
        from qiskit_ibm_runtime.executor_estimator import Estimator
    except ImportError as exc:
        raise SystemExit(
            "IBM Runtime support is optional and not installed. Run `python -m pip install -r "
            "requirements-hardware.txt` from the challenge directory in a supported environment first."
        ) from exc
    return QiskitRuntimeService, Estimator, generate_preset_pass_manager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare or explicitly submit a one-point HeH+ Runtime Estimator measurement."
    )
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS, help="Canonical scan JSON.")
    parser.add_argument("--distance", type=float, default=1.0, help="Saved scan point in Å (default: 1.0).")
    parser.add_argument("--backend", help="Required IBM Quantum backend name when submitting.")
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Actually submit a QPU job. Omit this for the safe no-cost preflight record.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion and write measured energy/error fields (requires --submit).",
    )
    parser.add_argument(
        "--precision",
        type=float,
        default=0.02,
        help="Target estimator precision in Hartree-scale expectation units (default: 0.02).",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=None,
        help="Optional Runtime default_shots setting; precision/twirling precedence is recorded.",
    )
    parser.add_argument(
        "--resilience-level",
        type=int,
        default=0,
        help="Runtime resilience level (default 0: no mitigation/suppression request).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON record destination (defaults under artifacts/hardware/).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.precision <= 0:
        raise SystemExit("--precision must be positive.")
    if args.shots is not None and args.shots <= 0:
        raise SystemExit("--shots must be positive when provided.")
    if args.resilience_level < 0:
        raise SystemExit("--resilience-level cannot be negative.")
    if args.wait and not args.submit:
        raise SystemExit("--wait requires --submit.")
    if args.submit and not args.backend:
        raise SystemExit("--submit requires an explicit --backend; the script will not choose one for you.")

    results_path = args.results.resolve()
    point = _load_point(results_path, args.distance)
    system = _system_for_point(point)
    output_path = args.output
    if output_path is None:
        if args.submit:
            timestamp = _utc_now().replace(":", "").replace("+00:00", "Z")
            output_path = DEFAULT_HARDWARE_DIRECTORY / f"hehplus_hardware_{timestamp}.json"
        else:
            output_path = DEFAULT_HARDWARE_DIRECTORY / "hehplus_hardware_preflight.json"
    output_path = output_path.resolve()

    record = _base_record(
        point=point,
        system=system,
        results_path=results_path,
        requested_distance=args.distance,
        backend_name=args.backend,
        precision=args.precision,
        shots=args.shots,
        resilience_level=args.resilience_level,
    )
    if not args.submit:
        _write_json(output_path, record)
        print(json.dumps({"hardware_execution": False, "record": str(output_path)}, indent=2))
        return 0

    # Persist the planned run before authenticating or submitting, so a failed
    # account setup never looks like a hardware result.
    record["execution_status"] = "preparing_submission"
    _write_json(output_path, record)
    QiskitRuntimeService, Estimator, generate_preset_pass_manager = _import_runtime()
    service = QiskitRuntimeService()
    backend = service.backend(args.backend)
    actual_backend_name = _backend_name(backend)

    bound_circuit = system.ansatz.assign_parameters(point["optimal_parameters"], inplace=False)
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuit = pass_manager.run(bound_circuit)
    isa_observable = system.qubit_hamiltonian.apply_layout(isa_circuit.layout)
    runtime_options: dict[str, Any] = {"resilience_level": args.resilience_level}
    if args.shots is not None:
        runtime_options["default_shots"] = args.shots
    estimator = Estimator(mode=backend, options=runtime_options)
    job = estimator.run([(isa_circuit, isa_observable)], precision=args.precision)

    record.update(
        {
            "hardware_execution": True,
            "execution_status": str(_job_value(job, "status")),
            "backend_name": actual_backend_name,
            "job_id": _job_value(job, "job_id"),
            "submitted_at_utc": _utc_now(),
            "runtime_package_version": metadata.version("qiskit-ibm-runtime"),
            "transpilation": {
                "optimization_level": 3,
                "isa_circuit_depth": int(isa_circuit.depth()),
                "isa_circuit_size": int(isa_circuit.size()),
                "physical_layout": str(isa_circuit.layout),
                "mapped_observable_qubits": int(isa_observable.num_qubits),
            },
        }
    )
    _write_json(output_path, record)

    if not args.wait:
        print(json.dumps({"hardware_execution": True, "job_id": record["job_id"], "record": str(output_path)}, indent=2))
        return 0

    try:
        pub_result = job.result()[0]
        electronic_energy = _scalar(pub_result.data.evs)
        electronic_stddev = _scalar(pub_result.data.stds)
        total_energy = electronic_energy + float(point["nuclear_repulsion_hartree"])
        record.update(
            {
                "execution_status": str(_job_value(job, "status")),
                "completed_at_utc": _utc_now(),
                "measured_electronic_energy_hartree": electronic_energy,
                "measured_electronic_energy_stddev_hartree": electronic_stddev,
                "measured_total_energy_hartree": total_energy,
                "absolute_error_vs_local_ideal_vqe_hartree": abs(
                    total_energy - float(point["total_molecular_energy_hartree"])
                ),
                "absolute_error_vs_exact_classical_hartree": abs(
                    total_energy - float(point["classical_total_molecular_energy_hartree"])
                ),
                "runtime_result_metadata": _json_safe(getattr(pub_result, "metadata", None)),
                "runtime_job_metrics": _json_safe(_job_value(job, "metrics")),
            }
        )
    except Exception as exc:
        record.update(
            {
                "execution_status": "result_retrieval_failed",
                "result_retrieval_error": f"{type(exc).__name__}: {exc}",
                "result_retrieval_attempted_at_utc": _utc_now(),
            }
        )
        _write_json(output_path, record)
        raise

    _write_json(output_path, record)
    print(
        json.dumps(
            {
                "hardware_execution": True,
                "job_id": record["job_id"],
                "measured_total_energy_hartree": record["measured_total_energy_hartree"],
                "absolute_error_vs_exact_classical_hartree": record[
                    "absolute_error_vs_exact_classical_hartree"
                ],
                "record": str(output_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
