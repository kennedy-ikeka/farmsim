from enum import Enum

from pydantic import BaseModel, Field

from src.models.action import FarmActionState, MarketActionState, PassActionState
from src.models.game import GameState, Reality
from src.models.event import EventState


class StepState(BaseModel):
    """The next set of actions for the farm."""

    farmer: FarmActionState = Field(
        default_factory=PassActionState,
        description="The farmer's next action."
    )

    hands: list[FarmActionState] = Field(
        default_factory=list,
        description="The next actions assigned to hired workers."
    )

    market: list[MarketActionState] = Field(
        default_factory=list,
        description="The next market actions."
    )


class StepResultState(BaseModel):
    state: GameState = Field(description="The analyzed state of the game")
    reward: dict[int, float] = Field(default_factory=dict, description="The reward from the step")
    done: bool = Field(default=False, description="Has the step completed")


class EnvironmentState(BaseModel):
    state: GameState = Field(description="The analyzed state of the game")
    events: list[EventState] = Field(default_factory=list, description="All events in the environment")
