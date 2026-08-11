from src.models.animals import ANIMAL_CONFIG
from src.models.action import BuyAnimalActionState


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
    cost = ANIMAL_CONFIG[action.animal]["cost"]
    affordable = int(farm.money // cost) if cost > 0 else action.count
    count = min(action.count, affordable)
    if count <= 0:
        return {"animal": action.animal, "count": 0, "unit_cost": cost, "cost": 0}

    farm.money -= count * cost
    shed = state.privates[state.player].shed
    setattr(shed, action.animal, getattr(shed, action.animal, 0) + count)
    return {"animal": action.animal, "count": count, "unit_cost": cost, "cost": count * cost}