from typing import get_args

from src.models.game import RealityState

from src.models.action import ActionState, BuyProductActionState
from src.models.objects import BUYABLE_PRODUCTS


def buy_product(state, action: BuyProductActionState) -> dict:
    """Buy `count` of `action.item` back from the market into the shed.

    Only WHEAT and FERTILIZER are buyable (enforced by the action model's
    `BUYABLE_PRODUCTS` literal). Buys at the current market sale price
    (`market.prices[item]`), draining `market.inventory[item]`. No-ops
    (silent) when the market is out of stock, the price is non-positive, or
    the farm cannot afford any units. Partial fulfillment: only as many
    units as the market holds and the farm can afford are bought, matching
    the market's one-unit-at-a-time "order is stopped when out of money"
    rule. Bought units are added to `private.shed[item]`.
    """
    farm = state.farms[state.player]
    item = action.item
    price = getattr(state.market.prices, item, 0)
    if price <= 0:
        return {"item": item, "count": 0, "price": 0, "cost": 0}

    available = getattr(state.market.inventory, item, 0)
    affordable = int(farm.money // price)
    count = min(action.count, available, affordable)
    if count <= 0:
        return {"item": item, "count": 0, "price": price, "cost": 0}

    setattr(state.market.inventory, item, available - count)
    farm.money -= count * price
    shed = state.privates[state.player].shed
    setattr(shed, item, getattr(shed, item, 0) + count)
    return {"item": item, "count": count, "price": price, "cost": count * price}


def get_valid_buy_product_actions(player) -> list[BuyProductActionState]:
    """Valid BUY_PRODUCT actions — one per buyable product the farm can afford.

    BUY_PRODUCT no-ops when `price <= 0`, the market is out of stock
    (`inventory <= 0`), or `farm.money < price`. Returns `count=1` per viable
    item (only WHEAT and FERTILIZER are buyable).
    """
    farm = player.farms[player.player]
    market = player.market
    actions: list[BuyProductActionState] = []
    for item in get_args(BUYABLE_PRODUCTS):
        price = getattr(market.prices, item, 0)
        available = getattr(market.inventory, item, 0)
        if price > 0 and available > 0 and farm.money >= price:
            actions.append(BuyProductActionState(type="BUY_PRODUCT", item=item, count=1))
    return actions


def get_buy_product_pipeline(action: BuyProductActionState, player: RealityState,
                             unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """BUY_PRODUCT buys an input (WHEAT for FEED, FERTILIZER for FERTILIZE) —
    its use depends on where the player later deploys it, so there is no
    deterministic next action.
    """
    return []