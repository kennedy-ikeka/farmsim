from dataclasses import field, dataclass

import simpy
from typing_extensions import Generator, Literal

from models.cycle import Stock
from models.pond import PondModel
from src.models.feed import FeedModel
from src.models.entity import Entity

TRANSACTION_TYPES = Literal["credit", "debit"]

@dataclass
class FarmingModel:
    max_biomass_per_m3 = 30
    stocks: list[Stock] = field(default_factory=list)
    feeding_hours = [7, 19]
    pond_contamination_limit = 0.5

@dataclass
class BusinessModel:
    ...

class FarmModel(Entity):
    money: simpy.Container
    feeds: list[FeedModel]
    ponds: list[PondModel]
    stocking_pond: PondModel
    farming_model: FarmingModel
    business_model: BusinessModel
    
    def transact(self, type: TRANSACTION_TYPES, amount: int, item, quantity=1) -> Generator:
        ...

    def feed_exists(self, size: float) -> bool:
        ...
        
    def stock_feed(self, feed: FeedModel, weight: float) -> Generator:
        ...

    def get_available_pond(self, volume: float) -> PondModel:
        ...

    def acquire_pond(self, pond: PondModel) -> Generator:
        ...

    def get_appropriate_pond(self) -> PondModel:
        ...

    def run_cycles(self) -> Generator:
        ...

    
        