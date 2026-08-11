from src.models.action import FertilizeActionState
from src.models.farm import PlantState


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