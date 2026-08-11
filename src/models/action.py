from typing_extensions import Annotated, Generic, TypeVar, Literal, Union

from pydantic import BaseModel, Field

from src.models.objects import ANIMALS, BUYABLE_PRODUCTS, CROPS, SELLABLE_PRODUCTS

T = TypeVar("T")

PLANT_ACTIONS = Literal['PLANT', 'WATER', 'HARVEST', 'FERTILIZE']
TERRAIN_ACTIONS = Literal['DIG']
MOVE_ACTIONS = Literal['NORTH', 'SOUTH', 'EAST', 'WEST']
INVENTORY_ACTIONS = Literal['PICKUP', 'PLACE']
MARKET_ACTIONS = Literal['BUY_SEED', 'BUY_PRODUCT', 'BUY_ANIMAL', 'SELL', 'HIRE', 'BUY_LAND']
ANIMAL_ACTIONS = Literal["BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE"]
# Town events are environment-driven (not player actions): a shop unlocking, an
# unlocked shop consuming market inventory, or the town center consuming market
# inventory on its tick. Recorded as EventState with player=-1.
TOWN_ACTIONS = Literal["SHOP_UNLOCK", "SHOP_CONSUME", "CENTER_CONSUME"]

class BaseAction(BaseModel, Generic[T]):
    """Base action model. The `type` field is generic so subclasses can
    constrain it to a specific Literal action tag."""

    type: T = Field(description="The action type tag")


class PlantActionState(BaseAction[Literal['PLANT']]):
    """Plant a new crop"""
    crop: CROPS = Field(description="The crop to plant")


class MoveActionState(BaseAction[MOVE_ACTIONS]):
    pass


class WaterActionState(BaseAction[Literal["WATER"]]):
    pass


class HarvestActionState(BaseAction[Literal["HARVEST"]]):
    pass


class FertilizeActionState(BaseAction[Literal["FERTILIZE"]]):
    pass


class DigActionState(BaseAction[Literal["DIG"]]):
    pass


class BuildCoopActionState(BaseAction[Literal["BUILD_COOP"]]):
    """Erect an empty goose coop on the unit's current tile."""


class BuildPastureActionState(BaseAction[Literal["BUILD_PASTURE"]]):
    """Erect an empty pasture on the unit's current tile."""


class FeedActionState(BaseAction[Literal["FEED"]]):
    """Feed a housed animal one wheat from the shed (once per day)."""


class CollectFertilizerActionState(BaseAction[Literal["COLLECT_FERTILIZER"]]):
    """Collect the 1 fertilizer a housed animal makes available each day."""


class CareActionState(BaseAction[Literal["CARE"]]):
    """Mark a housed animal cared-for today (once per day)."""


class BuySeedActionState(BaseAction[Literal['BUY_SEED']]):
    """Buy seeds from the market. Seeds live in their own slot and are consumed directly by PLANT."""
    crop: CROPS = Field(description="The crop whose seeds are being purchased")
    count: int = Field(description="The number of seed units to buy", gt=0)


class BuyProductActionState(BaseAction[Literal['BUY_PRODUCT']]):
    """Buy a buyable product (only wheat and fertilizer) back from the market."""
    item: BUYABLE_PRODUCTS = Field(description="The product to purchase")
    count: int = Field(description="The number of units to buy", gt=0)


class BuyAnimalActionState(BaseAction[Literal['BUY_ANIMAL']]):
    """Buy livestock from the market. Animals must be placed on a matching structure via PLACE."""
    animal: ANIMALS = Field(description="The animal being purchased")
    count: int = Field(description="The number of animals to buy", gt=0)


class SellActionState(BaseAction[Literal['SELL']]):
    """Sell harvested produce from the shed to the market at the current dynamic sale price."""
    item: SELLABLE_PRODUCTS = Field(description="The product being sold")
    count: int = Field(description="The number of units to sell", gt=0)


class HireActionState(BaseAction[Literal["HIRE"]]):
    pass


class BuyLandActionState(BaseAction[Literal["BUY_LAND"]]):
    pass


class PickupActionState(BaseAction[Literal['PICKUP']]):
    """Pick up a particular item(s) from the shed"""
    item: str = Field(description="The item to pickup")
    count: int = Field(description="The the number of items to pickup", gt=0)


class PlaceActionState(BaseAction[Literal['PLACE']]):
    """Place a particular item(s) from the inventory"""
    item: str = Field(description="The item to place")
    count: int = Field(description="The the number of items to place", gt=0)


class PassActionState(BaseAction[Literal["PASS"]]):
    pass


FarmActionState = Annotated[
    Union[
        PlantActionState,
        WaterActionState,
        MoveActionState,
        HarvestActionState,
        DigActionState,
        FertilizeActionState,
        BuildCoopActionState,
        BuildPastureActionState,
        FeedActionState,
        CollectFertilizerActionState,
        CareActionState,
        PickupActionState,
        PlaceActionState,
        PickupActionState,
        PassActionState
    ],
    Field(discriminator='type')
]


MarketActionState = Annotated[
    Union[
        BuySeedActionState,
        BuyProductActionState,
        BuyAnimalActionState,
        SellActionState,
        HireActionState,
        BuyLandActionState
    ],
    Field(discriminator='type')
]


ActionState = Annotated[
    Union[
        FarmActionState,
        MarketActionState
    ],
    Field(discriminator='type')
]
