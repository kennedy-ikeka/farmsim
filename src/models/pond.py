from typing_extensions import Generator, Literal

from src.models.entity import Entity

POND_TYPES = Literal[
    "Earthen", 
    "Concrete", 
    "Portable"
]

POND_BASE_COSTS = {
    "Earthen": 1500, # Cheapest to construct
    "Concrete": 6000, # Very expensive to construct
    "Portable": 4000, # Moderatly expenseive to purchase
}

POND_CONTAMINATION_RATE = {
    "Earthen": 0.4,    # 40% relative risk
    "Concrete": 0.15,  # 15% relative risk
    "Portable": 0.07   # 7% relative risk
}

POND_SPAWN_FEED_RATE = {
    "Earthen": 1.0,   # baseline, rich natural feed
    "Concrete": 0.6,  # moderate natural feed
    "Portable": 0.2   # very low natural feed
}

class PondModel(Entity):
    def get_cost(self) -> float:
        ...

    def get_rent_cost(self, duration=1) -> float:
        ...

    def spawn_feed(self) -> Generator:
        ...

    def decontaminate(self) -> Generator:
        ...

    def contaminate(self) -> Generator:
        ...
