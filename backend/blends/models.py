"""Version 1 of the blend-research request contract; separate from shape search."""

from pydantic import Field, model_validator
from ..schema import Model


class ChemicalGoals(Model):
    ph: float = Field(default=7.4, ge=2, le=12)
    target_charge: float = Field(default=0, ge=-20, le=20)
    target_hydropathy: float = Field(default=0, ge=-4.5, le=4.5)
    charge_weight: float = Field(default=0.5, ge=0, le=1)
    hydropathy_weight: float = Field(default=0.5, ge=0, le=1)
    diversity_weight: float = Field(default=0.3, ge=0, le=2)

    @model_validator(mode="after")
    def nonzero_weights(self):
        if self.charge_weight + self.hydropathy_weight <= 0:
            raise ValueError("At least one chemical-property weight must be positive.")
        return self


class ShortlistRequest(ChemicalGoals):
    search: str = Field(default="", max_length=200)
    min_length: int = Field(default=2, ge=2, le=60, strict=True)
    max_length: int = Field(default=60, ge=2, le=60, strict=True)
    pool_size: int = Field(default=8, ge=2, le=8, strict=True)

    @model_validator(mode="after")
    def valid_lengths(self):
        if self.min_length > self.max_length:
            raise ValueError("Minimum length cannot exceed maximum length.")
        return self


class BlendRequest(ChemicalGoals):
    candidate_ids: list[str] = Field(min_length=2, max_length=8)
    blend_size: int = Field(default=3, ge=1, le=7, strict=True)
    layers: int = Field(default=1, ge=1, le=2, strict=True)
    max_iterations: int = Field(default=60, ge=10, le=120, strict=True)
    shots: int = Field(default=2048, ge=128, le=8192, strict=True)
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)

    @model_validator(mode="after")
    def valid_pool(self):
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("Candidate IDs must be unique.")
        if self.blend_size >= len(self.candidate_ids):
            raise ValueError("Choose fewer peptides than the number of candidates in the pool.")
        return self
