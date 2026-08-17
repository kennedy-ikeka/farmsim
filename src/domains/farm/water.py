import math

from src.models.crops import CROP_CONFIG
from src.models.action import WaterActionState, ActionState
from src.models.farm import PlantState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.utils.farm import in_bounds, tile_at


def water(state, farm, unit_pos) -> dict:
    """Water the plant on the unit's current tile.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not a plant
      - the plant has already been watered today

    On success, sets `watered_today = True` and resets
    `consecutive_unwatered = 0`. For one-time crops watered within the
    bonus window (days `ceil(max_yield_day / 2)` through `max_yield_day`,
    measured from planting), adds 1 unit to harvestable yield — or 2 if
    FERTILIZE's bonus is still active (`fertilized_until_day >= day`).
    Ongoing crops accrue their watering bonus at scheduled production time,
    not here, so WATER on an ongoing crop only marks it watered.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "watered": False, "bonus": 0}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "watered": False, "bonus": 0}

    tile = farm.tiles[row][col]
    if not isinstance(tile, PlantState):
        return {"position": [row, col], "watered": False, "bonus": 0}

    if tile.watered_today:
        return {"position": [row, col], "watered": False, "bonus": 0}  # one bonus per day

    tile.watered_today = True
    tile.consecutive_unwatered = 0

    cfg = CROP_CONFIG[tile.crop]
    if cfg.yield_type != "one-time":
        return {"position": [row, col], "watered": True, "bonus": 0}  # ongoing: bonus at production time

    # Bonus window is measured in days since planting: the window starts at
    # ceil(max_yield_day / 2) and runs through max_yield_day (inclusive).
    days_since_planting = state.day - tile.planted_day
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    if not (window_start <= days_since_planting <= window_end):
        return {"position": [row, col], "watered": True, "bonus": 0}

    bonus = 2 if tile.fertilized_until_day >= state.day else 1
    tile.yield_units += bonus
    return {"position": [row, col], "watered": True, "bonus": bonus}


def get_valid_water_actions_for(farm, unit_pos) -> list[WaterActionState]:
    """Valid WATER actions for a unit at `unit_pos` ([row, col]).

    WATER is valid iff the unit is in bounds, the tile holds a plant, and that
    plant has not already been watered today.
    """
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if isinstance(tile, PlantState) and not tile.watered_today:
        return [WaterActionState(type="WATER")]
    return []


def water_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY this water adds: +1 yield (or +2 if fertilized) when
    watered inside the bonus window, valued at the crop's market price."""
    farm = player.farms[player.player]
    tile = tile_at(farm, farm.farmer)
    if not isinstance(tile, PlantState):
        return ResourceState()
    cfg = CROP_CONFIG[tile.crop]
    if cfg.yield_type != "one-time":
        return ResourceState()
    dsp = player.day - tile.planted_day
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    if not (window_start <= dsp <= window_end):
        return ResourceState()
    bonus = 2 if tile.fertilized_until_day >= player.day else 1
    return ResourceState(
        MONEY=float(bonus * getattr(player.market.prices, tile.crop, 0)),
        PRODUCE=float(bonus),
    )


def water_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream steps to realize the gain: one harvest + one sell."""
    return ResourceState(STEP=2.0)