from dataclasses import dataclass

from typing_extensions import Generator, Literal
from simpy.resources.container import Container

from src.models.entity import Entity

COST_PER_KILO = 2500

FISH_TYPES = Literal[
    "Catfish",
    "Tilapia"
]

FISH_SIZES = Literal[
    "Hatched",
    "Fry",
    "Small_Fingerlin",
    "Medium_Fingerlin",
    "Large_Fingerlin",
    "Juveniles",
    "Small_Table",
    "Medium_Table",
    "Large_Table",
    "Jumbo"
]

@dataclass
class FishSize:
    min_size: int
    max_size: int
    feed_size: float


FISH_SIZE_DETAILS = {
    "Hatched": FishSize(0, 1, .5),
    "Fry": FishSize(1, 5, .6),
    "Small_Fingerlin": FishSize(5, 10, .8),
    "Medium_Fingerlin": FishSize(10, 20, 1.2),
    "Large_Fingerlin": FishSize(20, 50, 1.5),
    "Juveniles": FishSize(50, 100, 2),
    "Small_Table": FishSize(100, 250, 3),
    "Medium_Table": FishSize(250, 500, 4),
    "Large_Table": FishSize(500, 1000, 5),
    "Jumbo": FishSize(1000, 2000, 6),
}

class AnimalModel(Entity):
    weight: Container
    id: int
    
    def get_hunger_rate(self) -> float:
        ...

    def get_hunt_rate(self) -> float:
        ...

    def get_stomach_size(self) -> float:
        ...

    def get_hunger_weight(self) -> float:
        ...

    def get_waste_weight(self) -> float:
        ...

    def get_feeding_rank(self) -> float:
        ...

    def eat(self, feed_weight: float, fcr=1) -> Generator:
        ...

    def hunt(self) -> Generator:
        ...

    def excrete(self, excrete_weight: float) -> Generator:
        ...

    def digest(self) -> Generator:
        ...

    def die(self) -> Generator:
        ...

class FishModel(AnimalModel):
    def set_pond(self, pond):
        ...


