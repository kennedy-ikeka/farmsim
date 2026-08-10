from src.models.action import BuyProductActionState


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
    shed = state.private.shed
    setattr(shed, item, getattr(shed, item, 0) + count)
    return {"item": item, "count": count, "price": price, "cost": count * price}