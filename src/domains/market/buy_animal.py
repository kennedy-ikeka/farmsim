from src.models.animals import ANIMAL_CONFIG
from src.models.action import BuyAnimalActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.domains.farm.production import animal_future_production


def buy_animal(state, action: BuyAnimalActionState) -> dict:
    """Buy `count` of `action.animal` from the market into the shed.

    The market has an unlimited supply of animals at the fixed per-animal
    cost (see ANIMAL_CONFIG). No-ops (silent) when the farm cannot afford
    any. On success, deducts `count * cost` from the farm's money and adds
    `count` to `private.shed[animal]`. Partial fulfillment: only as many
    animals as the farm can afford are bought, matching the market's
    one-unit-at-a-time "order is stopped when out of money" rule.
    """
    farm = state.farms[state.player]
    cost = ANIMAL_CONFIG[action.animal].cost
    affordable = int(farm.money // cost) if cost > 0 else action.count
    count = min(action.count, affordable)
    if count <= 0:
        return {"animal": action.animal, "count": 0, "unit_cost": cost, "cost": 0}

    farm.money -= count * cost
    shed = state.privates[state.player].shed
    setattr(shed, action.animal, getattr(shed, action.animal, 0) + count)
    return {"animal": action.animal, "count": count, "unit_cost": cost, "cost": count * cost}


def get_valid_buy_animal_actions(player) -> list[BuyAnimalActionState]:
    """Valid BUY_ANIMAL actions — one per animal the farm can afford.

    BUY_ANIMAL no-ops when `farm.money < cost`. Animals have unlimited market
    supply. Returns `count=1` per viable animal.
    """
    farm = player.farms[player.player]
    return [
        BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=1)
        for animal, cfg in ANIMAL_CONFIG.items()
        if farm.money >= cfg.cost
    ]


def buy_animal_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """BUY_ANIMAL costs `count * animal.cost` MONEY and one step."""
    return ResourceState(
        STEP=1.0,
        MONEY=float(action.count * ANIMAL_CONFIG[action.animal].cost),
    )


def buy_animal_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Immediate ANIMAL gained (valued at economic value = count * cost)."""
    return ResourceState(
        ANIMAL=float(action.count * ANIMAL_CONFIG[action.animal].cost)
    )


def buy_animal_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Each animal enables one PLACE → its full production + fertilizer under
    optimal completion. PRODUCE = future product + fertilizer units the bought
    animals will produce. Deployment costs are counted at PLACE time, so
    future_usage here is {}."""
    if action.animal not in ANIMAL_CONFIG:
        return ResourceState()
    y, f = animal_future_production(action.animal, player.day)
    product = ANIMAL_CONFIG[action.animal].product
    prices = player.market.prices
    return ResourceState(
        MONEY=float(action.count * (y * getattr(prices, product, 0) + f * getattr(prices, "FERTILIZER", 0))),
        PRODUCE=float(action.count * (y + f)),
    )