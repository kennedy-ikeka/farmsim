
from typing_extensions import Literal, Optional

from pydantic import Field, BaseModel


TILE_MODE = Literal['NONE', 'LOCKED']


class FarmState(BaseModel):
    """Represents a player's individual farm."""

    money: float = Field(
        description="Amount of money currently available to the farmer."
    )

    tiles: list[list[Optional[TILE_MODE]]] = Field(
        description=(
            "10x10 farm grid. A tile is None when it is available/empty, "
            "or 'LOCKED' when the tile has not been unlocked."
        )
    )

    farmer: list[int] = Field(
        description="Current [row, column] position of the farmer on the farm grid.",
        min_length=2,
        max_length=2,
    )

    hands: list = Field(
        description="Items currently being carried or held by the farmer."
    )

    unlocked_quadrants: list[str] = Field(
        description=(
            "Quadrants of the farm that have been unlocked. "
            "Examples include NW, NE, SW, and SE."
        )
    )

    hires_today: int = Field(
        description="Number of workers hired by this farm during the current day."
    )

