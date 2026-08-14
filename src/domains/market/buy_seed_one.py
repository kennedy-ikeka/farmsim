"""Per-unit buy_seed helper — buys exactly one seed of `action.crop` at the
fixed `seed_cost`. Used by the market interleave loop."""
from src.models.action import BuySeedActionState
from src.models.crops import CROP_CONFIG


def buy_seed_one(farm, priv, action: BuySeedActionState) -> tuple[bool, dict]:
    """Buy one seed of `action.crop` at the fixed `seed_cost`, deducting from
    `farm.money` and crediting `priv.seeds[crop]`. Returns `(success, unit_occurred)`.

    Fails when the farm cannot afford one unit.
    """
    cost = CROP_CONFIG[action.crop].seed_cost
    if farm.money < cost:
        return False, {"crop": action.crop, "count": 0, "unit_cost": cost, "cost": 0}
    farm.money -= cost
    setattr(priv.seeds, action.crop, getattr(priv.seeds, action.crop, 0) + 1)
    return True, {"crop": action.crop, "count": 1, "unit_cost": cost, "cost": cost}