from src.models.crops import CROP_CONFIG
from src.models.action import BuySeedActionState


def buy_seed(state, action: BuySeedActionState) -> dict:
    """Buy `count` seeds of `action.crop` from the market at the fixed seed cost.

    The market has an unlimited supply of seeds at the per-crop fixed
    `seed_cost` (see CROP_CONFIG). No-ops (silent) when the farm cannot
    afford any seeds. On success, deducts `count * seed_cost` from the farm's
    money and adds `count` to `private.seeds[crop]`. Partial fulfillment: only
    as many seeds as the farm can afford are bought, matching the market's
    one-unit-at-a-time "order is stopped when out of money" rule.
    """
    farm = state.farms[state.player]
    seed_cost = CROP_CONFIG[action.crop]["seed_cost"]
    affordable = int(farm.money // seed_cost) if seed_cost > 0 else action.count
    count = min(action.count, affordable)
    if count <= 0:
        return {"crop": action.crop, "count": 0, "unit_cost": seed_cost, "cost": 0}

    farm.money -= count * seed_cost
    seeds = state.privates[state.player].seeds
    setattr(seeds, action.crop, getattr(seeds, action.crop, 0) + count)
    return {"crop": action.crop, "count": count, "unit_cost": seed_cost, "cost": count * seed_cost}