from dataclasses import dataclass
from typing import Optional
from typing_extensions import Generator

from pydantic import Field
from simpy import Container

from src.models.asset import Asset

@dataclass
class FeedBatch:
    time: float
    stock: Container

class FeedModel(Asset): 
    size: float = Field(..., description="The size of the feed")
    name: str = Field(..., description="The name of the feed")
    floats: bool = Field(default=True, description="Does the feed sink in water")
    rate: float = Field(default=1.0, description="The conversion rate of the feed")
    batches: list[FeedBatch] = Field(default_factory=list, description="The batches of this feed")
    farm_id: Optional[str] = Field(default=None, description="The farm id for the feed")
    kind: str = Field(default="Feed")

    def expire(self) -> Generator:
        ...

    def get_cost(self, weight: int) -> int:
        ...

    def get_quantity(self) -> int:
        ...

    def consume(self, weight: float) -> Generator: 
        ...

    def refill(self, weight: int):
        ...        