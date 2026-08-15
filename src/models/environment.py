from enum import Enum
import random
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from src.models.clock import ClockState
from src.models.action import FarmActionState, MarketActionState, PassActionState
from src.models.game import GameState, SharedRealityState
from src.models.event import EventState


class ValidStepsState(BaseModel):
    """The next set of actions for the farm."""
    
    farmer: list[FarmActionState] = Field(
        default_factory=list,
        description="The farmer's valid actions."
    )

    hands: list[list[FarmActionState]] = Field(
        default_factory=list,
        description="The valid actions assinable to hired workers. Empty list if no hand should act."
    )

    market: list[MarketActionState] = Field(
        default_factory=list,
        description="The valid market actions. Empty list if no market actions is needed."
    )

class StepState(BaseModel):
    """The next set of actions for the farm."""

    farmer: FarmActionState = Field(
        default_factory=PassActionState,
        description="The farmer's next action."
    )

    hands: list[FarmActionState] = Field(
        default_factory=list,
        description="The next actions assigned to hired workers. Empty list if no hand should act."
    )

    market: list[MarketActionState] = Field(
        default_factory=list,
        description="The next market actions. Empty list if no market actions is needed."
    )

    def to_kaggle(self) -> dict:
        """Serialize to the kaggle env's positional-list action format.

        The kaggle env parses `farmer` / each `hands` entry / each `market`
        entry as a list (`action[0]` = op, `action[1..2]` = args) via
        `_apply_unit_action` / `_parse_order`, which reject dicts. Use this
        at the agent boundary; the internal `Environment.step` keeps using
        the typed action objects directly.
        """
        step = {
            "farmer": self.farmer.to_list(),
            "hands": [h.to_list() for h in self.hands],
            "market": [m.to_list() for m in self.market],
        }
        print(step)
        return step


class StepResultState(BaseModel):
    state: GameState = Field(description="The analyzed state of the game")
    reward: dict[int, float] = Field(default_factory=dict, description="The reward from the step")
    done: bool = Field(default=False, description="Has the step completed")


class SimulationResultState(BaseModel):
    """Outcome of an `Environment.simulate` run — final balances + winner."""
    balances: dict[int, float] = Field(
        default_factory=dict,
        description="Final bank balance per player id."
    )
    winner: Optional[int] = Field(
        default=None,
        description="Player id with the highest balance, or None on a tie."
    )
    done: bool = Field(default=False, description="Whether the episode finished.")


class EnvironmentState(BaseModel):
    seed: int = Field(42, description="The seed for generation")
    state: SharedRealityState = Field(default_factory=SharedRealityState, description="The analyzed state of the game")
    clock: ClockState = Field(default_factory=ClockState, description="The clock of the game")
    events: list[EventState] = Field(default_factory=list, description="All events in the environment")
    done: bool = Field(default=False, description="Whether the episode has reached its final step.")

    _rng: random.Random = PrivateAttr()
    def model_post_init(self, __context) -> None:                                                                 
          self._rng = random.Random(self.seed)  
