from dataclasses import dataclass

from pydantic import Field
from typing_extensions import Literal

from src.models.animal import AnimalModel

COST_PER_KILO = 2_500_00 # In kobo

FISH_TYPES = Literal[
    "Catfish",
    "Tilapia"
]

FISH_SIZES = Literal[
    "Hatched",
    "Fry",
    "Small_Fingerlin",
    "Medium_Fingerlin",
    "Large_Fingerlin",
    "Juveniles",
    "Small_Table",
    "Medium_Table",
    "Large_Table",
    "Jumbo"
]

@dataclass
class FishSize:
    min_size: int
    max_size: int
    feed_size: float
    daily_feeding_ratio: float
    default_price: float


FISH_SIZE_DETAILS = {
    "Hatched": FishSize(0, 1, .5, 0.05, 2_00),
    "Fry": FishSize(1, 5, .6, 0.05, 10_00),
    "Small_Fingerlin": FishSize(5, 10, .8, 0.04, 25_00),
    "Medium_Fingerlin": FishSize(10, 20, 1.2, 0.04, 40_00),
    "Large_Fingerlin": FishSize(20, 50, 1.5, 0.04, 70_00),
    "Juveniles": FishSize(50, 100, 2, 0.03, 150_00),
    "Small_Table": FishSize(100, 250, 3, 0.02, 550_00),
    "Medium_Table": FishSize(250, 500, 4, 0.02, 1200_00),
    "Large_Table": FishSize(500, 1000, 5, 0.02, 2400_00),
    "Jumbo": FishSize(1000, 2000, 6, 0.01, 4500_00),
}

class FishModel(AnimalModel):
    pond_id: str = Field(..., description="The id of the fish pond")
    type: FISH_TYPES = Field(..., description="The type of fish")
    kind: str = Field(default="Fish")
