from pydantic import BaseModel, Field

from src.models.farm import FarmState
from src.models.market import MarketState
from src.models.player import PrivateState
from src.models.town import TownState


class GameState(BaseModel):
    """The state of the game exposed to the player"""

    remainingOverageTime: int = Field(
        description=("Remaining computation/time allowance available to the player for the current game state.")
    )

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

    farms: list[FarmState] = Field(
        description="All farms belonging to the players in the game."
    )

    privates: list[PrivateState] = Field(
        description="Per-player private state, indexed by player id."
    )

    market: MarketState = Field(
        description="Public marketplace state, including inventory and prices."
    )

    town: TownState = Field(
        description="Current state of the town and its available shops."
    )
