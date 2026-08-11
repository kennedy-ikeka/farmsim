from src.models.crops import CROP_CONFIG
from src.models.action import HarvestActionState
from src.models.farm import PlantState


def harvest(state, farm, unit_pos, action: HarvestActionState) -> dict:
    """Harvest the plant on the unit's current tile into the shed.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not a plant
      - the plant has not yet reached its first yield day
      - the plant has no harvestable units (`yield_units == 0`)

    On success, transfers `yield_units` from the plant to `private.shed[crop]`.
    For one-time crops, the plant is consumed and the tile becomes empty
    (None). For ongoing crops, the plant stays and `yield_units` resets to 0
    so it can keep producing on its schedule. Shed-capacity overflow is
    settled at end-of-day, not here.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "crop": None, "yield": 0}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "crop": None, "yield": 0}

    tile = farm.tiles[row][col]
    if not isinstance(tile, PlantState):
        return {"position": [row, col], "crop": None, "yield": 0}

    cfg = CROP_CONFIG[tile.crop]
    days_since_planting = state.day - tile.planted_day
    if days_since_planting < cfg["first_yield_day"]:
        return {"position": [row, col], "crop": tile.crop, "yield": 0}  # not yet mature

    yield_units = tile.yield_units
    if yield_units <= 0:
        return {"position": [row, col], "crop": tile.crop, "yield": 0}  # nothing to harvest

    shed = state.privates[state.player].shed
    current = getattr(shed, tile.crop, 0)
    setattr(shed, tile.crop, current + yield_units)

    if cfg["yield_type"] == "one-time":
        farm.tiles[row][col] = None  # plant consumed
    else:
        tile.yield_units = 0  # ongoing: plant stays, reset for next yield
    return {"position": [row, col], "crop": tile.crop, "yield": yield_units}