from dataclasses import dataclass
from typing import Optional

from pydantic import Field, field_validator

from src.models.fish import FISH_SIZES, FISH_TYPES


@dataclass
class Phase():
    duration: int
    fractions: list[float]
    harvest: float = Field(description="The fraction to harvest after phase", le=1, ge=0)
    target_size: FISH_SIZES = Field(description="The target size for this phase")

    @field_validator("fractions", check_fields=False)
    def validate_phases(cls, v: list[float]):
        if abs(sum(v) - 1.0) > 1e-9:
            raise ValueError("All stock phases must sum up to 1")

@dataclass
class Stock():
    id: int
    type: FISH_TYPES
    count: int
    size: FISH_SIZES
    phases: list[Phase]
    gap: Optional[int] = None

    @property
    def duration(self) -> int:
        return sum([p.duration for p in self.phases])