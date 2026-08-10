from src.models.action import BuyLandActionState


# Unlock order (cheapest first) and fixed cost per quadrant.
QUADRANT_ORDER = ["NE", "SW", "SE"]
QUADRANT_COST = {"NE": 1000, "SW": 2000, "SE": 4000}


def buy_land(state, action: BuyLandActionState) -> dict:
    """Unlock the next quadrant of the farm grid.

    Quadrants unlock in fixed order NE ($1k) -> SW ($2k) -> SE ($4k),
    matching the increasing cost described in the README. No-ops (silent)
    when all quadrants are already unlocked or the farm cannot afford the
    next one. On success, deducts the cost, appends the quadrant name to
    `unlocked_quadrants`, and converts all `LOCKED` tiles in that quadrant
    to empty (None).
    """
    farm = state.farms[state.player]

    # Find the next quadrant to unlock (first in order not already unlocked).
    next_quad = None
    for q in QUADRANT_ORDER:
        if q not in farm.unlocked_quadrants:
            next_quad = q
            break
    if next_quad is None:
        return {"quadrant": None, "cost": 0, "unlocked": False}  # all quadrants already unlocked

    cost = QUADRANT_COST[next_quad]
    if farm.money < cost:
        return {"quadrant": next_quad, "cost": 0, "unlocked": False}

    farm.money -= cost
    farm.unlocked_quadrants.append(next_quad)
    _unlock_quadrant(farm, next_quad)
    return {"quadrant": next_quad, "cost": cost, "unlocked": True}


def _unlock_quadrant(farm, quadrant):
    """Convert all LOCKED tiles in the quadrant's range to None."""
    half_r = len(farm.tiles) // 2
    half_c = (len(farm.tiles[0]) if farm.tiles else 0) // 2
    full_r = len(farm.tiles)
    full_c = len(farm.tiles[0]) if farm.tiles else 0
    ranges = {
        "NW": (0, half_r, 0, half_c),
        "NE": (0, half_r, half_c, full_c),
        "SW": (half_r, full_r, 0, half_c),
        "SE": (half_r, full_r, half_c, full_c),
    }
    r0, r1, c0, c1 = ranges[quadrant]
    for r in range(r0, r1):
        for c in range(c0, c1):
            if farm.tiles[r][c] == "LOCKED":
                farm.tiles[r][c] = None