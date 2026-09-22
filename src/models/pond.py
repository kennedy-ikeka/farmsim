import simpy
from typing_extensions import Generator, Literal

from src.models.animal import AnimalModel
from src.models.entity import Entity

POND_TYPES = Literal[
    "Earthen_Pond", 
    "Concrete_Pond", 
    "Portable_Pond"
]

POND_TYPE_DETAILS = {
    "Earthen_Pond": {
        "cost": 1500, # Cheapest to construct
        "contamination_rate": 0.4,
        "feed_spawn_rate": 1.0 # baseline, rich natural feed
    },
    "Concrete_Pond": {
        "cost": 6000, # Very expensive to construct
        "contamination_rate": 0.14,
        "feed_spawn_rate": 0.6# moderate natural feed
    },
    "Portable_Pond": {
        "cost": 4000, # Moderatly expenseive to purchase
        "contamination_rate": 0.07,
        "feed_spawn_rate": 0.2 # very low natural feed
    }
}

class PondModel(Entity):
    fishes: list[AnimalModel]
    feed: simpy.Container
    health: simpy.Container

    def get_feed_availability(self) -> float:
        ...
        
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
