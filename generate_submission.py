"""Generate reproducible, presentation-ready artifacts for the HeH+ challenge.

This script deliberately delegates every energy calculation to this challenge's
own ``backend`` package. It does not import the parent PepperQ backend or
contain a second Hamiltonian, ansatz, or reference implementation. The files
it writes are a portable export of a newly executed local Qiskit calculation.

Run from this challenge directory:

    python generate_submission.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence


CHALLENGE_ROOT = Path(__file__).resolve().parent
if str(CHALLENGE_ROOT) not in sys.path:
    sys.path.insert(0, str(CHALLENGE_ROOT))

from backend.heh_plus import (  # noqa: E402
    HeHPlusConfig,
    HeHPlusResult,
    PotentialEnergyScan,
    build_heh_plus_system,
    run_potential_energy_scan,
)


DEFAULT_DISTANCES = (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0)
DEFAULT_OUTPUT_DIRECTORY = CHALLENGE_ROOT / "artifacts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _anchor_result(results: Iterable[HeHPlusResult]) -> HeHPlusResult:
    """Return the 1.0 Å point, which is used for the displayed circuit."""

    candidates = tuple(results)
    return min(candidates, key=lambda item: abs(item.config.bond_distance_angstrom - 1.0))


def _write_csv(results: Sequence[HeHPlusResult], path: Path) -> None:
    fields = (
        "bond_distance_angstrom",
        "vqe_total_energy_hartree",
        "exact_classical_total_energy_hartree",
        "absolute_total_energy_error_hartree",
        "vqe_electronic_energy_hartree",
        "exact_classical_electronic_energy_hartree",
        "nuclear_repulsion_hartree",
        "qubit_count",
        "variational_parameter_count",
        "logical_circuit_depth",
        "decomposed_circuit_depth",
        "optimizer_evaluations",
        "calculation_status",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "bond_distance_angstrom": result.config.bond_distance_angstrom,
                    "vqe_total_energy_hartree": result.total_molecular_energy_hartree,
                    "exact_classical_total_energy_hartree": result.classical_total_molecular_energy_hartree,
                    "absolute_total_energy_error_hartree": result.absolute_total_energy_error_hartree,
                    "vqe_electronic_energy_hartree": result.electronic_energy_hartree,
                    "exact_classical_electronic_energy_hartree": result.classical_electronic_energy_hartree,
                    "nuclear_repulsion_hartree": result.nuclear_repulsion_hartree,
                    "qubit_count": result.qubit_count,
                    "variational_parameter_count": result.parameter_count,
                    "logical_circuit_depth": result.circuit_depth,
                    "decomposed_circuit_depth": result.decomposed_circuit_depth,
                    "optimizer_evaluations": result.optimizer_evaluations,
                    "calculation_status": result.calculation_status,
                }
            )


def _render_curve(results: Sequence[HeHPlusResult], png_path: Path, svg_path: Path) -> None:
    """Render only values returned from the just-completed VQE scan."""

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    distances = [result.config.bond_distance_angstrom for result in results]
    vqe = [result.total_molecular_energy_hartree for result in results]
    reference = [result.classical_total_molecular_energy_hartree for result in results]
    lowest_index = min(range(len(results)), key=lambda index: vqe[index])

    figure, axis = plt.subplots(figsize=(9.2, 5.6), layout="constrained")
    axis.plot(
        distances,
        reference,
        color="#163a5f",
        linewidth=2.4,
        marker="o",
        markersize=4.8,
        label="Exact classical reference",
        zorder=2,
    )
    axis.plot(
        distances,
        vqe,
        color="#d65f00",
        linewidth=1.25,
        linestyle="--",
        marker="s",
        markersize=4.0,
        label="VQE (StatevectorEstimator + SLSQP)",
        zorder=3,
    )
    axis.scatter(
        [distances[lowest_index]],
        [vqe[lowest_index]],
        color="#bf2c22",
        edgecolor="white",
        linewidth=1.0,
        s=85,
        zorder=4,
    )
    axis.annotate(
        f"lowest sampled VQE point\n{distances[lowest_index]:.1f} Å",
        xy=(distances[lowest_index], vqe[lowest_index]),
        xytext=(18, 22),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1},
        fontsize=9,
        color="#243240",
    )
    axis.set_title("HeH+ potential-energy curve in STO-3G", weight="bold")
    axis.set_xlabel("He–H bond distance (Å)")
    axis.set_ylabel("Total molecular energy (Hartree)")
    axis.grid(alpha=0.22)
    axis.legend(loc="best", frameon=True)
    axis.text(
        0.01,
        0.01,
        "Born–Oppenheimer fixed-nuclei calculations; nuclear repulsion included once.",
        transform=axis.transAxes,
        fontsize=8.2,
        color="#475569",
        va="bottom",
    )
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)


def _render_circuit(result: HeHPlusResult, png_path: Path, text_path: Path) -> None:
    """Draw the decomposed optimized 1 Å UCCSD circuit with Qiskit's drawer."""

    config = result.config
    system = build_heh_plus_system(
        HeHPlusConfig(
            bond_distance_angstrom=config.bond_distance_angstrom,
            basis=config.basis,
            charge=config.charge,
            spin=config.spin,
            maxiter=config.maxiter,
            ftol=config.ftol,
        )
    )
    if len(result.optimal_parameters) != system.ansatz.num_parameters:
        raise RuntimeError(
            "The stored VQE parameter count does not match the reconstructed UCCSD ansatz."
        )
    circuit = system.ansatz.assign_parameters(result.optimal_parameters, inplace=False)
    decomposed = circuit
    for _ in range(3):
        next_circuit = decomposed.decompose()
        if next_circuit == decomposed:
            break
        decomposed = next_circuit
    text_path.write_text(str(decomposed.draw(output="text", fold=-1)) + "\n", encoding="utf-8")
    figure = decomposed.draw(output="mpl", fold=25, idle_wires=False, plot_barriers=False)
    figure.savefig(png_path, dpi=180, bbox_inches="tight")


