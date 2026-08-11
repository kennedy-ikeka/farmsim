from typing import Any, Union
from typing_extensions import Literal

from pydantic import BaseModel, Field

from src.models.action import (
    INVENTORY_ACTIONS,
    MARKET_ACTIONS,
    MOVE_ACTIONS,
    PLANT_ACTIONS,
    TERRAIN_ACTIONS,
    ANIMAL_ACTIONS,
    TOWN_ACTIONS,
)

# Every action that can be performed during a step is an event. The grouped
# action literals (PLANT_ACTIONS, MOVE_ACTIONS, etc.) are reused so this stays
# in sync with the action model; the animal-structure and care actions and the
# PASS no-op live only as individual Literal tags on their action classes.
# TOWN_ACTIONS covers environment-driven town events (no player action).
EVENT_TYPES = Union[
    MOVE_ACTIONS,
    PLANT_ACTIONS,
    TERRAIN_ACTIONS,
    INVENTORY_ACTIONS,
    ANIMAL_ACTIONS,
    MARKET_ACTIONS,
    TOWN_ACTIONS,
    Literal["PASS"],
]


class EventState(BaseModel):
    step: int = Field(
        description="Current simulation step or turn number."
    )

    day: int = Field(
        description="Current in-game day."
    )

    hour: int = Field(
        description="Current in-game hour."
    )

    player: int = Field(
        description="Identifier of the player whose turn/state is being represented."
    )

    type: EVENT_TYPES = Field(
        description="Identifier of the player whose turn/state is being represented."
    )

    intended: dict[str, Any] = Field(
        default_factory=dict,
        description="The action's requested parameters."
    )

    occurred: dict[str, Any] = Field(
        default_factory=dict,
        description="What actually happened."
    )
    