import simpy
from typing_extensions import Generator, Literal

from src.models.animal import AnimalModel
from src.models.entity import Entity

POND_TYPES = Literal[
    "Earthen_Pond", 
    "Concrete_Pond", 
    "Portable_Pond"
]

POND_BASE_COSTS = {
    "Earthen_Pond": 1500, # Cheapest to construct
    "Concrete_Pond": 6000, # Very expensive to construct
    "Portable_Pond": 4000, # Moderatly expenseive to purchase
}

POND_CONTAMINATION_RATE = {
    "Earthen_Pond": 0.4,    # 40% relative risk
    "Concrete_Pond": 0.15,  # 15% relative risk
    "Portable_Pond": 0.07   # 7% relative risk
}

POND_SPAWN_FEED_RATE = {
    "Earthen_Pond": 1.0,   # baseline, rich natural feed
    "Concrete_Pond": 0.6,  # moderate natural feed
    "Portable_Pond": 0.2   # very low natural feed
}

class PondModel(Entity):
    fishes: list[AnimalModel]
    feed: simpy.Container
    health: simpy.Container

    def get_cost(self) -> float:
        ...

    def get_rent_cost(self, duration=1) -> float:
        ...

    def spawn_feed(self) -> Generator:
        ...

    def decontaminate(self) -> Generator:
        ...

    def contaminate(self) -> Generator:
        ...
