from dataclasses import dataclass
from typing import Optional

from typing_extensions import Generator
from pydantic import Field, field_validator

from src.models.asset import Asset
from src.models.fish import FISH_SIZES, FISH_TYPES
from src.models.batch import BatchModel

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


class CycleModel(Asset):   
    farm_id: str = Field(..., description="The farm id for the cycle")
    stock: Stock = Field(..., description="The cycles stocking")
    batches: list[list[BatchModel]] = Field(default_factory=list, description="The cycle batches")
    kind: str = Field(default="Cycle")

    def split_phase(self, phase: Phase):
        ...
    
    def run_phases(self) -> Generator:
        ...

    def stock_fishes(self, num_fishes: int, size: FISH_SIZES) -> Generator:
        ...

    def harvest_fishes(self) -> Generator:
        ...

    def exist(self) -> Generator:
        ...
        