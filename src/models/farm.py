from typing import Optional, Union
from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field

from src.models.objects import ANIMALS, CROPS


# A locked-quadrant tile is represented in the raw game state by the literal
# string "LOCKED" (see gameplay/observation.json). Empty unlocked tiles are None.
LOCKED_TILE = Literal["LOCKED"]


class PlantState(BaseModel):
    """A planted crop occupying a single farm tile.

    Tracks the crop's planting day, watering state, accumulated harvestable
    yield, and the step at which decay begins. Per gameplay/AGENTS.md, the
    planting day counts as the first unwatered day, and two consecutive missed
    end-of-day refreshes turn the plant into a weed.
    """

    kind: Literal["PLANT"] = Field(
        default="PLANT", description="Tile kind discriminator."
    )
    crop: CROPS = Field(description="The crop planted on this tile.")
    planted_day: int = Field(
        description="In-game day the seed was planted (0-indexed)."
    )
    watered_today: bool = Field(
        default=False,
        description="Whether the plant has been watered during the current day.",
    )
    consecutive_unwatered: int = Field(
        default=0,
        description=(
            "Consecutive end-of-day refreshes missed. Two in a row turns the "
            "plant into a weed."
        ),
    )
    yield_units: int = Field(
        default=0,
        description="Harvestable units currently accumulated on the plant.",
    )
    max_lifespan_step: int = Field(
        description=(
            "Step (turn) at which the plant passes its max lifespan and begins "
            "to decay (one day after the crop's max_yield_day)."
        ),
    )
    fertilized_until_day: int = Field(
        default=0,
        description=(
            "Day through which FERTILIZE's watering bonus remains active "
            "(0 if unfertilized)."
        ),
    )


class WeedState(BaseModel):
    """A weed occupying a tile.

    Weeds spawn on empty unlocked tiles with probability `weedSpawnChance` at
    end-of-day, or appear when a plant dies from neglect. Cleared with DIG.
    """

    kind: Literal["WEED"] = Field(
        default="WEED", description="Tile kind discriminator."
    )


class AnimalState(BaseModel):
    """A coop or pasture structure, optionally housing a producing animal.

    COOP houses geese (eggs); PASTURE houses cows (milk) or sheep (wool). Animals
    must be fed wheat daily; two consecutive missed feeds cause the animal to
    escape (unrecoverable). `max_held` caps `yield_units` (unharvested product),
    not lifetime output — animals produce indefinitely while fed. CARE banks +1
    per fed-and-cared day, paid out in full on the next scheduled production.
    """

    kind: Literal["COOP", "PASTURE"] = Field(
        description=(
            "Tile kind discriminator: COOP houses geese, PASTURE houses cows/sheep."
        )
    )
    animal: Optional[ANIMALS] = Field(
        default=None,
        description=(
            "The animal housed on this structure, if any — GOOSE on a COOP, "
            "COW or SHEEP on a PASTURE."
        ),
    )
    placed_day: Optional[int] = Field(
        default=None,
        description="In-game day the structure (or its animal) was placed.",
    )
    yield_units: int = Field(
        default=0,
        description="Unharvested product units on the tile (capped by max_held).",
    )
    fed_today: bool = Field(
        default=False,
        description="Whether the animal was fed during the current day.",
    )
    consecutive_unfed: int = Field(
        default=0,
        description=(
            "Consecutive end-of-day feeds missed. Two in a row and the animal "
            "escapes (unrecoverable)."
        ),
    )
    cared_today: bool = Field(
        default=False,
        description="Whether the CARE action was applied during the current day.",
    )
    fertilizer_available: int = Field(
        default=0,
        description="Accumulated fertilizer units available to COLLECT_FERTILIZER.",
    )
    pending_care_bonus: int = Field(
        default=0,
        description=(
            "Banked CARE bonuses (one per fed-and-cared day) to pay out in full "
            "on the next scheduled production."
        ),
    )


# Discriminated union of the dict-like tile occupants (dispatched on `kind`).
OccupiedTileState = Annotated[
    Union[PlantState, WeedState, AnimalState],
    Field(discriminator="kind"),
]

# A farm tile is either empty (None), in a locked quadrant ("LOCKED"), or one
# of the occupied-tile states above.
TileState = Optional[Union[LOCKED_TILE, OccupiedTileState]]


class FarmState(BaseModel):
    """Represents a player's individual farm."""

    money: float = Field(
        3000,
        description="Amount of money currently available to the farmer."
    )

    tiles: list[list[TileState]] = Field(
        default_factory=list,
        description=(
            "10x10 farm grid indexed tiles[row][col]. A tile is None when "
            "empty and unlocked, 'LOCKED' when in an unbought quadrant, a "
            "PlantState for a planted crop, a WeedState for a weed, or an "
            "AnimalState for a coop/pasture structure."
        )
    )

    farmer: list[int] = Field(
        default=[5,5],
        description="Current [row, column] position of the farmer on the farm grid.",
        min_length=2,
        max_length=2,
    )

    hands: list = Field(
        default=[],
        description="Items currently being carried or held by the farmer."
    )

    unlocked_quadrants: list[str] = Field(
        default_factory=list,
        description=(
            "Quadrants of the farm that have been unlocked. "
            "Examples include NW, NE,, SW, and SE."
        )
    )

    hires_today: int = Field(
        0,
        description="Number of workers hired by this farm during the current day."
    )
    