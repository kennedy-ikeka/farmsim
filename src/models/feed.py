from pydantic import Field
from typing_extensions import Generator

import simpy
import numpy as np

from src.models.entity import Entity

class FeedModel(Entity): 
    size: float = Field(description="The size of the feed")
    name: str = Field(description="The name of the feed")
    sinks: bool = Field(description="Does the feed sink in water")
    rate: float = Field(default=1, description="The conversion rate of the feed")
    batches: list = Field(default_factory=list, description="The batches of this feed")

    def expire(self) -> Generator:
        ...

    def get_cost(self, weight: float) -> int:
        ...

    def get_quantity(self) -> int:
        ...

    def consume(self, weight: float) -> Generator: 
        ...

    def refill(self, weight: float):
        ...        