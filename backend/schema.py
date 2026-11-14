"""Validated request and response models shared with the frontend."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class OptimizationRequest(Model):
    sequence: str = Field(default="GAGA", min_length=2, max_length=8)
    method: Literal["classical", "qaoa"] = "classical"
    torsion_count: int = Field(default=3, ge=1, le=5, strict=True)
    angle_options: tuple[float, float] = (-60.0, 120.0)
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)
    layers: int = Field(default=1, ge=1, le=3, strict=True)
    max_iterations: int = Field(default=60, ge=10, le=120, strict=True)
    shots: int = Field(default=1024, ge=1, le=4096, strict=True)

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value):
        if not isinstance(value, str):
            raise ValueError("Sequence must be a string of one-letter amino-acid codes.")
        sequence = value.strip().upper()
        if any(code not in STANDARD_AMINO_ACIDS for code in sequence):
            raise ValueError("Use only the 20 standard one-letter amino-acid codes.")
        return sequence

    @field_validator("angle_options")
    @classmethod
    def validate_angles(cls, values):
        if any(not -180 <= value <= 180 for value in values):
            raise ValueError("Angles must be between -180 and 180 degrees.")
        if abs((values[0] - values[1]) % 360) < 1e-8:
            raise ValueError("Choose two distinct angles (modulo 360 degrees).")
        return values


class Torsion(Model):
    name: str
    residue_number: int
    atom_indices: tuple[int, int, int, int]


class Configuration(Model):
    bitstring: str
    angles_degrees: list[float]
    energy_kcal_mol: float


class BenchmarkResult(Model):
    minimum_energy_kcal_mol: float
    optimal_bitstrings: list[str]
    uniform_expected_energy_kcal_mol: float
    uniform_optimum_probability: float
    solver_expected_energy_kcal_mol: float
    solver_optimum_probability: float
    sampled_best_gap_kcal_mol: float


class OptimizationResult(Model):
    sequence: str
    method: Literal["classical", "qaoa"]
    execution_backend: str
    energy_model: str = "RDKit MMFF94, fixed-geometry discrete torsion scan"
    bit_order: str = "Rightmost bit controls the first torsion in the torsions list."
    seed: int
    torsions: list[Torsion]
    angle_options: tuple[float, float]
    configurations: list[Configuration]
    best_configuration: Configuration
    best_structure_molblock: str
    probabilities: dict[str, float]
    counts: dict[str, int]
    benchmark: BenchmarkResult
    optimizer_evaluations: int
    optimizer_converged: bool
    optimizer_message: str
    chemistry_seconds: float
    optimizer_seconds: float
    limitations: list[str]


class PeptideLookupRequest(Model):
    sequence: str = Field(min_length=2, max_length=200)
    limit: int = Field(default=5, ge=1, le=10, strict=True)
    include_similar: bool = False
    include_details: bool = True
    minimum_identity: float = Field(default=0.7, ge=0.5, le=1)

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value):
        return OptimizationRequest.normalize_sequence(value)
