import math

from src.models.crops import CROP_CONFIG
from src.models.action import FertilizeActionState, ActionState
from src.models.farm import PlantState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.utils.farm import in_bounds, tile_at
from src.domains.farm.production import EPISODE_DAYS


def fertilize(state, farm, unit_pos, action: FertilizeActionState) -> dict:
    """Fertilize the plant on the unit's current tile, consuming one fertilizer.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not a plant
      - there is no fertilizer in the shed

    On success, consumes one unit of FERTILIZER from `private.shed` and sets
    `fertilized_until_day = day + 3` on the plant, doubling the per-day
    watering bonus for the next 3 days (the bonus only applies on days the
    plant is also watered — basic needs first). Re-fertilizing refreshes the
    window to a fresh 3 days from today and consumes another unit.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "fertilized": False}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "fertilized": False}

    tile = farm.tiles[row][col]
    if not isinstance(tile, PlantState):
        return {"position": [row, col], "fertilized": False}

    shed = state.privates[state.player].shed
    if shed.FERTILIZER <= 0:
        return {"position": [row, col], "fertilized": False}

    shed.FERTILIZER -= 1
    tile.fertilized_until_day = state.day + 3
    return {"position": [row, col], "fertilized": True}


def get_valid_fertilize_actions_for(player, unit_pos) -> list[FertilizeActionState]:
    """Valid FERTILIZE actions for a unit at `unit_pos` ([row, col]).

    FERTILIZE is valid iff the unit is in bounds, the tile holds a plant, and
    the player has fertilizer in the shed.
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if not isinstance(tile, PlantState):
        return []
    if player.private.shed.FERTILIZER <= 0:
        return []
    return [FertilizeActionState(type="FERTILIZE")]


def fertilize_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """FERTILIZE consumes one FERTILIZER (valued at the market price) and one
    step. PRODUCE tracks the raw FERTILIZER unit consumed from the shed."""
    return ResourceState(
        STEP=1.0,
        MONEY=float(getattr(player.market.prices, "FERTILIZER", 0)),
        PRODUCE=1.0,
    )


def fertilize_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY from the +1 bonus on each remaining window day covered by
    the 3-day fertilize window, valued at the crop's market price."""
    farm = player.farms[player.player]
    tile = tile_at(farm, farm.farmer)
    if not isinstance(tile, PlantState):
        return ResourceState()
    cfg = CROP_CONFIG[tile.crop]
    if cfg.yield_type != "one-time":
        return ResourceState()
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    # FERTILIZE sets fertilized_until_day = day + 3, so the +1 bonus covers
    # future window days in (day, day + 3] that fit in the episode.
    bonus_days = sum(
        1
        for d in range(window_start, window_end + 1)
        if player.day < tile.planted_day + d <= player.day + 3
        and tile.planted_day + d < EPISODE_DAYS
    )
    return ResourceState(
        MONEY=float(bonus_days * getattr(player.market.prices, tile.crop, 0)),
        PRODUCE=float(bonus_days),
    )


def fertilize_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream steps to realize the gain: one harvest + one sell."""
    return ResourceState(STEP=2.0)