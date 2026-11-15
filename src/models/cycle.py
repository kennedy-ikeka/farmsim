from dataclasses import dataclass
from typing import Optional

from typing_extensions import Generator
from pydantic import Field, computed_field, field_validator

from src.models.farm import FarmModel
from src.models.stock import Phase, Stock
from src.models.asset import Asset
from src.models.fish import FISH_SIZES, FISH_TYPES, FishModel
from src.models.batch import BatchModel


class CycleModel(Asset):   
    farm_id: str = Field(..., description="The farm id for the cycle")
    stock: Stock = Field(..., description="The cycles stocking")
    batch_ids: list[list[str]] = Field(default_factory=list, description="The cycle batches")
    kind: str = Field(default="Cycle")

    def get_farm(self) -> FarmModel:
        ...

    def get_fishes(self) -> list[FishModel]:
        ...

    def get_batches(self) -> list[list[BatchModel]]:
        ...

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
        