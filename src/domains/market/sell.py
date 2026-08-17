from src.models.action import SellActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState


def sell(state, action: SellActionState) -> dict:
    """Sell `count` of `item` from the shed into the market at current price."""
    farm = state.farms[state.player]
    shed = state.privates[state.player].shed
    available = getattr(shed, action.item, 0)

    count = min(action.count, available)
    price = getattr(state.market.prices, action.item, 0)
    if count <= 0:
        return {"item": action.item, "count": 0, "price": price, "revenue": 0}

    setattr(shed, action.item, available - count)
    inventory = getattr(state.market.inventory, action.item, 0)

    setattr(state.market.inventory, action.item, inventory + count)
    farm.money += count * price
    return {"item": action.item, "count": count, "price": price, "revenue": count * price}


def get_valid_sell_actions(player) -> list[SellActionState]:
    """Valid SELL actions — one per priced item the shed currently holds.

    SELL (via the interleave loop's `sell_one`) no-ops when `shed.<item> <= 0`
    or `price <= 0`. Only items with a market price are sellable, so iterate
    the price fields and check the shed holds at least one. Returns `count=1`.
    """
    farm = player.farms[player.player]
    shed = player.private.shed
    prices = player.market.prices
    return [
        SellActionState(type="SELL", item=item, count=1)
        for item in type(prices).model_fields
        if getattr(shed, item, 0) > 0 and getattr(prices, item, 0) > 0
    ]


def sell_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """SELL consumes `count` of `item` from the shed (PRODUCE units) and one step."""
    return ResourceState(
        STEP=1.0,
        PRODUCE=float(action.count),
    )


def sell_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Immediate MONEY from selling `count` of `item` at the current market price."""
    return ResourceState(
        MONEY=float(action.count * getattr(player.market.prices, action.item, 0))
    )