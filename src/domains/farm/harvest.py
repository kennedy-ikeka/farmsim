from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG
from src.models.action import HarvestActionState
from src.models.farm import AnimalState, PlantState
from src.utils.farm import in_bounds


def harvest(state, farm, unit_pos, action: HarvestActionState) -> dict:
    """Harvest produce from the plant or animal on the unit's current tile.

    Two tile kinds are harvestable:

      - Plant tiles: transfers `yield_units` of the crop to `private.shed[crop]`.
        For one-time crops the plant is consumed (tile → None); for ongoing
        crops the plant stays and `yield_units` resets to 0 for the next yield.

      - Animal tiles (housed): transfers `yield_units` of the animal's product
        (EGG / MILK / WOOL) to `private.shed[product]` and resets `yield_units`
        to 0. The animal and its structure stay on the tile.

    No-ops (silent) when the unit position is malformed / out of bounds, the
    tile is neither a plant nor a housed animal, the plant has not yet reached
    its `first_yield_day`, or there are no harvestable units (`yield_units == 0`).
    Shed-capacity overflow is settled at end-of-day, not here.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "crop": None, "yield": 0}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "crop": None, "yield": 0}

    tile = farm.tiles[row][col]
    shed = state.privates[state.player].shed

    if isinstance(tile, PlantState):
        cfg = CROP_CONFIG[tile.crop]
        days_since_planting = state.day - tile.planted_day
        if days_since_planting < cfg.first_yield_day:
            return {"position": [row, col], "crop": tile.crop, "yield": 0}  # not yet mature

        yield_units = tile.yield_units
        if yield_units <= 0:
            return {"position": [row, col], "crop": tile.crop, "yield": 0}  # nothing to harvest

        current = getattr(shed, tile.crop, 0)
        setattr(shed, tile.crop, current + yield_units)
        if cfg.yield_type == "one-time":
            farm.tiles[row][col] = None  # plant consumed
        else:
            tile.yield_units = 0  # ongoing: plant stays, reset for next yield
        return {"position": [row, col], "crop": tile.crop, "yield": yield_units}

    if isinstance(tile, AnimalState) and tile.animal is not None:
        yield_units = tile.yield_units
        if yield_units <= 0:
            return {"position": [row, col], "animal": tile.animal, "product": None, "yield": 0}

        product = ANIMAL_CONFIG[tile.animal].product
        current = getattr(shed, product, 0)
        setattr(shed, product, current + yield_units)
        tile.yield_units = 0  # animal + structure stay; reset for next production
        return {"position": [row, col], "animal": tile.animal, "product": product, "yield": yield_units}

    return {"position": [row, col], "crop": None, "yield": 0}


def get_valid_harvest_actions_for(player, unit_pos) -> list[HarvestActionState]:
    """Valid HARVEST actions for a unit at `unit_pos` ([row, col]).

    HARVEST is valid iff the unit is in bounds and the tile is either:
      - a plant that has reached its `first_yield_day` with `yield_units > 0`, or
      - a housed animal structure with `yield_units > 0`.
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if isinstance(tile, PlantState):
        cfg = CROP_CONFIG[tile.crop]
        if (player.day - tile.planted_day) < cfg.first_yield_day:
            return []
        if tile.yield_units <= 0:
            return []
        return [HarvestActionState(type="HARVEST")]
    if isinstance(tile, AnimalState) and tile.animal is not None and tile.yield_units > 0:
        return [HarvestActionState(type="HARVEST")]
    return []