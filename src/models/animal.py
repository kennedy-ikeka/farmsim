
from typing import Optional

from faker import Generator
from pydantic import Field
from simpy.events import ProcessGenerator

from src.models.asset import Asset

class AnimalModel(Asset):
    type: str = Field(..., description="The type of animal")
    cycle_id: Optional[str] = Field(default=None, description="The cycle id of the animal")
    batch_id: Optional[str] = Field(default=None, description="The batch id of the animal")
    farm_id: Optional[str] = Field(default=None, description="The farm id of the animal")
    kind: str = Field(default="Animal")

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

    def terminate(self) -> ProcessGenerator:
        ...