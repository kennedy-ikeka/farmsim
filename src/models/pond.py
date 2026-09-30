from typing import Optional

import simpy
from typing_extensions import Generator, Literal

from src.models.animal import FishModel
from src.models.entity import Entity

POND_TYPES = Literal[
    "Earthen_Pond", 
    "Concrete_Pond", 
    "Portable_Pond"
]

POND_TYPE_DETAILS = {
    "Earthen_Pond": {
        "cost": 3000, # Cheapest to construct
        "contamination_rate": 0.4,
        "feed_spawn_rate": 1.0 # baseline, rich natural feed
    },
    "Concrete_Pond": {
        "cost": 10000, # Very expensive to construct
        "contamination_rate": 0.14,
        "feed_spawn_rate": 0.6# moderate natural feed
    },
    "Portable_Pond": {
        "cost": 6000, # Moderatly expenseive to purchase
        "contamination_rate": 0.07,
        "feed_spawn_rate": 0.2 # very low natural feed
    }
}

class PondModel(Entity):
    fishes: list[FishModel]
    feed: simpy.Container
    health: simpy.Container
    volume: float
    since: float
    duration: int

    def get_feed_availability(self) -> float:
        ...
        
    def get_cost(self, duration: int=0) -> int:
        ...

    def spawn_feed(self) -> Generator:
        ...

    def decontaminate(self) -> Generator:
        ...

    def contaminate(self) -> Generator:
        ...
