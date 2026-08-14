"""Animal configuration — fixed costs and production parameters per animal.

Sourced from the Object Types table in README.md.
"""
from typing_extensions import Literal

from pydantic import BaseModel, Field

from src.models.objects import ANIMALS


AnimalStructure = Literal["COOP", "PASTURE"]
AnimalProduct = Literal["EGG", "MILK", "WOOL"]


class AnimalConfig(BaseModel):
    """Fixed cost and production parameters for a single animal kind.

    Attributes:
        cost: fixed market price to buy one animal.
        structure: the structure type that houses this animal (COOP / PASTURE).
        product: the product this animal produces (EGG / MILK / WOOL).
        first_yield_day: days from placement before the first yield is available.
        interval: days between successive yields (1 = every day).
        max_held: cap on unharvested product units on the tile (not lifetime output).
    """

    cost: int = Field(description="Fixed market price to buy one animal.")
    structure: AnimalStructure = Field(
        description="The structure type that houses this animal (COOP / PASTURE)."
    )
    product: AnimalProduct = Field(
        description="The product this animal produces (EGG / MILK / WOOL)."
    )
    first_yield_day: int = Field(
        description="Days from placement before the first yield is available."
    )
    interval: int = Field(
        description="Days between successive yields (1 = every day)."
    )
    max_held: int = Field(
        description=(
            "Cap on unharvested product units on the tile "
            "(not lifetime output — animals produce indefinitely while fed)."
        )
    )


ANIMAL_CONFIG: dict[ANIMALS, AnimalConfig] = {
    "GOOSE": AnimalConfig(
        cost=300,
        structure="COOP",
        product="EGG",
        first_yield_day=4,
        interval=1,   # produces every day
        max_held=4,
    ),
    "COW": AnimalConfig(
        cost=400,
        structure="PASTURE",
        product="MILK",
        first_yield_day=8,
        interval=2,   # produces every two days
        max_held=6,
    ),
    "SHEEP": AnimalConfig(
        cost=500,
        structure="PASTURE",
        product="WOOL",
        first_yield_day=6,
        interval=3,   # produces every three days
        max_held=6,
    ),
}