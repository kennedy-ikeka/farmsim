from pydantic import Field, computed_field
from typing_extensions import Generator

from src.models.asset import Asset
from src.models.fish import FishModel
from src.models.feed import FeedModel
from src.models.pond import PondModel


class BatchModel(Asset):
    farm_id: str = Field(..., description="The farm id for the batch")
    pond_id: str = Field(..., description="The pond id for the batch")
    fishes: list[FishModel] = Field(default_factory=list, description="The fishes in the batch")
    cycle_id: str = Field(..., description="The batch cycle id")
    duration: int = Field(..., description="The duration for the batch")
    kind: str = Field(default="Batch")

    @computed_field
    @property
    def pond(self) -> PondModel:
        return self.sim.assets['Pond'][self.pond_id]

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
             