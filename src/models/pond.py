from dataclasses import dataclass
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

@dataclass
class PondDetail:
    cost: int # cost of 1 cubic meter or 1000 liters
    contamination_rate: float # rate at which pond gets dirty
    feed_spawn_rate: float # rate at which naturally occuring feed grows in the pond
    seepage: bool # rate at which rain enters or leaves the pond depending on the weather

POND_TYPE_DETAILS = {
    "Earthen_Pond": PondDetail(30000_00, .4, 1, True),
    "Concrete_Pond": PondDetail(150000_00, .14, .6, False),
    "Portable_Pond": PondDetail(60000_00, .07, .2, False)
}

POND_RENTAL_INTERVAL = 30

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
