"""Per-unit buy_land helper — unlocks the next quadrant in fixed order at the
fixed per-quadrant cost. Used by the market interleave loop (single-shot: one
attempt per order)."""
from src.models.action import BuyLandActionState

from src.domains.market.buy_land import QUADRANT_COST, QUADRANT_ORDER, _unlock_quadrant


def buy_land_one(farm, action: BuyLandActionState) -> tuple[bool, dict]:
    """Unlock the next quadrant for `farm` in fixed order (NE -> SW -> SE),
    charging the per-quadrant cost. Returns `(success, unit_occurred)`.

    Fails when all quadrants are already unlocked or the farm cannot afford
    the next one.
    """
    next_quad = None
    for q in QUADRANT_ORDER:
        if q not in farm.unlocked_quadrants:
            next_quad = q
            break
    if next_quad is None:
        return False, {"quadrant": None, "cost": 0, "unlocked": False}
    cost = QUADRANT_COST[next_quad]
    if farm.money < cost:
        return False, {"quadrant": next_quad, "cost": 0, "unlocked": False}
    farm.money -= cost
    farm.unlocked_quadrants.append(next_quad)
    _unlock_quadrant(farm, next_quad)
    return True, {"quadrant": next_quad, "cost": cost, "unlocked": True}