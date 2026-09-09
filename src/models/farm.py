from typing_extensions import Generator, Literal

from src.models.feed import FeedModel
from src.models.entity import Entity

TRANSACTION_TYPES = Literal["credit", "debit"]

class FarmModel(Entity):
    def transact(self, type: TRANSACTION_TYPES, amount, item, quantity=1) -> Generator:
        ...

    def get_feed_size(self) -> float:
        ...

    def get_appropriate_feed(self) -> (FeedModel | None):
        ...

    def feed_exists(self, size: float) -> bool:
        ...
        
    def stock_feed_process(self, feed: FeedModel, weight: bool) -> Generator:
        ...

    def acquire_pond(self) -> Generator:
        ...

    def start_cycle(self) -> Generator:
        ...

    
        