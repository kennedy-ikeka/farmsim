from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from typing_extensions import Generator
from pydantic import BaseModel, Field, field_validator

from models.animal import FISH_SIZES, FISH_TYPES
from models.batch import BatchModel
from models.pond import PondModel
from src.models.entity import Entity
from utils.conversion import to_kilo

@dataclass
class Phase():
    duration: int
    fractions: list[float]
    harvest: float = Field(description="The fraction to harvest after phase", le=1, gt=0)
    target_size: FISH_SIZES = Field(description="The target size for this phase")

    @field_validator("fractions", check_fields=False)
    def validate_phases(cls, v: list[float]):
        if abs(sum(v) - 1.0) > 1e-9:
            raise ValueError("All stock phases must sum up to 1")

@dataclass
class Stock():
    type: FISH_TYPES
    count: int
    size: FISH_SIZES
    phases: list[Phase]
    gap: Optional[int] = None
    id: str = ""

    @property
    def duration(self) -> int:
        return sum([p.duration for p in self.phases])


class CycleModel(Entity):    
    stock = Stock
    batches: list[BatchModel] = []
    
    def run_phases(self) -> Generator:
        ...

    def stock_fishes(self, num_fishes: int, size: FISH_SIZES) -> Generator:
        ...

    def harvest_fishes(self) -> Generator:
        ...
        