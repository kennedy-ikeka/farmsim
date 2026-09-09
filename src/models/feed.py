from typing_extensions import Generator

import simpy
import numpy as np

from src.models.entity import Entity

class FeedModel(Entity): 
    def expire(self) -> Generator:
        ...

    def get_cost(self, weight: float) -> float:
        ...

    def get_quantity(self) -> int:
        ...

    def consume(self, weight: float) -> Generator: 
        ...

    def refill(self, weight: float):
        ...        