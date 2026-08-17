from src.models.game import RealityState
from src.models.animals import ANIMAL_CONFIG
from src.models.action import ActionState, BuyAnimalActionState, PlaceActionState
from src.domains.farm.production import animal_pipeline


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


def get_buy_animal_pipeline(action: BuyAnimalActionState, player: RealityState,
                            unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """Actions following a BUY_ANIMAL: PLACE the animal on a matching
    structure, then the animal's per-day care + harvest + sell tail. The
    structure tile is not known at buy time; the evaluator resolves it.
    """
    return [PlaceActionState(type="PLACE", item=action.animal, count=1)] + animal_pipeline(action.animal, player.day)