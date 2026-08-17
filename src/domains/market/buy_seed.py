from src.models.game import RealityState
from src.models.crops import CROP_CONFIG
from src.models.action import (
    ActionState, BuySeedActionState, PlantActionState,
    WaterActionState, HarvestActionState, SellActionState,
)
from src.domains.farm.production import (
    crop_water_days_remaining, crop_expected_yield,
)


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
    seed_cost = CROP_CONFIG[action.crop].seed_cost
    affordable = int(farm.money // seed_cost) if seed_cost > 0 else action.count
    count = min(action.count, affordable)
    if count <= 0:
        return {"crop": action.crop, "count": 0, "unit_cost": seed_cost, "cost": 0}

    farm.money -= count * seed_cost
    seeds = state.privates[state.player].seeds
    setattr(seeds, action.crop, getattr(seeds, action.crop, 0) + count)
    return {"crop": action.crop, "count": count, "unit_cost": seed_cost, "cost": count * seed_cost}


def get_valid_buy_seed_actions(player) -> list[BuySeedActionState]:
    """Valid BUY_SEED actions — one per crop whose seed cost the farm can afford.

    BUY_SEED no-ops when `farm.money < seed_cost`, so a seed is valid iff the
    farm can afford at least one. Seeds have unlimited market supply, so
    inventory is never a constraint. Returns `count=1` (the minimal unit).
    """
    farm = player.farms[player.player]
    return [
        BuySeedActionState(type="BUY_SEED", crop=crop, count=1)
        for crop, cfg in CROP_CONFIG.items()
        if farm.money >= cfg.seed_cost
    ]


def get_buy_seed_pipeline(action: BuySeedActionState, player: RealityState,
                          unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """Actions following a BUY_SEED: PLANT the seed, then the plant's
    downstream chain — one WATER per remaining bonus-window day, then (for
    one-time crops) a HARVEST and a SELL of the expected yield. The PLANT's
    tile is not known at buy time; the evaluator resolves it when the farmer
    reaches an empty tile.
    """
    day = player.day
    waters = crop_water_days_remaining(action.crop, day, day)
    pipeline: list[ActionState] = [PlantActionState(type="PLANT", crop=action.crop)]
    pipeline += [WaterActionState(type="WATER") for _ in range(waters)]
    if CROP_CONFIG[action.crop].yield_type == "one-time":
        yield_units = crop_expected_yield(action.crop, day, day)
        pipeline.append(HarvestActionState(type="HARVEST"))
        if yield_units > 0:
            pipeline.append(SellActionState(type="SELL", item=action.crop, count=yield_units))
    return pipeline