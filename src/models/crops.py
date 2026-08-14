"""Crop growth configuration (the GAME CONFIG block from gameplay/roadmap.md).

Sourced from the Object Types table in README.md. These values drive seed
purchasing, planting, and the decay schedule.
"""
from typing_extensions import Literal

from pydantic import BaseModel, Field

from src.models.objects import CROPS


YieldType = Literal["one-time", "ongoing"]


class CropConfig(BaseModel):
    """Per-crop growth parameters.

    Attributes:
        yield_type: "one-time" (single harvest) or "ongoing" (repeated yields).
        seed_cost: fixed market price to buy one seed.
        first_yield_day: days from planting before the first yield is available.
        max_yield_day: day (from planting) of the last scheduled yield; decay
            begins one day after this for both yield types.
        max_yield: total harvestable units a single plant can produce.
    """

    yield_type: YieldType = Field(description="Whether the crop is harvested once or repeatedly.")
    seed_cost: int = Field(description="Fixed market price to buy one seed.")
    first_yield_day: int = Field(
        description="Days from planting before the first yield is available."
    )
    max_yield_day: int = Field(
        description=(
            "Day (from planting) of the last scheduled yield; decay begins "
            "one day after this for both yield types."
        )
    )
    max_yield: int = Field(
        description="Total harvestable units a single plant can produce."
    )


CROP_CONFIG: dict[CROPS, CropConfig] = {
    "WHEAT": CropConfig(
        yield_type="one-time",
        seed_cost=10,
        first_yield_day=2,
        max_yield_day=4,
        max_yield=6,
    ),
    "CARROT": CropConfig(
        yield_type="one-time",
        seed_cost=20,
        first_yield_day=2,
        max_yield_day=3,
        max_yield=4,
    ),
    "TOMATO": CropConfig(
        yield_type="ongoing",
        seed_cost=50,
        first_yield_day=8,
        max_yield_day=11,
        max_yield=4,
    ),
    "STRAWBERRY": CropConfig(
        yield_type="ongoing",
        seed_cost=100,
        first_yield_day=10,
        max_yield_day=16,
        max_yield=4,
    ),
    "MELON": CropConfig(
        yield_type="one-time",
        seed_cost=80,
        first_yield_day=10,
        max_yield_day=10,
        max_yield=6,
    ),
}