"""Order-event accumulation helpers for the market interleave loop.

The interleave loop processes one unit at a time per order; these helpers
build and fold the per-order `occurred` dict across units, then emit a single
`EventState` per order (with `intended` = the action parameters and `occurred`
= the accumulated outcome across all units of the order).
"""
from src.models.animals import ANIMAL_CONFIG
from src.models.crops import CROP_CONFIG
from src.models.event import EventState


def init_occurred(action) -> dict:
    """Initialize the per-order accumulated occurred dict with zeroed totals
    keyed to the action's `occurred` shape."""
    match action.type:
        case "SELL":
            return {"item": action.item, "count": 0, "price": 0, "revenue": 0.0}
        case "BUY_SEED":
            return {"crop": action.crop, "count": 0,
                    "unit_cost": CROP_CONFIG[action.crop].seed_cost, "cost": 0.0}
        case "BUY_PRODUCT":
            return {"item": action.item, "count": 0, "price": 0, "cost": 0.0}
        case "BUY_ANIMAL":
            return {"animal": action.animal, "count": 0,
                    "unit_cost": ANIMAL_CONFIG[action.animal].cost, "cost": 0.0}
        case "HIRE":
            return {"cost": 0, "position": None, "hired": False}
        case "BUY_LAND":
            return {"quadrant": None, "cost": 0, "unlocked": False}
        case _:
            return {}


def accumulate(acc: dict, unit: dict) -> None:
    """Fold one unit's occurred fragment into the order's accumulated occurred.

    Mutates `acc` in place. Counted actions accumulate `count`, `revenue`, and
    `cost`; `price` keeps the latest unit price seen (fixed within a turn for
    now). Single-shot fields (HIRE / BUY_LAND) take the unit's values directly.
    """
    if "count" in acc and "count" in unit:
        acc["count"] += unit["count"]
    if "revenue" in acc and "revenue" in unit:
        acc["revenue"] += unit["revenue"]
    if "cost" in acc and "cost" in unit:
        acc["cost"] += unit["cost"]
    if "price" in acc and "price" in unit:
        # Keep the latest unit price seen (price is fixed within a turn for now).
        acc["price"] = unit["price"]
    # Single-shot fields (HIRE / BUY_LAND): take the unit's values directly.
    if "hired" in unit:
        acc["hired"] = unit["hired"]
        acc["cost"] = unit.get("cost", acc["cost"])
        acc["position"] = unit.get("position", acc["position"])
    if "unlocked" in unit:
        acc["unlocked"] = unit["unlocked"]
        acc["cost"] = unit.get("cost", acc["cost"])
        acc["quadrant"] = unit.get("quadrant", acc["quadrant"])


def build_event(state, action, occurred: dict) -> EventState:
    """Build a single `EventState` for an order, tagged with the active player."""
    return EventState(
        step=state.step,
        day=state.day,
        hour=state.hour,
        player=state.player,
        type=action.type,
        intended=action.model_dump(exclude={"type"}),
        occurred=occurred,
    )