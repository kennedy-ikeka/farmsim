import simpy
from typing_extensions import Generator, Literal

from src.models.entity import Entity

ANIMAL_TYPE = Literal[
    "Catfish",
    "Tilapia"
]

class AnimalModel(Entity):
    weight: simpy.Container
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


