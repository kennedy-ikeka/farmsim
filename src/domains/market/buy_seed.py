from src.models.crops import CROP_CONFIG
from src.models.action import BuySeedActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.domains.farm.production import crop_future_yield


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


def buy_seed_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """BUY_SEED costs `count * seed_cost` MONEY and one step."""
    return ResourceState(
        STEP=1.0,
        MONEY=float(action.count * CROP_CONFIG[action.crop].seed_cost),
    )


def buy_seed_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Immediate SEED gained (valued at economic value = count * seed_cost)."""
    return ResourceState(
        SEED=float(action.count * CROP_CONFIG[action.crop].seed_cost)
    )


def buy_seed_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Each seed enables one PLANT → one crop's worth of yield under optimal
    completion. PRODUCE = future yield units the bought seeds will grow into.
    Deployment costs (seed, land, step, waters, harvest, sell) are counted at
    PLANT time, so future_usage here is {}."""
    cfg = CROP_CONFIG[action.crop]
    if cfg.yield_type != "one-time":
        return ResourceState()
    yield_units = crop_future_yield(action.crop, player.day)
    return ResourceState(
        MONEY=float(action.count * yield_units * getattr(player.market.prices, action.crop, 0)),
        PRODUCE=float(action.count * yield_units),
    )