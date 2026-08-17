from src.models.farm import AnimalState
from src.models.action import CollectFertilizerActionState
from src.utils.farm import in_bounds


def collect_fertilizer(state, farm, unit_pos, action) -> dict:
    """Collect the 1 fertilizer a housed animal makes available each day.

    Every surviving animal makes 1 fertilizer available at end-of-day; it
    does not accumulate beyond 1, so `fertilizer_available` is 0 or 1.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not an animal structure
      - no animal is housed on the structure
      - there is no fertilizer available to collect

    On success, moves `fertilizer_available` into `private.shed.FERTILIZER`
    and resets the tile's `fertilizer_available` to 0.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "animal": None, "collected": 0}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "animal": None, "collected": 0}

    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState):
        return {"position": [row, col], "animal": None, "collected": 0}
    if tile.animal is None:
        return {"position": [row, col], "animal": None, "collected": 0}
    if tile.fertilizer_available <= 0:
        return {"position": [row, col], "animal": tile.animal, "collected": 0}

    tile.fertilizer_available = 0
    state.privates[state.player].shed.FERTILIZER += 1
    return {"position": [row, col], "animal": tile.animal, "collected": 1}


def get_valid_collect_fertilizer_actions_for(farm, unit_pos) -> list[CollectFertilizerActionState]:
    """Valid COLLECT_FERTILIZER actions for a unit at `unit_pos` ([row, col]).

    Valid iff the unit is in bounds, the tile is an occupied animal structure
    with fertilizer available to collect.
    """
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState) or tile.animal is None:
        return []
    if tile.fertilizer_available <= 0:
        return []
    return [CollectFertilizerActionState(type="COLLECT_FERTILIZER")]