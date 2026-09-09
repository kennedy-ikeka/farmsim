from typing_extensions import Generator

from src.models.entity import Entity


class CycleModel(Entity):
    def stock_fishes(self, num_fishes: int, avg_weight: float) -> Generator:
        ...

    def get_next_feeding_time(self) -> float:
        ...

    def get_age(self) -> int:
        ...

    def feed_fishes(self) -> Generator:
        ...

    def clean_pond(self) -> Generator:
        ...

    def harvest_fishes(self) -> Generator:
        ...
        