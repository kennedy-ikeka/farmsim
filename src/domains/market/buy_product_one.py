"""Per-unit buy_product helper — buys exactly one unit of `action.item` back
from the market into the shed at the current price. Used by the market
interleave loop (drains shared market inventory one unit at a time)."""
from src.models.action import BuyProductActionState


def buy_product_one(farm, priv, market, action: BuyProductActionState) -> tuple[bool, dict]:
    """Buy one unit of `action.item` from `market` into `priv.shed` at the
    current price. Returns `(success, unit_occurred)`.

    Fails when the price is non-positive, the market is out of stock, or the
    farm cannot afford one unit.
    """
    price = getattr(market.prices, action.item, 0)
    if price <= 0:
        return False, {"item": action.item, "count": 0, "price": 0, "cost": 0}
    available = getattr(market.inventory, action.item, 0)
    if available <= 0:
        return False, {"item": action.item, "count": 0, "price": price, "cost": 0}
    if farm.money < price:
        return False, {"item": action.item, "count": 0, "price": price, "cost": 0}
    setattr(market.inventory, action.item, available - 1)
    farm.money -= price
    setattr(priv.shed, action.item, getattr(priv.shed, action.item, 0) + 1)
    return True, {"item": action.item, "count": 1, "price": price, "cost": price}