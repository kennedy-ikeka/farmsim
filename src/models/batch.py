from pydantic import Field, computed_field
from typing_extensions import Generator

from src.models.farm import FarmModel
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

    def get_pond(self) -> PondModel:
        ...

    def fishes(self) -> list[FishModel]:
        ...

    def get_farm(self) -> FarmModel:
        ...
    
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
             