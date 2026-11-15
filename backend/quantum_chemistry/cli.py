"""Command-line entry point for the isolated HeH+ VQE experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .heh_plus import (
    DEFAULT_OUTPUT_DIRECTORY,
    HeHPlusConfig,
    run_heh_plus_vqe,
    run_potential_energy_scan,
    save_result,
    save_scan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a real local-statevector VQE / exact-reference HeH+ calculation "
            "using PySCF, Qiskit Nature, UCCSD, and Jordan-Wigner mapping."
        )
    )
    geometry = parser.add_mutually_exclusive_group()
    geometry.add_argument(
        "--distance",
        type=float,
        default=1.0,
        help="One He-H bond distance in Angstrom (default: 1.0).",
    )
    geometry.add_argument(
        "--scan",
        type=float,
        nargs="+",
        metavar="ANGSTROM",
        help="Two or more (or one) explicitly listed bond distances in Angstrom.",
    )
    parser.add_argument("--maxiter", type=int, default=200, help="SLSQP maximum iterations.")
    parser.add_argument("--ftol", type=float, default=1e-10, help="SLSQP function tolerance.")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Where actual, ignored calculation artifacts are written.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.scan is not None:
        scan = run_potential_energy_scan(
            args.scan,
            maxiter=args.maxiter,
            ftol=args.ftol,
        )
        path = save_scan(scan, args.output_directory)
        print(json.dumps({"saved_scan": str(path), **scan.to_dict()}, indent=2, sort_keys=True))
        return 0

    result = run_heh_plus_vqe(
        HeHPlusConfig(
            bond_distance_angstrom=args.distance,
            maxiter=args.maxiter,
            ftol=args.ftol,
        )
    )
    json_path, circuit_path = save_result(result, args.output_directory)
    print(
        json.dumps(
            {
                "saved_result": str(json_path),
                "saved_circuit": str(circuit_path),
                **result.to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI
    raise SystemExit(main())
