"""Per-unit sell helper — sells exactly one unit of `action.item` from the shed
into the market at the current price.

Used by the market interleave loop (one unit at a time, round-robin across
players). Returns `(success, unit_occurred)` so the loop can accumulate the
per-order `occurred` dict across units.
"""
from src.models.action import SellActionState


def sell_one(farm, priv, market, action: SellActionState) -> tuple[bool, dict]:
    """Sell one unit of `action.item` from `priv.shed` into `market` at the
    current price, crediting `farm.money`. Returns `(success, unit_occurred)`.

    Fails (returns `(False, zeroed_occurred)`) when the shed is empty of the
    item or the current market price is non-positive.
    """
    available = getattr(priv.shed, action.item, 0)
    if available <= 0:
        return False, {"item": action.item, "count": 0, "price": 0, "revenue": 0}
    price = getattr(market.prices, action.item, 0)
    if price <= 0:
        return False, {"item": action.item, "count": 0, "price": 0, "revenue": 0}
    setattr(priv.shed, action.item, available - 1)
    cur_inv = getattr(market.inventory, action.item, 0)
    setattr(market.inventory, action.item, cur_inv + 1)
    farm.money += price
    return True, {"item": action.item, "count": 1, "price": price, "revenue": price}