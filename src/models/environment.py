from enum import Enum
import random

from pydantic import BaseModel, Field, PrivateAttr

from src.domains.environment.clock import Clock
from src.models.action import FarmActionState, MarketActionState, PassActionState
from src.models.game import GameState
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


class TurnActions(BaseModel):
    """All players' actions for a single step, indexed by player id."""
    actions: list[StepState] = Field(
        description="Per-player turn payloads; actions[p] is player p's actions."
    )


class EnvironmentState(BaseModel):
    seed: int = Field(description="The seed for generation")
    state: GameState = Field(description="The analyzed state of the game")
    clock: Clock = Field(default_factory=Clock, description="The clock of the game")
    events: list[EventState] = Field(default_factory=list, description="All events in the environment")
    done: bool = Field(default=False, description="Whether the episode has reached its final step.")

    _rng: random.Random = PrivateAttr()
    def model_post_init(self, __context) -> None:                                                                 
          self._rng = random.Random(self.seed)  
