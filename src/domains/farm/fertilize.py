from src.models.game import RealityState
from src.models.crops import CROP_CONFIG
from src.models.action import (
    ActionState, FertilizeActionState, WaterActionState,
    HarvestActionState, SellActionState,
)
from src.models.farm import PlantState
from src.utils.farm import in_bounds, tile_at
from src.domains.farm.production import (
    crop_water_days_remaining, crop_expected_yield,
)


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


def get_fertilize_pipeline(action: FertilizeActionState, player: RealityState,
                           unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """Actions following a FERTILIZE on a plant tile: the remaining bonus-window
    WATERs (the next 3 of which carry the +1 fertilize bonus), then (for one-time
    crops) a HARVEST and a SELL of the expected yield. Non-plant tiles have no
    downstream.
    """
    farm = player.farms[player.player]
    tile = tile_at(farm, unit_pos) if unit_pos is not None else None
    if not isinstance(tile, PlantState):
        return []
    day = player.day
    waters = crop_water_days_remaining(tile.crop, tile.planted_day, day)
    pipeline: list[ActionState] = [WaterActionState(type="WATER") for _ in range(waters)]
    if CROP_CONFIG[tile.crop].yield_type == "one-time":
        yield_units = crop_expected_yield(tile.crop, tile.planted_day, day)
        pipeline.append(HarvestActionState(type="HARVEST"))
        if yield_units > 0:
            pipeline.append(SellActionState(type="SELL", item=tile.crop, count=yield_units))
    return pipeline