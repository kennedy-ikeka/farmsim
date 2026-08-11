from typing_extensions import Literal
from pydantic import BaseModel, Field

from src.utils.config import (
    TOWN_CENTER_SELL_INTERVAL,
    TOWN_SHOP_SELL_INTERVAL,
    TOWN_SHOP_UNLOCK_INTERVAL,
)

TOWN_SHOPS = Literal[
    'BAKERY',
    'PET_CAFE',
    'YARN_STORE',
    'BRUNCH_SPOT',
    'PIZZA_SHOP',
    'SMOOTHIE_SHOP',
    'ICE_CREAM_SHOP',
    'FARMERS_MARKET',
]

# All shop types, in canonical order. Used by the Town controller to pick
# uniformly at random from the not-yet-unlocked shops.
ALL_SHOPS: tuple[TOWN_SHOPS, ...] = (
    'BAKERY',
    'PIZZA_SHOP',
    'BRUNCH_SPOT',
    'YARN_STORE',
    'ICE_CREAM_SHOP',
    'PET_CAFE',
    'SMOOTHIE_SHOP',
    'FARMERS_MARKET',
)

# Products each unlocked shop demands, per README "Town Buildings" table.
# Single-product shops (YARN_STORE, PET_CAFE) consume 2x per demand unit.
SHOP_DEMAND: dict[TOWN_SHOPS, list[str]] = {
    'BAKERY':         ['EGG', 'WHEAT'],
    'PIZZA_SHOP':     ['MILK', 'TOMATO', 'WHEAT'],
    'BRUNCH_SPOT':    ['EGG', 'WHEAT', 'STRAWBERRY'],
    'YARN_STORE':     ['WOOL'],            # 2x — single-product shop
    'ICE_CREAM_SHOP': ['STRAWBERRY', 'MILK', 'WHEAT'],
    'PET_CAFE':       ['CARROT'],          # 2x — single-product shop
    'SMOOTHIE_SHOP':  ['STRAWBERRY', 'MILK'],
    'FARMERS_MARKET': ['WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY'],
}

# Single-product shops consume 2 units of their one product per tick.
SINGLE_PRODUCT_SHOPS: frozenset[TOWN_SHOPS] = frozenset({'YARN_STORE', 'PET_CAFE'})

# Town center consumes one of every product *except fertilizer* per tick.
# (Fertilizer is excluded per README "town center consumes one of every product
# excluding fertilizer".)
TOWN_CENTER_PRODUCTS: tuple[str, ...] = (
    'WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL',
)


class TownState(BaseModel):
    """State of the town: unlocked shops + town-center/shop consumption scheduling.

    Per README "Town Buildings":
    - A new shop unlocks every `townShopUnlockInterval` days (default 3), randomly
      chosen from shops not yet unlocked; once unlocked, a shop stays active for
      the rest of the game. Total demand grows monotonically as more shops unlock.
    - Each unlocked shop consumes one of every product it demands (2x for
      single-product shops) every `townShopSellInterval` turns (default 4).
    - The town center consumes one of every product (excluding fertilizer) every
      `townCenterSellInterval` turns (default 12); 2 of each after day 10,
      4 of each after day 20.
    """

    unlocked_shops: list[TOWN_SHOPS] = Field(
        default_factory=list,
        description=(
            "Shops currently unlocked in town. Grows monotonically as the "
            "season progresses; once unlocked, a shop stays active."
        ),
    )

    town_shop_unlock_interval: int = Field(
        default=TOWN_SHOP_UNLOCK_INTERVAL,
        description="Days between successive town shop unlocks.",
    )
    town_shop_sell_interval: int = Field(
        default=TOWN_SHOP_SELL_INTERVAL,
        description="Turns between consumption ticks by every unlocked shop.",
    )
    town_center_sell_interval: int = Field(
        default=TOWN_CENTER_SELL_INTERVAL,
        description="Turns between consumption ticks by the town center.",
    )

    last_shop_unlock_day: int = Field(
        default=0,
        description=(
            "In-game day of the most recent shop unlock. Used to schedule the "
            "next unlock against `townShopUnlockInterval`."
        ),
    )

    last_shop_consume_step: int = Field(
        default=0,
        description=(
            "Step at which the unlocked shops last consumed market inventory. "
            "Used to schedule the next consumption tick against "
            "`townShopSellInterval`."
        ),
    )

    last_center_consume_step: int = Field(
        default=0,
        description=(
            "Step at which the town center last consumed market inventory. "
            "Used to schedule the next consumption tick against "
            "`townCenterSellInterval`; the per-product amount scales with day "
            "(1 until day 10, 2 until day 20, 4 thereafter)."
        ),
    )