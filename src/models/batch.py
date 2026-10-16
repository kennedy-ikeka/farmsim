from typing_extensions import Generator

from models.animal import FishModel
from models.entity import Entity
from models.feed import FeedModel
from models.pond import PondModel


class BatchModel(Entity):
    active: bool
    duration: int
    pond: PondModel
    fishes: list[FishModel]

    def next_feeding_time(self) -> float:
        ...

    def feed_size(self) -> float:
        ...

    def appropriate_feed(self) -> FeedModel:
        ...

    def feed_fishes(self) -> Generator:
        ...

    def clean_pond(self) -> Generator:
        ...