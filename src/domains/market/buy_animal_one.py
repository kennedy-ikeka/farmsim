"""Per-unit buy_animal helper — buys exactly one animal of `action.animal` at
the fixed per-animal cost. Used by the market interleave loop."""
from src.models.action import BuyAnimalActionState
from src.models.animals import ANIMAL_CONFIG


def buy_animal_one(farm, priv, action: BuyAnimalActionState) -> tuple[bool, dict]:
    """Buy one animal of `action.animal` at the fixed cost, deducting from
    `farm.money` and crediting `priv.shed[animal]`. Returns `(success, unit_occurred)`.

    Fails when the farm cannot afford one unit.
    """
    cost = ANIMAL_CONFIG[action.animal]["cost"]
    if farm.money < cost:
        return False, {"animal": action.animal, "count": 0, "unit_cost": cost, "cost": 0}
    farm.money -= cost
    setattr(priv.shed, action.animal, getattr(priv.shed, action.animal, 0) + 1)
    return True, {"animal": action.animal, "count": 1, "unit_cost": cost, "cost": cost}