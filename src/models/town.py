from typing_extensions import Literal
from pydantic import BaseModel, Field

TOWN_SHOPS = Literal['PET_CAFE', 'YARN_STORE', 'BRUNCH_SPOT', 'PIZZA_SHOP', 'SMOOTHIE_SHOP', 'ICE_CREAM_SHOP']


class TownState(BaseModel):
    """State of the town and its available shops."""

    unlocked_shops: list[TOWN_SHOPS] = Field(
        description="Names or identifiers of shops currently unlocked in town."
    )

