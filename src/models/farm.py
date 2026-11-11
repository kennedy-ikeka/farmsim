from pydantic import BaseModel, Field, computed_field, field_validator
from typing_extensions import Generator, Literal

from src.models.asset import Asset
from src.models.fish import FISH_SIZES
from src.models.cycle import CycleModel, Stock
from src.models.pond import PondModel
from src.models.feed import FeedModel

TRANSACTION_TYPES = Literal["credit", "debit"]


class FarmBusinessModel(BaseModel):
    capital: int = Field(default=100_000_00, description="The farming capital", ge=0)
    stocks: list[Stock] = Field(default_factory=list, min_length=1)
    feeding_hours: dict[int, list[int]] = Field(default={0: [7, 19]}, description="The hours for feeding fishes based on size") # at 7am and 7pm
    feed_conversion_rate: dict[int, float] = Field(default={0: 1.2}, description="The conversion of rate of the feed based on size")
    feed_floating: dict[int, bool] = Field(default={0: False}, description="The interval for medicating fishes based on size")
    max_biomass_per_m3: dict[int, int] = Field(default={0: 30}, description="Max biomax for pond based on size")
    pond_contamination_limit: dict[int, float] = Field(default={0: .5}, description="Contamination limits based on size")
    medication_interval: dict[int, int] = Field(default={0: 14}, description="The interval for medicating fishes based on size") # every 2weeks
    stock_increase_rate: float = Field(default=0, description="The rate at which the stocking quantity increases", ge=0, le=1)

    @field_validator('pond_contamination_limit')
    def vaidate_pond_contamination_limit(cls, v: dict[int, float]):
        for k, val in v.items():
            if k < 0:
                raise ValueError(f"Not a valid weight for pond_contamination_limit: {k}")
            if 0 >= val >= 1:
                raise ValueError(f"Not a valid pond_contamination_limit: {val}, for weight: {k}")
        return v

    @field_validator('feed_conversion_rate')
    def vaidate_feed_conversion_rate(cls, v: dict[int, float]):
        for k, val in v.items():
            if k < 0:
                raise ValueError(f"Not a valid weight for feed_conversion_rate: {k}")
            if 1 > val > 1.5:
                raise ValueError(f"Not a valid feed_conversion_rate: {val}, for weight: {k}")
        return v

    @field_validator('feeding_hours')
    def vaidate_feeding_hours(cls, v: dict[int, list[int]]):
        for k, val in v.items():
            if k < 0:
                raise ValueError(f"Not a valid weight for feeding_hourse: {k}")
            for t in val:
                if 0 > t > 24:
                    raise ValueError(f"Not a valid feeding_hours: {t}, for weight: {k} ")
        return v


class FarmModel(Asset):
    name: str = Field(..., description="The name of the farm")
    business_model: FarmBusinessModel = Field(default_factory=FarmBusinessModel, description="The business model of the farm")
    pond_ids: list[str] = Field(default_factory=list, description="The ponds for the farm")
    feed_ids: list[str] = Field(default_factory=list, description="The feeds for the farm")
    cycle_ids: list[str] = Field(default_factory=list, description="The cycles implemented by the farm")
    stocking_pond: PondModel = Field(default_factory=lambda data: PondModel(sim=data["sim"], type="Portable_Pond"), description="The ponds stocking portable pond")
    kind: str = Field(default="Farm")
    
    def transact(self, type: TRANSACTION_TYPES, amount: int, item: str, entity_tag: str, quantity=1) -> Generator:
        ...

    def feed_exists(self, size: float) -> bool:
        ...
        
    def stock_feed(self, feed: FeedModel, weight: float) -> Generator:
        ...

    def get_available_pond(self, volume: float) -> PondModel:
        ...

    def acquire_pond(self, pond: PondModel) -> Generator:
        ...

    def generate_appropriate_pond(self, target_weight: FISH_SIZES, count: int, duration: int) -> PondModel:
        ...

    def run_cycles(self) -> Generator:
        ...

    
        