from pydantic import Field, computed_field
from typing_extensions import Generator

from src.models.asset import Asset
from src.models.fish import FishModel
from src.models.feed import FeedModel
from src.models.pond import PondModel


class BatchModel(Asset):
    pond_id: str = Field(..., description="The pond id for the batch")
    fish_ids: list[str] = Field(default_factory=list, description="The fishes in the batch")
    cycle_id: str = Field(..., description="The batch cycle id")
    duration: int = Field(..., description="The duration for the batch")
    kind: str = Field(default="Batch")

    @computed_field
    @property
    def pond(self) -> PondModel:
        return self.sim.get_asset("Pond", self.pond_id)

    @computed_field
    @property
    def fishes(self) -> list[FishModel]:
        return self.sim.list_assets("Fish", lambda x: x.id in self.fish_ids)
    
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
             