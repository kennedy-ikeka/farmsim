from dataclasses import dataclass
from typing import Optional

from typing_extensions import Generator, Literal
from simpy.resources.container import Container

from src.models.entity import Entity

COST_PER_KILO = 2_500_00 # In kobo

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
    daily_feeding_ratio: float


FISH_SIZE_DETAILS = {
    "Hatched": FishSize(0, 1, .5, 0.05),
    "Fry": FishSize(1, 5, .6, 0.05),
    "Small_Fingerlin": FishSize(5, 10, .8, 0.04),
    "Medium_Fingerlin": FishSize(10, 20, 1.2, 0.04),
    "Large_Fingerlin": FishSize(20, 50, 1.5, 0.04),
    "Juveniles": FishSize(50, 100, 2, 0.03),
    "Small_Table": FishSize(100, 250, 3, 0.02),
    "Medium_Table": FishSize(250, 500, 4, 0.02),
    "Large_Table": FishSize(500, 1000, 5, 0.02),
    "Jumbo": FishSize(1000, 2000, 6, 0.01),
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

    def terminate(self) -> Generator:
        ...

class FishModel(AnimalModel):
    stock_id: Optional[int]
    batch_id: Optional[int]
    def set_pond(self, pond):
        ...


