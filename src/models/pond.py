from dataclasses import dataclass
from typing import Optional

from pydantic import Field, computed_field
from simpy.core import SimTime
from typing_extensions import Generator, Literal

from src.models.asset import Asset
from src.models.fish import FishModel
from src.utils.conversion import DAY_IN_HOURS, HOUR_IN_MINUTES

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

class PondModel(Asset):
    fishes: list[FishModel] = Field(default_factory=list, description="Fishes in the pond")
    length: float = Field(default=1.0, description="The length of the pond")
    width: float = Field(default=1.0, description="The width of the pond")
    depth: float = Field(default=1.0, description="The depth of the pond")
    density: float = Field(default=1.0, description="The depth of the pond")
    aerated: bool = Field(default=False, description="The aeration status of the pond")
    duration: int = Field(default=0, description="The duration of the pond")
    type: POND_TYPES = Field(..., description="The type of pond")    
    acquired_at: Optional[SimTime] = Field(default=None, description="Time when pond was aqcuired")
    kind: str = Field(default="Pond")
       
    @computed_field
    @property
    def volume(self) -> float:
        return self.length * self.width * self.depth

    @computed_field
    @property
    def capacity(self) -> float:
        return self.volume * self.density

    @computed_field
    @property
    def details(self) -> PondDetail:
        return POND_TYPE_DETAILS[self.type]

    @computed_field
    @property
    def drain_speed(self) -> float:
        return self.rng.integers(30, 40) / HOUR_IN_MINUTES / DAY_IN_HOURS  # drain speed in days
    
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