def _manifest(scan: PotentialEnergyScan, output_directory: Path, generated_files: Sequence[Path]) -> dict[str, Any]:
    anchor = _anchor_result(scan.results)
    lowest = min(scan.results, key=lambda result: result.total_molecular_energy_hartree)
    return {
        "artifact_type": "pepperq.ibm_hehplus_challenge_submission",
        "artifact_version": 1,
        "generated_at_utc": scan.created_at_utc,
        "result_source": "newly calculated local ideal-state Qiskit VQE scan",
        "molecule": "HeH+",
        "molecular_charge": 1,
        "electron_count": 2,
        "basis": "STO-3G",
        "mapping": "JordanWignerMapper (no qubit reduction)",
        "ansatz": "UCCSD with HartreeFock initial state",
        "optimizer": anchor.optimizer,
        "estimator": anchor.estimator,
        "energy_convention": anchor.energy_convention,
        "calculation_context": "Local ideal-state simulation; not IBM hardware execution.",
        "sampled_lowest_vqe_point": {
            "bond_distance_angstrom": lowest.config.bond_distance_angstrom,
            "total_molecular_energy_hartree": lowest.total_molecular_energy_hartree,
        },
        "one_angstrom_check": {
            "vqe_total_energy_hartree": anchor.total_molecular_energy_hartree,
            "exact_classical_total_energy_hartree": anchor.classical_total_molecular_energy_hartree,
            "absolute_error_hartree": anchor.absolute_total_energy_error_hartree,
        },
        "files": {
            path.relative_to(output_directory).as_posix(): {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in generated_files
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the real HeH+ local VQE scan and export standalone challenge artifacts."
    )
    parser.add_argument(
        "--distances",
        type=float,
        nargs="+",
        default=DEFAULT_DISTANCES,
        metavar="ANGSTROM",
        help="He–H distances in Å (default: verified ten-point challenge grid).",
    )
    parser.add_argument("--maxiter", type=int, default=200, help="SLSQP maximum iterations.")
    parser.add_argument("--ftol", type=float, default=1e-10, help="SLSQP function tolerance.")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory for exported challenge artifacts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.distances:
        raise SystemExit("At least one bond distance is required.")
    if args.maxiter <= 0:
        raise SystemExit("--maxiter must be positive.")

    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    scan = run_potential_energy_scan(
        tuple(args.distances), maxiter=args.maxiter, ftol=args.ftol
    )

    raw_scan_path = output_directory / "hehplus_potential_energy_scan.json"
    csv_path = output_directory / "hehplus_potential_energy_curve.csv"
    curve_png_path = output_directory / "hehplus_potential_energy_curve.png"
    curve_svg_path = output_directory / "hehplus_potential_energy_curve.svg"
    circuit_png_path = output_directory / "hehplus_vqe_circuit_1.0A.png"
    circuit_text_path = output_directory / "hehplus_vqe_circuit_1.0A.txt"
    manifest_path = output_directory / "submission_manifest.json"

    _write_json(raw_scan_path, scan.to_dict())
    _write_csv(scan.results, csv_path)
    _render_curve(scan.results, curve_png_path, curve_svg_path)
    _render_circuit(_anchor_result(scan.results), circuit_png_path, circuit_text_path)
    generated_files = (
        raw_scan_path,
        csv_path,
        curve_png_path,
        curve_svg_path,
        circuit_png_path,
        circuit_text_path,
    )
    _write_json(manifest_path, _manifest(scan, output_directory, generated_files))

    anchor = _anchor_result(scan.results)
    lowest = min(scan.results, key=lambda result: result.total_molecular_energy_hartree)
    print(
        json.dumps(
            {
                "output_directory": str(output_directory),
                "scan_manifest": str(manifest_path),
                "points": len(scan.results),
                "one_angstrom_vqe_total_energy_hartree": anchor.total_molecular_energy_hartree,
                "one_angstrom_classical_total_energy_hartree": anchor.classical_total_molecular_energy_hartree,
                "one_angstrom_absolute_error_hartree": anchor.absolute_total_energy_error_hartree,
                "lowest_sampled_distance_angstrom": lowest.config.bond_distance_angstrom,
                "lowest_sampled_vqe_total_energy_hartree": lowest.total_molecular_energy_hartree,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
